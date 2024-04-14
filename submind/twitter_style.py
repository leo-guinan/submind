import uuid
from datetime import datetime

from decouple import config
from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers.openai_functions import JsonKeyOutputFunctionsParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from submind.documents import get_or_create_document
from submind.models import Like, Thought, Task
from submind.research import start_research

functions = [
    {
        "name": "respond_to_thought",
        "description": "respond to a thought from the founder",
        "parameters": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "object",
                    "description": "The questions you have about the work you are doing",
                    "properties": {
                        "responseType": {
                            "type": "string",
                            "description": "The type of response you want to give",
                            "enum": ["research", "question", "action"]

                        },
                        "message": {
                            "type": "string",
                            "description": "The message you want to send"
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
            "required": ["response"],
        },
    }
]

SUBMIND_INITIAL_PROMPT = """
    You are the submind of a founder. 
    
    Your job is to align your values with them as much as possible and help them out in any way you can.
    
    Here's what you know about the founder: {founder}
    
    From interacting with the founder, you have learned these values so far: {values}
    
    Here's your current state of mind: {mind}
    
    You have just received a thought from the founder: {thought}
    
    Based on this thought, your shared values, and your current state of mind, what do you think your next action should be?
    
    You can research something to find out more about it, ask a question to clarify something, or take an action to help the founder.
    
    Respond with one of these options: research, question, action, and a message that explains your choice. Return json with fields "type" and "message".
"""


def twitter_style_submind_run(submind, session):
    founder = get_or_create_document(submind.ownerId, "You don't know anything about the founder yet",
                                     submind.founderUUID if submind.founderUUID else str(uuid.uuid4()))
    values = get_or_create_document(submind.ownerId, "You don't know anything about the founder's values yet",
                                    submind.valuesUUID if submind.valuesUUID else str(uuid.uuid4()))
    mind = get_or_create_document(submind.ownerId, "You don't know anything about the founder's mind yet",
                                    submind.mindUUID if submind.mindUUID else str(uuid.uuid4()))

    model = ChatOpenAI(model="gpt-4", openai_api_key=config("OPENAI_API_KEY"))
    prompt = ChatPromptTemplate.from_template(SUBMIND_INITIAL_PROMPT)
    chain = prompt | model.bind(function_call={"name": "respond_to_thought"},
                                functions=functions) | JsonKeyOutputFunctionsParser(key_name="response")

    for thought in submind.pendingThoughts:
        like = Like()
        like.thoughtId = thought.id
        like.submindId = submind.id
        like.createdAt = datetime.now()
        session.add(like)
        session.commit()

        report = chain.invoke({
            "founder": founder['content'],
            "values": values['content'],
            "mind": mind['content'],
            "thought": thought.content

        })
        print(report['responseType'])
        if report['responseType'] == "research":
            start_research(submind, thought, report['message'], session)

        elif report['responseType'] == "question":
            # Ask a question
            new_thought = Thought()
            new_thought.content = report['message']
            new_thought.submindId = submind.id
            new_thought.contextId = submind.contextId
            new_thought.uuid = str(uuid.uuid4())
            new_thought.createdAt = datetime.now()
            new_thought.parentId = thought.id
            new_thought.ownerId = submind.ownerId
            session.add(new_thought)
            session.commit()

        elif report['responseType'] == "action":
            new_thought = Thought()
            new_thought.content = f"Looks like I should take this action: {report['message']}. I am still learning to take actions right now, so I'll make a note of this and come back to it once I know how to do it."
            new_thought.submindId = submind.id
            new_thought.contextId = submind.contextId
            new_thought.uuid = str(uuid.uuid4())
            new_thought.createdAt = datetime.now()
            new_thought.parentId = thought.id
            new_thought.ownerId = submind.ownerId
            session.add(new_thought)
            session.commit()
            task = Task()
            task.name = report['message']
            task.submindId = submind.id
            task.ownerId = submind.ownerId
            task.createdAt = datetime.now()
            task.updatedAt = datetime.now()
            task.thoughtId = new_thought.id
            task.uuid = str(uuid.uuid4())
            session.add(task)
            session.commit()
            # Take an action

        submind.pendingThoughts.remove(thought)
        session.add(submind)
        session.commit()


    # {"type": "question", "message": "Could you please clarify what specific functionality or feature you would like to be implemented or improved in our application?"}

