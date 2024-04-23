import uuid
from datetime import datetime

from decouple import config
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from submind.models import Thought
from submind.thoughts import find_related_thoughts

REFLECTION_PROMPT = """
    You are the submind of a founder. 
    
    Your job is to align your values with them as much as possible and help them out in any way you can.
    
    Here's what you know about the founder: {founder}
    
    From interacting with the founder, you have learned these values so far: {values}
    
    Here's your current state of mind: {mind}
    
    Here are potentially related thoughts you remember: {related_thoughts}

    Based on this thought: {thought} and this reasoning: {reasoning}, respond with what you know.
    
    
    If you don't know anything about this, say so.
    
    

"""

def reflect(submind, session, thought, message):
    model = ChatOpenAI(model="gpt-4", openai_api_key=config("OPENAI_API_KEY"))
    prompt = ChatPromptTemplate.from_template(REFLECTION_PROMPT)
    output_parser = StrOutputParser()
    chain = prompt | model | output_parser
    related_thoughts = find_related_thoughts(submind, f'{thought.content} {message}')
    print(related_thoughts)
    response =  chain.invoke({
        "founder": submind.ownerId,
        "values": submind.valuesUUID,
        "mind": submind.mindUUID,
        "related_thoughts": "\n".join(map(lambda x: x.page_content, related_thoughts)),
        "thought": thought,
        "reasoning": message
    })
    print(response)

    new_thought = Thought()
    new_thought.content = response
    new_thought.submindId = submind.id
    new_thought.contextId = submind.contextId
    new_thought.uuid = str(uuid.uuid4())
    new_thought.createdAt = datetime.now()

    new_thought.parentId = thought.id
    new_thought.ownerId = submind.ownerId
    session.add(new_thought)
    session.commit()