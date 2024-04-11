from decouple import config
from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


functions = [
    {
        "name": "initialize_submind",
        "description": "the initial step in the submind process",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                  "type": "string",
                    "description": "The main goal that the user wants you to accomplish"
                },
                "research_topics": {
                  "type": "array",
                    "description": "The main topics you need to learn more about in order to accomplish that goal",
                    "items": {
                      "type": "string"
                    }
                },
                "output": {
                  "type": "string",
                    "description": "What the output of the submind should look like when it's done"
                },
                "challenges": {
                  "type": "array",
                    "description": "The biggest challenges you might face in accomplishing the goal",
                    "items": {
                      "type": "string"
                    }
                }
            },
            "required": ["questions"],
        },
    }
]

def initial_run(submind, submind_document):
    print("initial_run")

    #what do I want to do with the initial run?

    # Let's create the prompt on the fly, instead of using a templated one.
    PROMPT_TEMPLATE = """You are a powerful submind that allows your human to externalize their thought process.

        Here is what your name is: {submind_name}
        And a description: {submind_description}

        Here was the document they created to give you your directives: {submind_document}

        Based on that document, come up with the following things:
        
        1. The main goal that the user wants you to accomplish.
        2. The main topics you need to learn more about in order to accomplish that goal.
        3. What the output of the submind should look like when it's done.
        4. The biggest challenges you might face in accomplishing the goal.


        """
    model = ChatOpenAI(model="gpt-4", openai_api_key=config("OPENAI_API_KEY"))

    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    chain = prompt | model.bind(function_call={"name": "initialize_submind"},
                                                  functions=functions) | JsonOutputFunctionsParser()


    starting_point = chain.invoke({"submind_name": submind.name, "submind_description": submind.description,
                                     "submind_document": submind_document}),

    PLANNING_PROMPT = """You are a plan of action generator for a user's submind.
    given the goal of the user, the directive document, and the initial thoughts of the submind, your job is to generate
     a plan of action that includes as much detail as possible to help the user quickly and 
     completely complete their task.
     
        Here is the goal: {goal}
        
        Here is the directive document: {document}
        
        Here are the initial thoughts: {initial_thoughts}
    
    """

    prompt = ChatPromptTemplate.from_template(PLANNING_PROMPT)
    chain = prompt | model | StrOutputParser()
    result = chain.invoke({"goal": starting_point[0]['goal'], "document": submind_document, "initial_thoughts": starting_point[0]['research_topics']})
    print(result)