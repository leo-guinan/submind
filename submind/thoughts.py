from decouple import config
from langchain.embeddings import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

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


def find_related_thoughts(submind, related_to):
    # new_answers = pull_new_answers(session, submind)
    # human_answers = session.query(Answer).filter(Answer.submindId == submind.id, Answer.source == "user").all()
    # combined_answers = new_answers + list(map(lambda x: f'{x.question.content}: {x.content}', human_answers))

    pc = Pinecone(api_key=config("PINECONE_API_KEY"))
    embeddings = OpenAIEmbeddings(openai_api_key=config("OPENAI_API_KEY"))

    index = pc.Index(config("PINECONE_INDEX_NAME"), host=config("PINECONE_HOST"))
    vectorstore = PineconeVectorStore(index, embeddings, "text", namespace=config('PINECONE_NAMESPACE'))

    thoughts_to_return = []

    res = vectorstore.similarity_search_with_score(related_to, k=10,
                                                   filter={"type": "thought", "userId": submind.ownerId})
    for thought, score in res:
        if score < 0.85:
            continue
        thoughts_to_return.append(thought)

    return thoughts_to_return
