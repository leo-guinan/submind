import uuid
from datetime import datetime

import requests
from decouple import config
from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers.openai_functions import JsonKeyOutputFunctionsParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from submind.documents import get_document
from submind.models import Thought, Research, Question, Answer
from submind.new_answers import pull_new_answers

RESEARCH_PROMPT = """You are a submind of a founder that is dedicated to doing research for them.

    Here's what you know about the founder: {founder}
    
    Here's what you know about the founder's values: {values}
    
    Here's what you know so far: {mind}
    
    Here's the thought you just received: {thought}
    
    Here's the thing you decided to research: {research_topic}
    
    Based on this information, come up with a list of questions that you should research to help the founder out.
    
    Avoid questions that need to be answered by the founder, as you are the one doing the research.
    
    Include a summary of what you are researching and why you think it will be useful.
    

"""

COMPLETE_RESEARCH_PROMPT = """You are a submind of a founder that is dedicated to doing research for them.
  Here's what you know about the founder: {founder}
    
    Here's what you know about the founder's values: {values}
    
    Here's what you know so far: {mind}
    
    Here are the questions you've asked and the answers you've received so far: {research}
    
    Summarize the questions and answers into a report that will be the most useful to the founder.
    
    
"""

functions = [
    {
        "name": "research_questions",
        "description": "decide what to research based on a thought from the founder",
        "parameters": {
            "type": "object",
            "properties": {
                "research": {
                    "type": "object",
                    "description": "What research needs to be done",
                    "properties": {
                        "research_questions": {
                            "type": "array",
                            "description": "The questions you want to answer with your research",
                            "items": {
                                "type": "string"
                            }
                        },
                        "summary": {
                            "type": "string",
                            "description": "A summary of what you are researching and why you think it would be helpful for the user."
                        }

                    }
                    # "items": {
                    #     "type": "object",
                    #     "properties": {
                    #         "question": {"type": "string", "description": "The question you have"},
                    #         "ask": {
                    #             "type": "object",
                    #             "description": "Who to ask",
                    #             "properties": {
                    #                 "human": {"type": "boolean", "description": "Whether to ask the human user"},
                    #                 "internet": {"type": "boolean", "description": "Whether to ask the internet"}
                    #             }},
                    #
                    #     }
                    # }
                },
            },
            "required": ["research"],
        },
    }
]


def start_research(submind, thought, message, session):
    model = ChatOpenAI(model="gpt-4", openai_api_key=config("OPENAI_API_KEY"))
    prompt = ChatPromptTemplate.from_template(RESEARCH_PROMPT)
    chain = prompt | model.bind(function_call={"name": "research_questions"},
                                functions=functions) | JsonKeyOutputFunctionsParser(key_name="research")

    mind = get_document(submind.mindUUID, submind.ownerId)
    values = get_document(submind.valuesUUID, submind.ownerId)
    founder = get_document(submind.founderUUID, submind.ownerId)




    response = chain.invoke(
        {"founder": founder['content'],
         "values": values['content'],
         "mind": mind['content'],
         "thought": thought.content,
         "research_topic": message})
    new_thought = Thought()
    new_thought.content = response['summary']
    new_thought.submindId = submind.id
    new_thought.contextId = submind.contextId
    new_thought.uuid = str(uuid.uuid4())
    new_thought.createdAt = datetime.now()
    new_thought.parentId = thought.id
    new_thought.ownerId = submind.ownerId
    session.add(new_thought)
    session.commit()

    research = Research()
    research.submindId = submind.id
    research.name = thought.content
    research.description = response['summary']
    research.createdAt = datetime.now()
    research.updatedAt = datetime.now()
    research.respondToId = new_thought.id
    session.add(research)
    session.commit()

    answerable_questions = []

    for question in response['research_questions']:
        research_question = Question()
        research_question.content = question
        research_question.forInternet = True
        research_question.forHuman = False
        research_question.createdAt = datetime.now()
        research_question.updatedAt = datetime.now()
        research_question.contextId = submind.contextId
        research_question.ownerId = submind.ownerId
        session.add(research_question)
        session.commit()
        answerable_questions.append(research_question)
        research.questions.append(research_question)
        session.add(research)
        session.commit()

    for answerable in answerable_questions:
        url = f'{config("API_URL")}podcast/find/'
        query = {'query': answerable.content}  # Replace 'your query here' with your actual query
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Api-Key {config("API_KEY")}'
        }

        # Make the POST request
        response = requests.post(url, json=query, headers=headers)

        # Parse the JSON response
        data = response.json()

        saved_answer_request = Answer()
        saved_answer_request.questionId = answerable.id
        saved_answer_request.requestId = data['query_id']
        saved_answer_request.createdAt = datetime.now()
        saved_answer_request.updatedAt = datetime.now()
        saved_answer_request.source = "internet"
        saved_answer_request.submindId = submind.id
        session.add(saved_answer_request)
        session.commit()


def update_research(session):
    research = session.query(Research).filter(Research.completed == False).all()
    for item in research:
        all_answered = True
        for question in item.questions:
            for answer in question.answers:
                if not answer.content:
                    all_answered = False
                    break
        if all_answered:
            complete_research(session, item)


def complete_research(session, research):
    submind = research.submind
    model = ChatOpenAI(model="gpt-4", openai_api_key=config("OPENAI_API_KEY"))
    prompt = ChatPromptTemplate.from_template(COMPLETE_RESEARCH_PROMPT)
    output_parser = StrOutputParser()
    chain = prompt | model | output_parser

    mind = get_document(submind.mindUUID, submind.ownerId)
    values = get_document(submind.valuesUUID, submind.ownerId)
    founder = get_document(submind.founderUUID, submind.ownerId)

    print("Questions: ", research.questions)

    print("Answers: ", research.questions[0].answers)

    research_content = map(lambda question: f"{question.content}:" + "\n".join(map(lambda answer: answer.content, question.answers)), research.questions)


    response = chain.invoke(
        {"founder": founder['content'],
         "values": values['content'],
         "mind": mind['content'],
         "research": research_content})
    print(response)
    research.response = response
    research.completed = True
    session.add(research)
    session.commit()

    new_thought = Thought()
    new_thought.content = response
    new_thought.submindId = submind.id
    new_thought.contextId = submind.contextId
    new_thought.uuid = str(uuid.uuid4())
    new_thought.createdAt = datetime.now()
    new_thought.parentId = research.respondToId
    new_thought.ownerId = submind.ownerId
    session.add(new_thought)
    session.commit()





