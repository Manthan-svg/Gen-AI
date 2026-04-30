import os
import re
import numpy as np
from rank_bm25 import BM25Okapi
from typing import List
from langchain_chroma import Chroma
import chromadb
from chromadb.config import Settings
from chromadb.config import System
from chromadb.telemetry.product import ProductTelemetryClient, ProductTelemetryEvent
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.schema import Document
from dotenv import load_dotenv
from ingestor import DataIngestor
from overrides import override
from diagram_utils import detect_diagram_request_type, extract_diagrams_from_docs

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(CURRENT_DIR, ".env"))


class NoOpProductTelemetry(ProductTelemetryClient):
    """Disable Chroma product telemetry to avoid noisy startup/runtime errors."""

    def __init__(self, system: System):
        super().__init__(system)

    @override
    def capture(self, event: ProductTelemetryEvent) -> None:
        return None

# Known garbage patterns produced by broken contextualize LLM calls
_GARBAGE_PATTERNS = [
    "omerang", "boomerang", "Question:", "question:", 
    "standalone question", "Standalone question"
]

_SMALL_TALK_RESPONSES = {
    "greeting": "Hello! I can help you with questions about your uploaded documents. Ask me anything from the knowledge base.",
    "thanks": "You're welcome. If you need anything from the uploaded documents, ask away.",
    "farewell": "Goodbye! Come back anytime if you want help with the knowledge base.",
    "assistant_help": "I can answer questions using your uploaded documents, summarize relevant information, and help you find specific details from the knowledge base.",
}

_GREETING_PHRASES = {
    "hello",
    "hi",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
}

_THANKS_PHRASES = {
    "thanks",
    "thank you",
    "thx",
    "thanks a lot",
    "thank you so much",
}

_FAREWELL_PHRASES = {
    "bye",
    "goodbye",
    "see you",
    "see you later",
}

_ASSISTANT_HELP_PHRASES = {
    "help",
    "what can you do",
    "how can you help",
    "what do you do",
}

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


def _normalize_markdown_answer(text: str) -> str:
    """
    Preserve markdown structures while cleaning up excessive spacing in prose.
    """
    normalized = str(text or "").replace("\r\n", "\n").strip()
    if not normalized:
        return ""

    segments = re.split(r"(```[\s\S]*?```)", normalized)
    cleaned_segments = []

    for segment in segments:
        if not segment:
            continue
        if segment.startswith("```") and segment.endswith("```"):
            cleaned_segments.append(segment.strip())
            continue

        cleaned_segments.append(re.sub(r"\n{3,}", "\n\n", segment).strip("\n"))

    return "\n\n".join(part for part in cleaned_segments if part)


def _extract_history_item(item):
    if isinstance(item, dict):
        return item.get("role"), item.get("content")
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return item[0], item[1]
    return None, None

def _normalize_user_text(text: str) -> str:
    lowered = str(text or "").lower().strip()
    lowered = re.sub(r"[^\w\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _merge_diagram_request_type(raw_type, standalone_type):
    priority = {
        None: 0,
        "all": 1,
        "mermaid": 2,
        "plantuml": 2,
    }
    if priority.get(standalone_type, 0) > priority.get(raw_type, 0):
        return standalone_type
    return raw_type


def _filter_diagrams_by_type(diagrams: list, requested_type):
    if requested_type in (None, "all"):
        return diagrams
    return [diagram for diagram in diagrams if diagram.get("type") == requested_type]


_DIAGRAM_QUERY_STOPWORDS = {
    "show", "me", "the", "a", "an", "for", "of", "to", "please", "diagram",
    "flow", "chart", "render", "display", "give", "with", "and", "that",
    "this", "plantuml", "puml", "uml", "mermaid", "sequence", "architecture",
}


def _title_match_tokens(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", str(text or "").lower())
    return {
        token for token in tokens
        if len(token) > 2 and token not in _DIAGRAM_QUERY_STOPWORDS
    }


def _filter_diagrams_by_title_match(diagrams: list, *queries: str):
    query_tokens = set()
    for query in queries:
        query_tokens |= _title_match_tokens(query)

    if not query_tokens:
        return diagrams

    if len(diagrams) == 1:
        diagram = diagrams[0]
        title_tokens = _title_match_tokens(diagram.get("title", ""))
        return diagrams if (query_tokens & title_tokens) else []

    scored = []
    for diagram in diagrams:
        title_tokens = _title_match_tokens(diagram.get("title", ""))
        score = len(query_tokens & title_tokens)
        scored.append((score, diagram))

    best_score = max((score for score, _ in scored), default=0)
    if best_score <= 0:
        return []

    best_diagrams = [diagram for score, diagram in scored if score == best_score]
    if len(best_diagrams) == len(diagrams):
        return diagrams

    return best_diagrams


def _filter_diagram_docs_by_selected(diagram_docs: List[Document], selected_diagrams: list):
    selected_keys = {
        (
            diagram.get("sourceName"),
            diagram.get("type"),
            diagram.get("title"),
            diagram.get("diagramIndex"),
        )
        for diagram in selected_diagrams
    }
    return [
        doc for doc in diagram_docs
        if (
            (getattr(doc, "metadata", {}) or {}).get("source_name"),
            (getattr(doc, "metadata", {}) or {}).get("content_type"),
            (getattr(doc, "metadata", {}) or {}).get("diagram_title"),
            (getattr(doc, "metadata", {}) or {}).get("diagram_index"),
        ) in selected_keys
    ]


def _detect_small_talk_intent(text: str) -> str | None:
    normalized = _normalize_user_text(text)
    if not normalized:
        return None

    tokens = normalized.split()
    if len(tokens) > 6:
        return None

    if normalized in _GREETING_PHRASES:
        return "greeting"
    if normalized in _THANKS_PHRASES:
        return "thanks"
    if normalized in _FAREWELL_PHRASES:
        return "farewell"
    if normalized in _ASSISTANT_HELP_PHRASES:
        return "assistant_help"

    # Allow a very small near-exact greeting surface such as "hi there".
    if len(tokens) == 2 and tokens[0] in {"hello", "hi", "hey"} and tokens[1] in {"there", "team", "assistant"}:
        return "greeting"

    return None


class DeepContextEngine:
    def __init__(self):
        # Allow the model to download into the shared cache on first boot, then
        # optionally switch back to cache-only mode for offline runs.
        self.hf_local_files_only = os.getenv("HUGGINGFACE_LOCAL_FILES_ONLY", "false").lower() == "true"
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu", "local_files_only": self.hf_local_files_only},
            encode_kwargs={"normalize_embeddings": False},
            cache_folder=os.path.expanduser("~/.cache/huggingface/hub"),
        )

        self.db_path = os.path.join(CURRENT_DIR, "chroma_db")
        self.collection_name = os.getenv("CHROMA_COLLECTION_NAME", "deepcontext")
        self.chroma_host = os.getenv("CHROMA_HOST", "localhost")
        self.chroma_port = int(os.getenv("CHROMA_PORT", "8001"))
        self.chroma_ssl = os.getenv("CHROMA_SSL", "false").lower() == "true"

        self.vector_db = self._create_vector_db()

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
        for item in chat_history[-6:]:
            role, content = _extract_history_item(item)
            if role is None:
                continue
            # ✅ Skip old garbage AI responses so they don't poison the context
            if role == "ai" and _is_garbage(content):
                print(f"⚠️ Skipping garbage history entry: {content[:60]}")
                continue
            if role == "human":
                result.append(HumanMessage(content=content))
            elif role == "ai":
                result.append(AIMessage(content=content))

        return result
    
    def _hybrid_search(self, query: str, k: int = 5) -> List[Document]:
        """
        Combines ChromaDB semantic search + BM25 lexical search
        using Reciprocal Rank Fusion (RRF) to merge results.
        """

        # ── 1. Semantic Search (your existing ChromaDB) ──────────────────
        semantic_results = self.vector_db.similarity_search_with_score(
            query, k=10
        )
        # Lower score = better in Chroma (distance metric)
        semantic_docs = [
            (doc, score) for doc, score in semantic_results if score < 3.2
        ]

        # ── 2. Fetch all docs for BM25 ───────────────────────────────────
        all_dept_data = self.vector_db.get()
        all_texts     = all_dept_data.get("documents", [])
        all_metadatas = all_dept_data.get("metadatas", [])

        if not all_texts:
            print("⚠️ No docs for BM25, falling back to semantic only.")
            return [doc for doc, _ in semantic_docs[:k]]

        # ── 3. Build BM25 Index ───────────────────────────────────────────
        tokenized_corpus = [text.lower().split() for text in all_texts]
        bm25 = BM25Okapi(tokenized_corpus)

        # ── 4. Score All Docs Against Query ──────────────────────────────
        tokenized_query = query.lower().split()
        bm25_scores     = bm25.get_scores(tokenized_query)
        top_bm25_idx    = np.argsort(bm25_scores)[::-1][:10]

        # ── 5. Reciprocal Rank Fusion (RRF) ──────────────────────────────
        RRF_K      = 60          # standard constant
        rrf_scores = {}           # doc_key → cumulative RRF score
        doc_store  = {}           # doc_key → Document object
        source_docs = {}          # source_name → list[Document]

        def _doc_key(doc: Document, fallback_text: str | None = None) -> str:
            meta = getattr(doc, "metadata", {}) or {}
            source_name = meta.get("source_name") or meta.get("source") or "unknown"
            chunk_index = meta.get("chunk_index")
            preview = (fallback_text if fallback_text is not None else doc.page_content)[:120]
            return f"{source_name}::{chunk_index if chunk_index is not None else 'na'}::{preview}"

        # Semantic results contribute to RRF
        for rank, (doc, _) in enumerate(semantic_docs):
            key = _doc_key(doc)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
            doc_store[key]  = doc

        # BM25 results contribute to RRF
        for rank, idx in enumerate(top_bm25_idx):
            if bm25_scores[idx] <= 0:         # skip zero-score docs
                continue
            text = all_texts[idx]
            meta = all_metadatas[idx] if idx < len(all_metadatas) else {}
            key  = _doc_key(Document(page_content=text, metadata=meta), fallback_text=text)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
            if key not in doc_store:
                doc_store[key] = Document(page_content=text, metadata=meta)

        # ── 6. Sort by RRF score descending, return top-k ────────────────
        ranked_keys = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)
        final_docs  = [doc_store[key] for key in ranked_keys if key in doc_store]

        # If the top hit comes from a multi-chunk source, bring in sibling chunks
        # from the same source so the answer model sees the full document context.
        if final_docs:
            top_source = (getattr(final_docs[0], "metadata", {}) or {}).get("source_name")
            if top_source:
                for text, meta in zip(all_texts, all_metadatas):
                    if not isinstance(meta, dict):
                        continue
                    if meta.get("source_name") != top_source:
                        continue
                    doc = Document(page_content=text, metadata=meta)
                    source_docs.setdefault(top_source, []).append(doc)

                if top_source in source_docs:
                    source_docs[top_source].sort(
                        key=lambda d: (
                            getattr(d, "metadata", {}) or {}).get("chunk_index") or 0
                    )

                    expanded_docs = []
                    seen_keys = set()
                    for doc in source_docs[top_source][:3]:
                        key = _doc_key(doc)
                        if key in seen_keys:
                            continue
                        expanded_docs.append(doc)
                        seen_keys.add(key)

                    for doc in final_docs:
                        key = _doc_key(doc)
                        if key in seen_keys:
                            continue
                        expanded_docs.append(doc)
                        seen_keys.add(key)
                        if len(expanded_docs) >= k:
                            break

                    final_docs = expanded_docs[:k]

        # print(f"✅ Hybrid search → {len(semantic_docs)} semantic + "
        #     f"{sum(1 for i in top_bm25_idx if bm25_scores[i] > 0)} BM25 "
        #     f"→ {len(final_docs)} fused docs returned")
        
        return final_docs[:k]

    def _create_vector_db(self):
        """Create a Chroma handle backed by the shared Chroma HTTP server."""
        fresh_client = chromadb.HttpClient(
            host=self.chroma_host,
            port=self.chroma_port,
            ssl=self.chroma_ssl,
            settings=Settings(
                anonymized_telemetry=False,
                chroma_product_telemetry_impl="rag_engine.NoOpProductTelemetry",
                chroma_telemetry_impl="rag_engine.NoOpProductTelemetry",
            )
        )
        return Chroma( 
            client=fresh_client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings
        )

    def _reload_vector_db(self):
        """Recreate the HTTP-backed Chroma handle."""
        self.vector_db = self._create_vector_db()
        return self.vector_db

    def _fetch_diagram_docs_for_sources(self, vector_db, source_names: set[str]) -> List[Document]:
        if not source_names:
            return []

        snapshot = vector_db.get()
        documents = snapshot.get("documents", [])
        metadatas = snapshot.get("metadatas", [])

        diagram_docs = []
        for text, meta in zip(documents, metadatas):
            if not isinstance(meta, dict):
                continue
            if meta.get("source_name") not in source_names:
                continue
            if meta.get("content_type") not in {"plantuml", "mermaid"}:
                continue
            diagram_docs.append(Document(page_content=text, metadata=meta))

        return diagram_docs

    def fresh_reader(self):
        """
        Create a fresh Chroma reader while reusing the loaded embedding model and LLM.
        """
        reader = DeepContextEngine.__new__(DeepContextEngine)
        reader.embeddings = self.embeddings
        reader.db_path = self.db_path
        reader.collection_name = self.collection_name
        reader.chroma_host = self.chroma_host
        reader.chroma_port = self.chroma_port
        reader.chroma_ssl = self.chroma_ssl
        reader.llm = self.llm
        reader.vector_db = reader._create_vector_db()
        return reader

    def get_vector_db(self, refresh: bool = False):
        if refresh or self.vector_db is None:
            return self._reload_vector_db()
        return self.vector_db

    def _try_persist(self):
        vector_db = self.get_vector_db()
        if hasattr(vector_db, "persist"):
            vector_db.persist()
            return
        client = getattr(vector_db, "_client", None)
        if client is not None and hasattr(client, "persist"):
            client.persist()

    def _get_standalone_question(self, user_question: str, safe_history: List) -> str:
        if not safe_history:
            return user_question

        contextualize_q_system_prompt = (
            "You are a helpful assistant. Convert the latest user question into a "
            "self-contained standalone question using prior context if needed. "
            "Return ONLY the question. No prefixes, no explanation, no extra words."
            
            "Rewrite the user question in one standalone question. No prefixes, no explanation, no extra words."
            "Rules: "
            "1. The output must an question instead of answer."
            "2. Output must end with a ?"
            "3. Do not answer using facts from chat history."
            "4. Do not add prefixes, quotes, explanations, or markdown."
            "5. If the latest user turn is already standalone, return it as a single clean question."
        )   

        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat-history"),
            ("human", "{input}")
        ])

        try:
            chain = contextualize_q_prompt | self.llm
            response = chain.invoke({
                "input": user_question,
                "chat-history": safe_history
            })
            candidate = response.content.strip()

            # Hard sanity checks for runaway/garbage rewrites
            if len(candidate) > 220:
                return user_question
            if (candidate.count("/") + candidate.count("\\")) > 4:
                return user_question

            if _is_garbage(candidate):
                print(f"⚠️ Garbage standalone_q detected, falling back. Got: {candidate[:80]}")
                return user_question

            return candidate

        except Exception as e:
            print(f"⚠️ Contextualize step failed ({e}), falling back to original question.")
            return user_question

    def get_answer(self, user_question: str, chat_history: List = None):
        small_talk_intent = _detect_small_talk_intent(user_question)
        if small_talk_intent:
            return {
                "answer": _SMALL_TALK_RESPONSES[small_talk_intent],
                "retrieved": False,
                "intent": small_talk_intent,
                "diagrams":[] 
            }

        # Step 1: Reload Chroma to pick up freshly ingested docs
        vector_db = self.get_vector_db(refresh=True)

        visible_snapshot = vector_db.get()
        visible_count = len(visible_snapshot.get("documents", []))
        visible_sources = sorted({
            metadata.get("source_name")
            for metadata in visible_snapshot.get("metadatas", [])
            if isinstance(metadata, dict) and metadata.get("source_name")
        })
        print(
            f"🔎 Retrieval snapshot | docs_visible={visible_count} | "
            f"sources_visible={visible_sources[:10]} | question={user_question[:120]!r}"
        )

        # Step 2: Convert raw history tuples → LangChain messages (filter garbage)
        safe_history = self._normalize_chat_history(chat_history)

        valid_docs = self._hybrid_search(user_question, k=5)

        if not valid_docs:
            return {
                "answer": "I'm sorry, I couldn't find any relevant information in the documents for your question.",
                "retrieved": False,
                "diagrams":[]
            }
        print(valid_docs)
        
        """  
            Diagram Detection Logic
        """
        diagrams = []
        diagram_docs = []
                    
        top_retrieval_preview = [
            {
                "source": (doc.metadata or {}).get("source_name", "Unknown source"),
                "page": (doc.metadata or {}).get("page"),
                "status": (doc.metadata or {}).get("status"),
                "preview": doc.page_content[:120].replace("\n", " "),
            }
            for doc in valid_docs[:5]
        ]
        print(f"🔎 Top retrieved docs | {top_retrieval_preview}")
        
        # print(valid_docs)
        

        # Step 5: Get standalone question (safe, with fallback)
        standalone_q = self._get_standalone_question(user_question, safe_history)
        print(f"✅ standalone_q: {standalone_q}")

        raw_diagram_request_type = detect_diagram_request_type(user_question)
        standalone_diagram_request_type = detect_diagram_request_type(standalone_q)
        requested_diagram_type = _merge_diagram_request_type(
            raw_diagram_request_type,
            standalone_diagram_request_type,
        )
        is_diagram_request = requested_diagram_type is not None

        if is_diagram_request:
            source_names = {
                (getattr(doc, "metadata", {}) or {}).get("source_name")
                for doc in valid_docs
                if (getattr(doc, "metadata", {}) or {}).get("source_name")
            }
            diagram_docs = self._fetch_diagram_docs_for_sources(vector_db, source_names)
            diagrams = _filter_diagrams_by_type(
                extract_diagrams_from_docs(diagram_docs),
                requested_diagram_type,
            )
            diagrams = _filter_diagrams_by_title_match(
                diagrams,
                standalone_q,
                user_question,
            )
            diagram_docs = _filter_diagram_docs_by_selected(diagram_docs, diagrams) if diagrams else diagram_docs

        if is_diagram_request and diagrams:
            return {
                "answer": "",
                "retrieved": True,
                "diagrams": diagrams,
            }

        if is_diagram_request and not diagrams:
            diagram_type_label = {
                "mermaid": "Mermaid",
                "plantuml": "PlantUML",
                "all": "diagram",
            }.get(requested_diagram_type, "diagram")
            return {
                "answer": f"I couldn't find a {diagram_type_label} in the retrieved documents for this question.",
                "retrieved": True,
                "diagrams": [],
            }

        # Step 6: Answer using ONLY the retrieved docs — no chat history here
        system_prompt = (
            "You are a Corporate Knowledge Assistant. Your ONLY job is to answer the user's "
            "question using the provided context block below.\n\n"
            "STRICT RULES:\n"
            "1. Read the entire provided context carefully before answering. Make sure to read the context block below.\n"
            "2. If the answer IS present in the provided context — answer it directly and completely."
            "Do NOT say 'I don't know' if the information exists in the provided context.\n"
            "3. Only say you don't know if the provided context genuinely has no relevant information "
            "after careful reading.\n"
            "4. For list-type questions (participants, members, action items, decisions), "
            "extract and list every item found in the provided context.\n"
            "5. Do not fabricate anything not in the provided context.\n"
            "6. Format the answer as clean markdown when it improves readability.\n"
            "7. Use bullet points or numbered lists for multi-item answers.\n"
            "8. Use markdown tables only when the source information is naturally tabular.\n"
            "9. Use fenced code blocks for commands, code, or structured snippets.\n"
            "10. Do not use raw HTML.\n"
            "11. Keep simple answers as short plain paragraphs without unnecessary headings.\n\n"
            "provided context:\n{context}"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])

        # ── Retry loop: up to 3 attempts if the model returns a bad "I don't know" ──
        _DONT_KNOW_PHRASES = [
            "i don't know", "i do not know", "no information",
            "not available", "no relevant", "cannot find",
            "not mentioned", "not provided", "no details"
        ]

        def _looks_like_dont_know(text: str) -> bool:
            lowered = text.lower().strip()
            return any(phrase in lowered for phrase in _DONT_KNOW_PHRASES)

        question_answer_chain = create_stuff_documents_chain(self.llm, prompt)

        answer_text = None
        for attempt in range(3):
            raw_answer = question_answer_chain.invoke({
                "input": standalone_q,
                "context": valid_docs
            })
            candidate = _normalize_markdown_answer(_extract_answer_text(raw_answer))

            # If the model gave a real answer, accept it immediately
            if not _looks_like_dont_know(candidate):
                answer_text = candidate
                break

            print(f"⚠️ Attempt {attempt + 1}: LLM returned a weak answer despite valid docs. Retrying...")
            answer_text = candidate  # keep last attempt as fallback


        return {
            "answer": answer_text,
            "retrieved": True,
            "diagrams":diagrams
        }
