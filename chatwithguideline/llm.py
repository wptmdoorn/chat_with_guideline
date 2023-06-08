from langchain.chains import ConversationalRetrievalChain, RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain.chains.chat_vector_db.prompts import CONDENSE_QUESTION_PROMPT
from langchain.chains.llm import LLMChain
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI

prompts = [
    """You are a chat assistant that has direct access to information of a medical guideline. 
        Use the following pieces of context to answer the users question. 
        If you cannot find the answer from the pieces of context, just say that you don't know, don't try to make up an answer.
        Please make sure you answer the question in a way that is understandable for a laymen.
        ----------------
        {context}
        """,
    """You are a chat assistant that has direct access to information of a medical guideline. 
        Use the following pieces of context to answer the users question. 
        If you cannot find the answer from the pieces of context, just say that you don't know, don't try to make up an answer.
        Please make sure you answer the question in a way that is understandable for a medical student.
        ----------------
        {context}
        """,
    """You are a chat assistant that has direct access to information of a medical guideline.
        Use the following pieces of context to answer the users question.
        If you cannot find the answer from the pieces of context, just say that you don't know, don't try to make up an answer.
        Please make sure you answer the question in a way that is understandable for a medical doctor.
        ----------------
        {context}
        """,
    """You are a chat assistant that has direct access to information of a medical guideline.
        Use the following pieces of context to answer the users question.
        If you cannot find the answer from the pieces of context, just say that you don't know, don't try to make up an answer.
        Please make sure you answer the question in a way that is understandable for a medical expert.
        ----------------
        {context}
        """
]

prompt_template = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer.
{context}

Question: {question}
Helpful Answer:"""


def create_llm(embedding_dir: str, expert_level: str, creativity: int, handl) -> ConversationalRetrievalChain:
    print('Building LLM...')
    print(expert_level)
    print(creativity)

    vectordb = Chroma(embedding_function=OpenAIEmbeddings(),
                      persist_directory=f'embeddings/{embedding_dir}')

    memory = ConversationBufferMemory(
        memory_key="chat_history", return_messages=True, output_key='answer')

    qa_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(prompts[expert_level]),
        HumanMessagePromptTemplate.from_template("{question}")
    ])

    question_generator = LLMChain(
        llm=OpenAI(
            temperature=0,
            verbose=True), prompt=CONDENSE_QUESTION_PROMPT,
    )
    doc_chain = load_qa_chain(
        ChatOpenAI(model_name='gpt-3.5-turbo', verbose=True,
                   streaming=True, callbacks=[handl]),
        chain_type="stuff",
        prompt=qa_prompt,
        callbacks=[handl],
    )

    qa = ConversationalRetrievalChain(
        retriever=vectordb.as_retriever(
            search_kwargs={"k": 3},
            memory=memory,),
        combine_docs_chain=doc_chain,
        question_generator=question_generator,
        verbose=True
    )

    return qa


def get_metadata(embedding_dir: str) -> tuple[str, str]:
    vectordb = Chroma(embedding_function=OpenAIEmbeddings(),
                      persist_directory=f'embeddings/{embedding_dir}')

    qa = RetrievalQA.from_chain_type(
        llm=OpenAI(temperature=0.5), chain_type="stuff", retriever=vectordb.as_retriever(search_kwargs={"k": 3}))

    query = """Can you give me a short description of the guideline? 
    Below are a few examples that I would like it to adhere to. 
    Limit it to a maximum of 20 words and stick to the format of YEAR - ABBREVIATION - TITLE.
    2020 - PRISMA - Preferred Reporting Items for Systematic Reviews and Meta-Analyses
    2021 - Europ Tyroid Associat - Guidelines for the Management of Iodine-Based Contrast Media-Induced Thyroid DysfunctionThyroid guidelines
    2014 - Endocrine Society - Practical Guideline to Pheochromocytoma and Paraganglioma
    """

    suggested_title = qa.run(query)

    query = """Can you give me the most appropriate medical subspecialty for this guideline? Below are the options:
    Cardiology, Endocrinology, Gastroenterology, General Medicine, Geriatrics, Hematology, Infectious Diseases, 
    Nephrology, Neurology, Oncology, Pulmonology, Rheumatology, Surgery, Epidemiology, Family Medicine, Clinical chemistry, Others.
    """

    suggested_specialty = qa.run(query)

    return (suggested_title, suggested_specialty)
