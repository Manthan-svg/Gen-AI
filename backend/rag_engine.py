import os
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain 
from dotenv import load_dotenv
from ingestor import DataIngestor

load_dotenv()

class DeepContextEngine:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_db = Chroma(
            persist_directory="./chroma_db",
            embedding_function=self.embeddings
        )
        
        self.llm = ChatGroq(
            temperature=0, 
            model_name="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        
    def run_engine(self):
        ingestion = DataIngestor()
        dataFolder = "./data"
        
        exsiting_docs = self.vector_db.get()
        
        unique_docs = set(doc.get("source_name") for doc in exsiting_docs["metadatas"])
        
        for fileName in os.listdir(dataFolder):
            if fileName in unique_docs:
                print(f"⏩ Skipping {fileName} (Already in memory)")
                continue
            
            
            file_path = os.path.join(dataFolder,fileName)
            
            chunks = ingestion.ingestion_documents(file_path)
            
            if chunks:
                ids = [f"{fileName}_{i}" for i in range(len(chunks))]
                self.vector_db.add_documents(chunks, ids=ids)
                
        
    # Step 2 - Answer question from stored knowledge
    def get_answer(self, user_question: str):
        system_prompt = (
            "You are an expert knowledge assistant for a distributed team. "
            "Use the provided context to answer the user's question. "
            "If you don't know the answer based on the context, say you don't know. "
            "Context: {context}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])
        
        question_answer_chain = create_stuff_documents_chain(self.llm, prompt)
        retriever = self.vector_db.as_retriever(search_kwargs={"k": 15})
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        
        response = rag_chain.invoke({"input": user_question})
        return response
    