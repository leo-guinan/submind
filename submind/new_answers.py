import time

import requests
from decouple import config
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import and_, or_

from submind.models import Answer


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