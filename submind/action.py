import uuid
from datetime import datetime

from decouple import config
from langchain.chains.llm import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories.mongodb import MongoDBChatMessageHistory
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers.openai_functions import JsonKeyOutputFunctionsParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI

from submind.models import Thought, Task
from submind.thoughts import find_related_thoughts

functions = [
    {
        "name": "classify_action",
        "description": "decide whether an action is long-term or short-term",
        "parameters": {
            "type": "object",
            "properties": {
                "classification": {
                    "type": "string",
                    "description": "The classification of the action",
                    "enum": ["long-term", "short-term"]

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
            "required": ["classification"],
        },
    },
{
        "name": "generate_tasks",
        "description": "A generator of tasks based on a plan",
        "parameters": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "description": "The tasks contained in the plan",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "The name of the task"},
                            "details": {"type": "string", "description": "The details of the task"},
                            "dependsOn": {"type": "array", "description": "The tasks the task depends on",
                                          "items": {
                                              "type": "string",
                                              "description": "The name of the task the task depends on"
                                          }
                                          },
                            "subtasks": {
                                "type": "array",
                                "description": "The subtasks of the task",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "The name of the subtask"
                                        },
                                        "details": {
                                            "type": "string",
                                            "description": "The details of the subtask"
                                        },
                                        "dependsOn": {
                                            "type": "array",
                                            "description": "The tasks the subtask depends on",
                                            "items": {
                                                "type": "string",
                                                "description": "The name of the task the task depends on"

                                            }
                                        }
                                    }
                                }
                            }
                        },
                    },
                    "required": ["tasks"],
                },
            }
        }
    }
]

CLASSIFY_ACTION_PROMPT = """
    You are an action classifier.
    
    Given an action, determine if it is long-term (will be executed/measured over multiple steps) 
    or a short-term action (will be executed/measured in a single step).
    
    Here is the action you need to classify: {action}
    

"""


def take_action(submind, session, thought, action):
    # First, decide whether this is a long-term or short-term action
    type_of_action = classify_action(action)
    if type_of_action == "long-term":
        long_term_action(submind, session, thought, action)
    else:
        short_term_action(submind, session, thought, action)


def classify_action(action):
    model = ChatOpenAI(model="gpt-4", openai_api_key=config("OPENAI_API_KEY"))
    prompt = ChatPromptTemplate.from_template(CLASSIFY_ACTION_PROMPT)
    chain = prompt | model.bind(function_call={"name": "classify_action"},
                                functions=functions) | JsonKeyOutputFunctionsParser(key_name="classification")

    return chain.invoke({"action": action})


def short_term_action(submind, session, thought, action):
    new_thought = Thought()
    new_thought.content = f"Looks like I should take this action: {action}. I am still learning to take actions right now, so I'll make a note of this and come back to it once I know how to do it."
    new_thought.submindId = submind.id
    new_thought.contextId = submind.contextId
    new_thought.uuid = str(uuid.uuid4())
    new_thought.createdAt = datetime.now()
    new_thought.parentId = thought.id
    new_thought.ownerId = submind.ownerId
    session.add(new_thought)
    session.commit()
    task = Task()
    task.name = action
    task.submindId = submind.id
    task.ownerId = submind.ownerId
    task.createdAt = datetime.now()
    task.updatedAt = datetime.now()
    task.thoughtId = new_thought.id
    task.uuid = str(uuid.uuid4())
    session.add(task)
    session.commit()
    return action


def long_term_action(submind, session, thought, action):
    plan = create_plan(submind, session, thought, action)
    new_thought = Thought()
    new_thought.content = f"Here is the plan of action that I have created for you: {plan}"
    new_thought.submindId = submind.id
    new_thought.contextId = submind.contextId
    new_thought.uuid = str(uuid.uuid4())
    new_thought.createdAt = datetime.now()
    new_thought.parentId = thought.id
    new_thought.ownerId = submind.ownerId
    session.add(new_thought)
    session.commit()
    task = Task()
    task.name = action
    task.submindId = submind.id
    task.ownerId = submind.ownerId
    task.createdAt = datetime.now()
    task.updatedAt = datetime.now()
    task.thoughtId = new_thought.id
    task.uuid = str(uuid.uuid4())
    session.add(task)
    session.commit()
    tasks = generate_tasks_from_plan(plan)
    for task in tasks:
        task_model = Task()
        task_model.name = task['name']
        task_model.details = task['details']
        task_model.dependsOn = task['dependsOn']
        task_model.submindId = submind.id
        task_model.ownerId = submind.ownerId
        task_model.createdAt = datetime.now()
        task_model.updatedAt = datetime.now()
        task_model.thoughtId = new_thought.id
        task_model.uuid = str(uuid.uuid4())
        session.add(task_model)
        session.commit()
        for subtask in task['subtasks']:
            subtask_model = Task()
            subtask_model.name = subtask['name']
            subtask_model.details = subtask['details']
            subtask_model.dependsOn = subtask['dependsOn']
            subtask_model.submindId = submind.id
            subtask_model.ownerId = submind.ownerId
            subtask_model.createdAt = datetime.now()
            subtask_model.updatedAt = datetime.now()
            subtask_model.thoughtId = new_thought.id
            subtask_model.uuid = str(uuid.uuid4())
            session.add(subtask_model)
            session.commit()

    return action


def create_plan(submind, session, thought, action):
    prompt = """
         You are a plan of action generator for a founder's submind. Given the founder's thought, your understanding of the long-term action 
          that is to be taken, and a few related thoughts, your job
            is to generate a markdown action plan that includes as much detail as possible to help the founder quickly and completely
            complete their task.       
    
        Here is the thought that you looked at: {thought}
        
        Here is the action that you think needs to be taken: {action}
        
        You have already determined that this is a long-term action that has multiple steps that must be evaluated.
        
        Here are thoughts from the founder that might be related: {related_thoughts}
        
        Given this information, create an action plan that will help the user accomplish this task.
        
        Provide some information about what metrics should be tracked in order to determine if the task is being completed.
        
        
    """


    model = ChatOpenAI(model="gpt-4", openai_api_key=config("OPENAI_API_KEY"))
    prompt_template = ChatPromptTemplate.from_template(prompt)
    output_parser = StrOutputParser()
    chain = prompt_template | model | output_parser
    related_thoughts = find_related_thoughts(submind, f'{thought.content} {action}')
    print(related_thoughts)
    response = chain.invoke({
        "thought": thought,
        "action": action,
        "related_thoughts": "\n".join(map(lambda x: x.page_content, related_thoughts)),
    })




    return response


def generate_tasks_from_plan(plan):
    template = """
           You are an expert in task identification and relations.

           Your job is to identify the tasks and their subtasks from the plan, and the dependencies between them. 
           You should return the tasks and their subtasks in the following JSON format:
           {{
               "tasks": [
                   {{
                       "name": "<short name of the task>",
                       "details": "<details of the task>",
                       "dependsOn": ["<short name of the task>", "<short name of the task>"],
                       "subtasks": [
                           {{
                               "name": "<short name of the subtask>",
                               "details": "<details of the subtask>"
                               "dependsOn": ["<short name of the subtask>", "<short name of the subtask>"],
                           }}
                       ]
                   }}
               ]
           }}

           Here's the message: {input}
           """
    prompt = ChatPromptTemplate.from_template(template=template)
    model = ChatOpenAI(api_key=config("OPENAI_API_KEY"), model_name="gpt-4")
    chain = prompt | model.bind(function_call={"name": "generate_tasks"},
                                functions=functions) | JsonKeyOutputFunctionsParser(
        key_name="tasks")
    response = chain.invoke({"input": plan})
    print("task plan tasks", response)
    return response