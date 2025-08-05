import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain

load_dotenv()

st.title("RAG Application with Gemini API")

# PDF'den veri yükleme ve parçalama
loader = PyPDFLoader("mypdf.pdf")
data = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
docs = text_splitter.split_documents(data)

# Embedding ve Vectorstore
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
vectorstore = Chroma.from_documents(
    documents=docs,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 10})

# LLM tanımı
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    max_tokens=500
)

# Chat arayüzünden kullanıcı girdisi al
query = st.chat_input("Sorunuzu buraya yazın:")

# Sistem promptu ve template
system_prompt = (
    "You are an assistant for question-answering tasks.\n"
    "Use the following pieces of retrieved context to answer.\n"
    "If you don't know the answer, say you don't know.\n"
    "Use three sentences maximum and keep the answer concise and correct.\n\n"
    "{context}"
)

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}")
])

# Kullanıcı bir soru yazdıysa işle
if query:
    with st.spinner("Yanıtlanıyor..."):
        question_answer_chain = create_stuff_documents_chain(llm, prompt_template)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        response = rag_chain.invoke({"input": query})
        st.write("**Yanıt:**")
        st.write(response["answer"])
