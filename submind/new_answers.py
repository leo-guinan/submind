import re

import requests
from decouple import config
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy import and_, or_

from submind.models import Answer


def pull_new_answers(session, submind):
    new_answers = []

    unanswered_questions = session.query(Answer).filter(
        and_(or_(Answer.content == '', Answer.content.is_(None)), Answer.submindId == submind.id)).all()
    print(f'Unanswered questions for submind {submind.id}: {len(unanswered_questions)}')
    errored_answers = []
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
        if data['status'] != 'Completed':
            print("Query still running. Skipping")
            continue
        if data['error']:
            errored_answers.append(question)
            continue
        # print(f"Found {len(data['results'])} snippets")

        ANSWER_TEMPLATE = """You are a recursive answer compiler. Given a question, your answer so far, and a new snippet,
         your job is to revise your answer with the information in the new snippet. 



        """

        HUMAN_MESSAGE_TEMPLATE = """ Here is the question: {question}
        
        Here is your answer so far: {answer}

        Here is the next snippet: {snippet}"""
        model_35 = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=config("OPENAI_API_KEY"))
        model_4 = ChatOpenAI(model="gpt-4-turbo", openai_api_key=config("OPENAI_API_KEY"))
        model_claude = ChatAnthropic(model_name="claude-3-haiku-20240307",
                                     anthropic_api_key=config("ANTHROPIC_API_KEY"))
        prompt = ChatPromptTemplate.from_messages([("system", ANSWER_TEMPLATE), ("human", HUMAN_MESSAGE_TEMPLATE)])
        output_parser = StrOutputParser()
        current_answer = ""
        for snippet in data['results']:

            try:
                chain = prompt | model_claude | output_parser
                # remove all timestamps in [] brackets
                cleaned_text = re.sub(r'\[\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\]', '',
                                      snippet['snippet'])
                current_answer = chain.invoke(
                    {"question": question.question.content,
                     "answer": current_answer,
                     "snippet": cleaned_text
                     })
            except Exception as e:
                try:
                    print("Failed to get answer from claude-3-haiku-20240307, using gpt-3.5-turbo")
                    print(e)
                    chain = prompt | model_35 | output_parser
                    # remove all timestamps in [] brackets
                    cleaned_text = re.sub(r'\[\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\]', '',
                                          snippet['snippet'])

                    current_answer = chain.invoke(
                        {"question": question.question.content,
                         "answer": current_answer,
                         "snippet": cleaned_text
                         })
                except Exception as e2:
                    try:
                        print("Failed to get answer from gpt-3.5-turbo, using gpt-4-turbo")
                        print(e2)
                        chain = prompt | model_4 | output_parser
                        # remove all timestamps in [] brackets
                        cleaned_text = re.sub(r'\[\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\]', '',
                                              snippet['snippet'])

                        current_answer = chain.invoke(
                            {"question": question.question.content,
                             "answer": current_answer,
                             "snippet": cleaned_text
                             })

                    except Exception as e3:
                        print("Failed to get answer")
                        print(e3)
                        continue
        question.content = current_answer
        session.add(question)
        session.commit()
        new_answers.append(f'{question.question.content}\n{current_answer}')
    print(f'New answers for submind {submind.id}: {len(new_answers)}')
    print(f'Errored answers for submind {submind.id}: {len(errored_answers)}')
    for err in errored_answers:
        print(f'Error for question {err.question.content}')
        err.content = "Error getting answer from API"
        err.question.error = "Error getting answer from API"
        session.add(err)
        session.commit()
    return new_answers
