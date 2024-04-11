import uuid

from decouple import config
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from submind.documents import create_report


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
