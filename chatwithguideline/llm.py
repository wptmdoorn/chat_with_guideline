from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.conversational_retrieval.prompts import CONDENSE_QUESTION_PROMPT, QA_PROMPT
from langchain.prompts.prompt import PromptTemplate

prompt_template = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer.

{context}

Question: {question}
Helpful Answer:"""
prompt = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)


# we can adjust the prompt with the following:
# see stuff_prompt.py
# that should be used as QA prompt

def create_llm(embedding_dir: str) -> ConversationalRetrievalChain:
    vectordb = Chroma(embedding_function=OpenAIEmbeddings(),
                      persist_directory=f'embeddings/{embedding_dir}')

    memory = ConversationBufferMemory(
        memory_key="chat_history", return_messages=True, output_key='answer')
    doc_chain = load_qa_chain(OpenAI(model_name='gpt-3.5-turbo'),
                              chain_type="stuff", prompt=QA_PROMPT)
    llm = ConversationalRetrievalChain.from_llm(
        llm=ChatOpenAI(model_name='gpt-3.5-turbo'),
        return_source_documents=True,
        # combine_docs_chain_kwargs={"prompt": prompt},
        retriever=vectordb.as_retriever(
            search_kwargs={"k": 3},
            memory=memory,)
    )

    return llm
