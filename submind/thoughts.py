import time
import uuid
from datetime import datetime

import requests
from decouple import config
from langchain.embeddings import OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_community.output_parsers.ernie_functions import JsonKeyOutputFunctionsParser
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from sqlalchemy import and_, or_

from submind.documents import get_document, update_document, create_document, create_report
from submind.models import Thought, Question, Answer

functions = [
    {
        "name": "identify_questions",
        "description": "An identifier of questions",
        "parameters": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "description": "The questions you have about the work you are doing",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string", "description": "The question you have"},
                            "ask": {
                                "type": "object",
                                "description": "Who to ask",
                                "properties": {
                                    "human": {"type": "boolean", "description": "Whether to ask the human user"},
                                    "internet": {"type": "boolean", "description": "Whether to ask the internet"}
                                }},

                        }
                    }
                },
            },
            "required": ["questions"],
        },
    }
]


#
#
# def classify_command(command):
#     template = """
#     You are a message classifier.
#     Determine whether the following message is a statement, a question, or a command.
#     Respond in JSON format like this:
#     {{
#         "classification": "statement"
#     }}
#
#     Here's the message: {input}
#     """
#     prompt = ChatPromptTemplate.from_template(template=template)
#     model = ChatOpenAI(api_key=config("OPENAI_API_KEY"), model_name="gpt-4")
#     chain = prompt | model.bind(function_call={"name": "classify"}, functions=functions) | JsonKeyOutputFunctionsParser(
#         key_name="classification")
#     response = chain.invoke({"input": command})
#     print(response)
#     return response

def pull_new_answers(session, submind):
    new_answers = []
    try:
        unanswered_questions = session.query(Answer).filter(
            and_(or_(Answer.content == '', Answer.content.is_(None)), Answer.submindId == submind.id)).all()

        for question in unanswered_questions:
            url = f'{config("API_URL")}podcast/query/'
            query = {'query_id': question.requestId}
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Api-Key {config("API_KEY")}'
            }

            # Make the POST request
            response = requests.post(url, json=query, headers=headers)

            data = response.json()

            ANSWER_TEMPLATE = """You are an answer compiler. Given a question and a list of relevant snippets, your job is to compile a coherent answer that addresses the question as completely as possible.
            
           
            
            """

            HUMAN_MESSAGE_TEMPLATE = """ Here is the question: {question}
            
            Here are the snippets: {snippets}"""
            # model = ChatOpenAI(model="gpt-4", openai_api_key=config("OPENAI_API_KEY"))
            model = ChatAnthropic(model_name="claude-3-haiku-20240307", anthropic_api_key=config("ANTHROPIC_API_KEY"))
            prompt = ChatPromptTemplate.from_messages([("system", ANSWER_TEMPLATE), ("human", HUMAN_MESSAGE_TEMPLATE)])
            output_parser = StrOutputParser()
            chain = prompt | model | output_parser
            combined_answer = chain.invoke(
                {"question": question.question.content,
                 "snippets": "\n".join(map(lambda x: x['snippet'], data['results']))})

            print(combined_answer)
            question.content = combined_answer
            session.add(question)
            session.commit()
            new_answers.append(f'{question.question.content}\n{combined_answer}')
            # rate limit is for every 60 seconds, so wait slightly longer than that to make sure.
            time.sleep(65)
    except Exception as e:
        # hit the rate limit most likely. Just print the message and move on,
        # because the next one will be picked up the following run.
        print(e)
    return new_answers


def final_run(session, submind, document, mind, ):
    PROMPT_TEMPLATE = """You are a powerful submind that allows your human to externalize their thought process.
    
   Here is what your name is: {submind_name}
    And a description: {submind_description}
    
    Here was the document they created to give you your directives: {submind_document}
    
    Here is what you've figured out so far: {submind_mind}
    
    After learning everything you could, you now need to compile a report that contains your final findings.    
    
    
    """

    model = ChatOpenAI(model="gpt-4", openai_api_key=config("OPENAI_API_KEY"))
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    output_parser = StrOutputParser()
    chain = prompt | model | output_parser
    report = chain.invoke({"submind_name": submind.name, "submind_description": submind.description,
                           "submind_document": document,
                           "submind_mind": mind, "related_thoughts": "\n".join(
            map(lambda x: x.content, submind.relatedThoughts))})
    print(report)
    create_report(submind.ownerId, report, str(uuid.uuid4()))
    submind.status = "COMPLETED"
    session.add(submind)
    session.commit()


def find_related_thoughts(submind, session):
    new_answers = pull_new_answers(session, submind)
    human_answers = session.query(Answer).filter(Answer.submindId == submind.id, Answer.source == "user").all()
    combined_answers = new_answers + list(map(lambda x: f'{x.question.content}: {x.content}', human_answers))

    pc = Pinecone(api_key=config("PINECONE_API_KEY"))
    embeddings = OpenAIEmbeddings(openai_api_key=config("OPENAI_API_KEY"))

    index = pc.Index(config("PINECONE_INDEX_NAME"), host=config("PINECONE_HOST"))
    vectorstore = PineconeVectorStore(index, embeddings, "text", namespace=config('PINECONE_NAMESPACE'))

    # figure out what things might be related.

    PROMPT_TEMPLATE = """You are a powerful submind that allows your human to externalize their thought process.
    
    Here is what your name is: {submind_name}
    And a description: {submind_description}
    
    Here was the document they created to give you your directives: {submind_document}
    
    Here is what you've figured out so far: {submind_mind}
    
    Here are the new answers you've received to previously asked questions: {new_answers}
    
    Based on this information, what things do you wish you knew more about? What would make it easier to accomplish your directive?
    
    
    """
    model = ChatOpenAI(model="gpt-4", openai_api_key=config("OPENAI_API_KEY"))

    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    output_parser = StrOutputParser()
    chain = prompt | model | output_parser

    fetched_document = get_document(submind.documentUUID, submind.ownerId)
    fetched_mind = get_document(submind.mindUUID, submind.ownerId)
    if not fetched_mind:
        fetched_mind = create_document(submind.ownerId, "", str(uuid.uuid4()))

    if submind.lastRun and datetime.now() > submind.lastRun:
        final_run(session, submind, fetched_document['content'], fetched_mind['content'])
        return

    things_to_lookup = chain.invoke({"submind_name": submind.name, "submind_description": submind.description,
                                     "submind_document": fetched_document['content'],
                                     "submind_mind": fetched_mind['content'],
                                     "new_answers": "\n".join(combined_answers) if combined_answers else ""})
    # record answer as a new thought
    new_thought = Thought()
    new_thought.ownerId = submind.ownerId
    new_thought.content = things_to_lookup
    new_thought.submindId = submind.id
    new_thought.uuid = str(uuid.uuid4())
    new_thought.contextId = submind.contextId
    new_thought.createdAt = datetime.now()
    session.add(new_thought)
    session.commit()
    print(things_to_lookup)
    res = vectorstore.similarity_search_with_score(things_to_lookup, k=10,
                                                   filter={"type": "thought", "userId": submind.ownerId})
    # submind may or may not already have related thoughts included. Need to dedupe the results
    print(f'Related thoughts: {submind.relatedThoughts}')
    for thought, score in res:
        print(f"The thought is: {thought}")
        print(score)
        if score < 0.7:
            continue
        # check if the thought is already included in the submind's mind
        if thought.metadata['thoughtId'] in map(lambda x: x.id, submind.relatedThoughts):
            continue

        thought_object = session.query(Thought).filter(Thought.id == thought.metadata['thoughtId']).first()
        if thought_object:
            submind.relatedThoughts.append(thought_object)
            session.add(submind)
            session.commit()

    UPDATE_MIND_PROMPT = """You are a powerful submind that allows your human to externalize their thought process.
    Here is what your name is: {submind_name}
    And a description: {submind_description}
    
    Here was the document they created to give you your directives: {submind_document}
    
    Here is your current state : {submind_mind}
    
    Here are the user's related thoughts that you've uncovered: {related_thoughts}
    
    Based on this information, update your state to reflect what you've learned.

    
    """

    update_chain = ChatPromptTemplate.from_template(UPDATE_MIND_PROMPT) | model | output_parser
    updated_mind = update_chain.invoke({"submind_name": submind.name, "submind_description": submind.description,
                                        "submind_document": fetched_document['content'],
                                        "submind_mind": fetched_mind['content'], "related_thoughts": "\n".join(
            map(lambda x: x.content, submind.relatedThoughts))})

    fetched_mind['content'] = updated_mind
    submind.mindUUID = fetched_mind['uuid']
    session.add(submind)
    session.commit()
    update_document(submind.mindUUID, updated_mind)

    questions = session.query(Question).filter(Question.submindId == submind.id).all()
    existing_answers = session.query(Answer).filter(Answer.submindId == submind.id).all()
    open_questions = list(filter(lambda x: not any(map(lambda y: y.questionId == x.id, existing_answers)), questions))

    QUESTIONS_MIND_PROMPT = """You are a powerful submind that allows your human to externalize their thought process.
        Here is what your name is: {submind_name}
        And a description: {submind_description}

        Here was the document they created to give you your directives: {submind_document}

        Here is your current state : {submind_mind}

        Here are the user's related thoughts that you've uncovered: {related_thoughts}
        
        Here are the currently open questions that haven't been answered yet: {open_questions}

        Based on this information, what questions would you like answered? Don't ask any questions that are duplicates of the currently open questions.
         And should those questions be answered by the user or by research?
        


        """
    question_prompt = ChatPromptTemplate.from_template(QUESTIONS_MIND_PROMPT)

    question_chain = question_prompt | model.bind(function_call={"name": "identify_questions"},
                                                  functions=functions) | JsonKeyOutputFunctionsParser(
        key_name="questions")
    response = question_chain.invoke({
        "submind_name": submind.name,
        "submind_description": submind.description,
        "submind_document": fetched_document['content'],
        "submind_mind": fetched_mind['content'],
        "related_thoughts": "\n".join(map(lambda x: x.content, submind.relatedThoughts)),
        "open_questions": "\n".join(map(lambda x: x.content, open_questions))
    })

    answerable_questions = []

    for question in response:
        new_question = Question()
        new_question.ownerId = submind.ownerId
        new_question.contextId = submind.contextId
        new_question.submindId = submind.id
        new_question.content = question['question']
        new_question.forHuman = question['ask']['human']
        new_question.forInternet = question['ask']['internet']
        new_question.createdAt = datetime.now()
        new_question.updatedAt = datetime.now()

        session.add(new_question)
        session.commit()
        if new_question.forInternet:
            answerable_questions.append(new_question)

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
