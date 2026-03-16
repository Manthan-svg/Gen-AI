import os
import re
from typing import List
from langchain_chroma import Chroma
import chromadb
from chromadb.config import Settings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from ingestor import DataIngestor

load_dotenv()

# Known garbage patterns produced by broken contextualize LLM calls
_GARBAGE_PATTERNS = [
    "omerang", "boomerang", "Question:", "question:", 
    "standalone question", "Standalone question"
]

def _is_garbage(text: str) -> bool:
    """Returns True if the standalone_q looks like LLM hallucination/garbage."""
    if not text or len(text.strip()) < 8:
        return True
    for pattern in _GARBAGE_PATTERNS:
        if pattern.lower() in text.lower():
            return True
    # Path-like or repo file spam (common garbage mode)
    slash_count = text.count("/") + text.count("\\")
    if len(text) > 200 and slash_count > 4:
        return True
    # Highly repetitive token soup
    tokens = re.findall(r"[A-Za-z0-9_.-]+", text)
    if len(tokens) >= 30:
        unique_ratio = len(set(tokens)) / len(tokens)
        if unique_ratio < 0.35:
            return True
        most_common_ratio = max(tokens.count(t) for t in set(tokens)) / len(tokens)
        if most_common_ratio > 0.2:
            return True
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 8 and (len(set(lines)) / len(lines)) < 0.4:
        return True
    return False


def _extract_answer_text(answer_obj) -> str:
    """
    Normalize LangChain/Groq outputs to a plain string for storage + API response.
    """
    if isinstance(answer_obj, str):
        return answer_obj.strip()
    # LangChain BaseMessage (e.g., AIMessage)
    content = getattr(answer_obj, "content", None)
    if isinstance(content, str):
        return content.strip()
    # Some chains return dicts
    if isinstance(answer_obj, dict):
        for key in ("answer", "output_text", "content", "text"):
            val = answer_obj.get(key)
            if isinstance(val, str):
                return val.strip()
    return str(answer_obj).strip()


class DeepContextEngine:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(current_dir, "chroma_db")
        self.collection_name = "deepcontext"

        client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        self.vector_db = Chroma(
            client=client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings
        )

        self.llm = ChatGroq(
            temperature=0,
            model_name="llama-3.1-8b-instant",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )

    def _normalize_chat_history(self, chat_history: List):
        """
        Converts raw SQLite tuples → LangChain message objects.
        Skips any AI message that looks like garbage from old broken responses.
        """
        if not chat_history:
            return []

        result = []
        for role, content in chat_history[-6:]:
            # ✅ Skip old garbage AI responses so they don't poison the context
            if role == "ai" and _is_garbage(content):
                print(f"⚠️ Skipping garbage history entry: {content[:60]}")
                continue
            if role == "human":
                result.append(HumanMessage(content=content))
            elif role == "ai":
                result.append(AIMessage(content=content))

        return result

    def _reload_vector_db(self):
        """Creates a fresh Chroma client to see newly ingested docs."""
        fresh_client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        self.vector_db = Chroma(
            client=fresh_client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings
        )

    def _try_persist(self):
        if hasattr(self.vector_db, "persist"):
            self.vector_db.persist()
            return
        client = getattr(self.vector_db, "_client", None)
        if client is not None and hasattr(client, "persist"):
            client.persist()

    def _get_standalone_question(self, user_question: str, safe_history: List) -> str:
        """
        Rewrites the user question as standalone ONLY when history exists.
        If no history, skip the LLM call entirely — return original question.
        Always falls back to original question if output looks like garbage.
        """
        # ✅ Skip contextualize step completely if there is no history
        if not safe_history:
            return user_question

        contextualize_q_system_prompt = (
            "You are a helpful assistant. Convert the latest user question into a "
            "self-contained standalone question using prior context if needed. "
            "Return ONLY the question. No prefixes, no explanation, no extra words."
        )

        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])

        try:
            chain = contextualize_q_prompt | self.llm
            response = chain.invoke({
                "input": user_question,
                "chat_history": safe_history
            })
            candidate = response.content.strip()

            # Hard sanity checks for runaway/garbage rewrites
            if len(candidate) > 220:
                return user_question
            if (candidate.count("/") + candidate.count("\\")) > 4:
                return user_question

            # ✅ Hard validation: if output looks wrong, fall back to original
            if _is_garbage(candidate):
                print(f"⚠️ Garbage standalone_q detected, falling back. Got: {candidate[:80]}")
                return user_question

            return candidate

        except Exception as e:
            print(f"⚠️ Contextualize step failed ({e}), falling back to original question.")
            return user_question

    def get_answer(self, user_question: str, user_dept: str, chat_history: List = None):
        # Step 1: Reload Chroma to pick up freshly ingested docs
        self._reload_vector_db()

        # Step 2: Convert raw history tuples → LangChain messages (filter garbage)
        safe_history = self._normalize_chat_history(chat_history)

        # Step 3: Retrieve relevant docs using the RAW user question
        # (Always use original question for retrieval — not rewritten one)
        docs_with_scores = self.vector_db.similarity_search_with_score(
            user_question,
            k=5,
            filter={"department": user_dept}
        )
        print(docs_with_scores)

        # Step 4: Filter by distance score (lower = better in Chroma)
        valid_docs = [doc for doc, score in docs_with_scores if score < 3.2]

        if not valid_docs:
            return {
                "answer": "I'm sorry, I couldn't find any relevant information in the documents for your question."
            }

        # Step 5: Get standalone question (safe, with fallback)
        standalone_q = self._get_standalone_question(user_question, safe_history)
        print(f"✅ standalone_q: {standalone_q}")

        # Step 6: Answer using ONLY the retrieved docs — no chat history here
        system_prompt = (
            "You are a Corporate Integrity AI. Answer the user's question using ONLY "
            "the provided context. Do not mention sources. Do not make up information. "
            "Check out the provided context properly , analyze it . Don't say I don't know even if the context is present . Take your time , but answer the question properly. "
            "If the answer is not in the context, say you don't know.\n\nContext: {context}"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])

        question_answer_chain = create_stuff_documents_chain(self.llm, prompt)

        answer = question_answer_chain.invoke({
            "input": standalone_q,
            "context": valid_docs
        })

        return {"answer": _extract_answer_text(answer)}
