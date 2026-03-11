import os
from re import search
from typing import List
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain 
from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import MessagesPlaceholder 
from dotenv import load_dotenv
from ingestor import DataIngestor

load_dotenv()

class DeepContextEngine:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(current_dir,"chroma_db")
        
        self.vector_db = Chroma(
            persist_directory=self.db_path,
            embedding_function=self.embeddings
        )

        self.llm = ChatGroq(
            temperature=0, 
            model_name="llama-3.1-8b-instant",
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
                
        
    def _normalize_chat_history(self, chat_history: List):
        if not chat_history:
            return []
        normalized = []
        for item in chat_history:
            # Accept (role, content) or (role, content, sources)
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                normalized.append((item[0], item[1]))
                continue
            # Accept {"role": "...", "content": "..."}
            if isinstance(item, dict) and "role" in item and "content" in item:
                normalized.append((item["role"], item["content"]))
        return normalized
    # Step 2 - Answer question from stored knowledge
    def _reload_vector_db(self):
        # Reopen the persistent collection so this process sees new ingestions
        self.vector_db = Chroma(
            persist_directory=self.db_path,
            embedding_function=self.embeddings
        )

    def _try_persist(self):
        # Support different Chroma/LangChain versions
        if hasattr(self.vector_db, "persist"):
            self.vector_db.persist()
            return
        client = getattr(self.vector_db, "_client", None)
        if client is not None and hasattr(client, "persist"):
            client.persist()

    def get_answer(self, user_question: str, user_dept: str, chat_history: List = None):
        # Ensure this process sees newly ingested docs
        self._reload_vector_db()
        safe_history = self._normalize_chat_history(chat_history)
        # 1. Manual Retrieval with Scores (Already in your code)
        docs_with_scores = self.vector_db.similarity_search_with_score(
            user_question,
            k=5,
            filter={"department": user_dept}    
        )
        
        # 2. Filter for quality (Already in your code)
        valid_docs = [doc for doc, score in docs_with_scores if score < 3.2]

        if not valid_docs:
            return {
                "answer": "I'm sorry, I couldn't find any information in the documents regarding your question.",
                "sources": []
            }

        # 3. Handle Contextualization (Stand-alone question logic)
        contextualize_q_system_prompt = (
            "Given a chat history and the latest user question, "
            "formulate a standalone question. Do NOT answer it."
        )
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}") 
        ])
        
        # Generate the standalone question
        standalone_question_chain = contextualize_q_prompt | self.llm
        standalone_q_response = standalone_question_chain.invoke({
            "input": user_question, 
            "chat_history": safe_history
        })
        standalone_q = standalone_q_response.content

        # 4. Use the valid_docs DIRECTLY in the answer chain
        system_prompt = (
            "You are a Corporate Integrity AI. Use the provided context to answer. "
            "STRICT RULE: Do not mention 'Source: None' or try to list sources in your text. "
            "The system UI will handle citations automatically. "
            "Answer ONLY based on the facts provided. If unsure, say you don't know."
            "\n\nContext: {context}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        
        # We invoke the answer chain using OUR valid_docs as the 'context'
        question_answer_chain = create_stuff_documents_chain(self.llm, prompt)
        
        # Notice we are NOT using rag_chain.invoke()
        answer = question_answer_chain.invoke({
            "input": standalone_q,
            "chat_history": safe_history,
            "context": valid_docs # This ensures only filtered docs are used!
        })
        
        # 5. Build Sources from valid_docs
        sources = []
        for doc in valid_docs:
            sources.append({
                "source": doc.metadata.get("source_name", "Unknown"),
                "page": doc.metadata.get("page", "N/A"),
                "content_preview": doc.page_content[:100] + "...."
            })
            
        return {
            "answer": answer,
            "sources": sources
        }

    
