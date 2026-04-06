# Enhanced Implementation Features Document for DeepContext

## 1. Executive Summary

DeepContext is currently a capable internal knowledge assistant for business documents. It already supports asynchronous ingestion, hybrid retrieval, markdown answers with citations, diagram-aware responses, multi-session chat history, meeting transcript summarization, and Slack-triggered ingestion. In its current form, however, it behaves as a shared single-tenant tool: all users operate as `anonymous`, all documents live in one shared corpus, and operational feedback during ingestion and answer generation is limited.

The enhancements in this document are intended to move DeepContext from a useful internal prototype into a production-ready multi-user platform. The next stage is not simply about adding features; it is about introducing identity, data scoping, operational visibility, version control for documents, better ranking quality, streaming UX, and lightweight response evaluation so the system can scale in both users and trustworthiness.

## 2. Current System Overview

| Area | Current implementation | Known limitation |
| --- | --- | --- |
| Authentication and access control | The frontend loads directly into the app with no login flow, and the backend treats usage as a shared anonymous model. Chat sessions are stored under a shared `anonymous` username. | There is no user isolation, no route protection, no authorization boundary, and no distinction between uploader and reader privileges. |
| Document ingestion pipeline | Files are uploaded through FastAPI and processed asynchronously through Celery. The pipeline supports `.txt`, `.md`, text PDFs, scanned PDFs via OCR-style extraction, images, `.puml`, `.mmd`, and `.mermaid`. | Ingestion is functionally rich, but status feedback is coarse and document lifecycle management is minimal. There is no first-class notion of replacement, version history, or workspace ownership. |
| Vector storage and retrieval | Retrieval uses ChromaDB with HuggingFace sentence-transformer embeddings and BM25 fusion via Reciprocal Rank Fusion. The corpus is shared across the entire application. | Retrieval quality is bounded by chunk quality and first-pass ranking. There is no workspace filtering, no reranking layer, and no document-level access control. |
| Answer generation | Answers are generated through Groq-hosted LLaMA models via LangChain. The system is context-grounded, outputs markdown, and attaches inline citations using claim-level semantic matching. | Answers are returned only after full generation completes, and there is no explicit confidence scoring or post-generation hallucination check. |
| Diagram support | Mermaid is rendered client-side and PlantUML diagrams are shown through generated public `plantuml.com` URLs. Retrieval is diagram-aware, and diagrams can be returned directly. | PlantUML depends on a public rendering service, and document management does not yet expose diagram assets or version-aware diagram replacement. |
| Chat sessions | Sessions and message history are stored in SQLite, with session titles, previews, timestamps, retrieval, and deletion. | Sessions are not scoped by real users or workspaces, and SQLite is not ideal for multi-user concurrent production growth. |
| Frontend | The UI is built with React 19, Vite, Tailwind CSS 4, and `react-markdown` with GFM support. Upload flow currently relies on polling `/job-status` every two seconds. | There is no true real-time ingestion progress, no dedicated document management page, and no streamed answer rendering. |
| Meeting transcripts | Files containing `meeting` or `transcript` branch to `MeetingAgent`, which produces structured summaries and stores them as high-value knowledge records. | This path is useful but still lands in the same shared corpus model, without workspace ownership, versioning, or specialized evaluation. |
| Slack integration | Slack `file_shared` events hit a webhook and route files through the same Celery ingestion pipeline. | Slack-ingested content is not yet tied to user identity, workspace membership, or policy-driven access control. |
| Vector DB refresh | Operationally, the system now expects a standalone Chroma HTTP server, and the backend often refreshes its handle explicitly before reads. | The architecture still needs to be formalized so visibility of newly ingested documents is guaranteed consistently across API and worker processes without any manual refresh assumptions. |

## 3. Enhanced Features - Detailed Specification

### 3.1 Multi-User Authentication with Role-Based Access

| Aspect | Specification |
| --- | --- |
| What it is | Introduce full account-based authentication with signup, login, hashed passwords, JWT access tokens, and role levels such as `admin`, `editor`, and `viewer`. |
| Why it is needed | DeepContext is currently a shared anonymous system, which prevents secure collaboration, individual accountability, and access-controlled operations such as upload and delete. |
| What the current system does instead | The current app has no login or token exchange. Session ownership is effectively synthetic and all actions are available to anyone who can reach the UI and API. |
| How it should work after implementation | Users authenticate through dedicated auth endpoints and receive JWTs. The frontend stores the token securely and attaches it to API requests. Backend route guards enforce role policies: admins can upload and delete documents, editors can upload but not perform destructive management tasks, and viewers can only query and browse approved content. |
| Files or components involved | Existing backend entry points include [backend/MainApplicationRunner.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/MainApplicationRunner.py), [backend/database.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/database.py), and [backend/chat_session_manager.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/chat_session_manager.py). Frontend work will center on [frontend/src/main.jsx](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/main.jsx), [frontend/src/App.jsx](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/App.jsx), and [frontend/src/utils/api.util.js](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/utils/api.util.js), plus new auth pages and route guards. |
| Dependencies or prerequisites | User and role tables, password hashing, JWT signing keys, token middleware, protected frontend routing, and migration of session ownership from `anonymous` to real user IDs. |

### 3.2 Department or Workspace Scoping

| Aspect | Specification |
| --- | --- |
| What it is | Add first-class workspaces or departments so documents, sessions, and retrieval results are scoped to an active workspace selected by the user. |
| Why it is needed | The current shared corpus model is the largest product limitation. Without scoping, confidential content can bleed across teams and retrieval quality degrades as unrelated material accumulates. |
| What the current system does instead | All retrieval is executed against one shared Chroma collection and chat sessions are effectively global under the anonymous model. |
| How it should work after implementation | Users belong to one or more workspaces. Every upload, chat session, and retrieval request carries a workspace context. Documents are tagged with workspace identifiers in metadata, and retrieval filters only search within the active workspace. Admins can manage membership and switch user access by policy. |
| Files or components involved | Retrieval and metadata changes belong primarily in [backend/rag_engine.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/rag_engine.py), [backend/supervisor.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/supervisor.py), [backend/ingestor.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/ingestor.py), and [backend/MainApplicationRunner.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/MainApplicationRunner.py). Session scoping extends [backend/chat_session_manager.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/chat_session_manager.py). |
| Dependencies or prerequisites | Workspace membership schema, token claims or session context carrying workspace identity, metadata filters in Chroma, and UI affordances for workspace selection and administration. |

### 3.3 Real-Time Ingestion Progress via WebSockets

| Aspect | Specification |
| --- | --- |
| What it is | Replace polling-based job tracking with push-based ingestion progress via WebSockets or Server-Sent Events, including granular status updates and a live progress bar. |
| Why it is needed | The current upload UX feels opaque. Users only know that polling is happening, not which ingestion stage is active or whether the file is stalled, parsing, OCRing, chunking, or indexing. |
| What the current system does instead | The frontend polls `/job-status/{job_id}` every two seconds from upload components. |
| How it should work after implementation | When an upload begins, the frontend opens a live channel keyed by job ID. The Celery worker emits stage transitions such as `uploaded`, `extracting`, `ocr_processing`, `chunking`, `indexing`, and `completed` or `failed`. The UI renders these updates immediately and removes the polling loop. |
| Files or components involved | Polling logic currently lives in [frontend/src/components/ChatHistoryDrawer.jsx](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/components/ChatHistoryDrawer.jsx) and the unused [frontend/src/components/MenuComponent.jsx](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/components/MenuComponent.jsx). Backend orchestration is centered in [backend/MainApplicationRunner.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/MainApplicationRunner.py) and [backend/celery_worker.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/celery_worker.py). |
| Dependencies or prerequisites | A transport choice between WebSockets and SSE, a pub/sub channel for worker-to-API progress forwarding, and a canonical progress event schema shared by backend and frontend. |

### 3.4 ChromaDB HTTP Server Architecture

| Aspect | Specification |
| --- | --- |
| What it is | Standardize DeepContext on a dedicated ChromaDB HTTP server as an explicit runtime dependency for both the API and Celery worker. |
| Why it is needed | Shared visibility of new documents depends on a single live vector store endpoint rather than process-local persistence assumptions. This is especially important once multi-user ingestion and document versioning are introduced. |
| What the current system does instead | The current code already instantiates `chromadb.HttpClient` and the README instructs operators to run `./start_chroma.sh`. The enhancement here is therefore architectural hardening rather than a first-time migration from embedded storage. |
| How it should work after implementation | Chroma runs as a managed service with startup checks, health checks, collection bootstrap, and environment-driven connection settings. API and workers never assume local persistence. Collection access, refresh, and failure handling become standardized and observable. |
| Files or components involved | Current vector DB initialization is in [backend/rag_engine.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/rag_engine.py), and process startup is in [backend/start_chroma.sh](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/start_chroma.sh). |
| Dependencies or prerequisites | Stable Chroma deployment, startup ordering, health probes, connection retry policies, and environment-managed host and port settings. |

### 3.5 Document Versioning and Update Support

| Aspect | Specification |
| --- | --- |
| What it is | Detect when an uploaded document supersedes an existing document and replace or archive the old chunks instead of creating duplicates. Persist version number and upload timestamp per document. |
| Why it is needed | The system currently treats repeated uploads as additional records, which causes duplicate retrieval hits, stale answers, and unclear provenance. |
| What the current system does instead | Uploads create new chunks and diagram records. Metadata contains timestamps and a `version` field in some paths, but there is no document-level replacement workflow. |
| How it should work after implementation | Before indexing a new upload, the system checks whether a document with the same logical identity already exists within the same workspace. If found, the previous version is archived or deleted and the new upload becomes the active version. Retrieval should default to active versions only, while history remains queryable for audit purposes if archival mode is chosen. |
| Files or components involved | Core changes belong in [backend/supervisor.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/supervisor.py), [backend/ingestor.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/ingestor.py), [backend/rag_engine.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/rag_engine.py), and [backend/MainApplicationRunner.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/MainApplicationRunner.py). |
| Dependencies or prerequisites | A document registry table or metadata index, a clear document identity rule, archive-versus-delete policy, and UI support for showing version history. |

### 3.6 Hybrid Reranking with Cross-Encoder

| Aspect | Specification |
| --- | --- |
| What it is | Add a cross-encoder reranking layer after the current hybrid retrieval pipeline to reorder the initially retrieved chunks by deeper semantic relevance. |
| Why it is needed | BM25 plus embedding retrieval is a strong first pass, but difficult enterprise queries often need a second ranking stage to elevate the most useful chunks before they reach the LLM. |
| What the current system does instead | [backend/rag_engine.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/rag_engine.py) currently performs semantic search and BM25 fusion through Reciprocal Rank Fusion, then sends top chunks directly into answer generation. |
| How it should work after implementation | The retrieval stage should fetch a larger candidate set, score each query-chunk pair with a local cross-encoder such as `cross-encoder/ms-marco-MiniLM-L-6-v2`, and pass only the reranked top `k` chunks into the answer chain. The reranker should be configurable and easy to disable in low-resource environments. |
| Files or components involved | The change is concentrated in [backend/rag_engine.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/rag_engine.py), with optional instrumentation in [backend/CitationSystemGuide.md](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/CitationSystemGuide.md) and any future evaluation tooling. |
| Dependencies or prerequisites | Local model download and caching, additional latency budgeting, and benchmarks to determine candidate set size and acceptable throughput. |

### 3.7 Contextual Chunk Enrichment

| Aspect | Specification |
| --- | --- |
| What it is | Prepend each chunk with a short contextual sentence that explains where the chunk fits within the broader source document before embedding and storage. |
| Why it is needed | Many chunks lose meaning when isolated from section headers, nearby paragraphs, or document purpose. Contextual chunk enrichment improves retrieval precision for such fragments. |
| What the current system does instead | Chunks are stored largely as extracted content with metadata. Diagram records carry useful structure, but prose chunks do not receive LLM-generated contextual framing before embedding. |
| How it should work after implementation | During ingestion, the pipeline derives a brief contextual summary for each chunk using its local neighborhood in the source document. Both the enriched text and the raw text should be preserved so retrieval benefits from context while preview and audit tools can still show the original extracted content cleanly. |
| Files or components involved | Primary changes belong in [backend/ingestor.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/ingestor.py) and [backend/supervisor.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/supervisor.py), with retrieval usage in [backend/rag_engine.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/rag_engine.py). |
| Dependencies or prerequisites | An enrichment prompt template, cost and latency controls, fallback behavior for low-value or very short chunks, and metadata fields separating raw and enriched variants. |

### 3.8 Answer Streaming to Frontend

| Aspect | Specification |
| --- | --- |
| What it is | Stream answer tokens incrementally from the LLM pipeline to the frontend so the chat bubble renders as content arrives. |
| Why it is needed | Waiting for the full answer before rendering makes the product feel slower than it is, especially for longer grounded responses and diagram-heavy prompts. |
| What the current system does instead | The chat UI waits for the complete `/get-answer` response before inserting the assistant message into the transcript. |
| How it should work after implementation | The backend exposes a streaming endpoint using SSE or WebSockets. The frontend opens the stream when a question is submitted and updates the in-progress assistant message as tokens arrive. Citations and diagrams can be attached at completion or progressively if supported cleanly by the chain. |
| Files or components involved | Current answer orchestration is in [backend/MainApplicationRunner.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/MainApplicationRunner.py) and [backend/rag_engine.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/rag_engine.py). Frontend rendering changes will center on [frontend/src/components/ChatWindow.jsx](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/components/ChatWindow.jsx) and [frontend/src/components/MarkdownRenderer.jsx](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/components/MarkdownRenderer.jsx). |
| Dependencies or prerequisites | Groq streaming support through the chosen LangChain path, a stable event protocol, cancellation handling, and a UI state model for partial assistant messages. |

### 3.9 Document Management UI

| Aspect | Specification |
| --- | --- |
| What it is | Build a dedicated document management interface for browsing and administering uploaded content, rather than relying on a narrow sidebar view. |
| Why it is needed | As document count grows, users need to inspect ingestion status, identify duplicates, see versions, confirm workspace ownership, preview extracted text, and manage lifecycle actions from a single place. |
| What the current system does instead | The app currently exposes only a simple document list in [frontend/src/App.jsx](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/App.jsx) and upload actions inside [frontend/src/components/ChatHistoryDrawer.jsx](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/components/ChatHistoryDrawer.jsx). |
| How it should work after implementation | The new page should show document name, active version, workspace, file size, upload time, ingestion state, and preview availability. Admins should be able to delete or archive documents, editors should re-upload new versions, and viewers should inspect metadata and preview extracted text when permitted. |
| Files or components involved | Existing document API usage is in [frontend/src/App.jsx](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/App.jsx) and [frontend/src/utils/api.util.js](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/utils/api.util.js). Backend extensions belong in [backend/MainApplicationRunner.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/MainApplicationRunner.py) with supporting metadata retrieval logic in [backend/rag_engine.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/rag_engine.py). |
| Dependencies or prerequisites | Rich document metadata storage, role-aware endpoints, pagination or filtering strategy, and extracted-text preview APIs. |

### 3.10 Evaluation and Hallucination Detection

| Aspect | Specification |
| --- | --- |
| What it is | Add a lightweight post-generation evaluator that measures similarity between the final answer and the retrieved chunks, flags low-confidence responses, and logs them for review. |
| Why it is needed | Grounded prompting reduces hallucination risk but does not eliminate it. Teams need a visible signal when an answer may have drifted beyond its retrieved evidence. |
| What the current system does instead | The system currently generates citations and relies on context-only prompting, but it does not compute a confidence score or produce any UI-level warning badge. |
| How it should work after implementation | After answer generation, the backend computes embeddings for the answer or its claim spans and compares them to the retrieved chunk set. If the maximum similarity falls below a configurable threshold, the response is marked low confidence. The frontend displays a warning badge, and the event is logged for later inspection and prompt or retrieval tuning. |
| Files or components involved | Retrieval and answer assembly are in [backend/rag_engine.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/rag_engine.py); persistence and response transport are in [backend/MainApplicationRunner.py](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/backend/MainApplicationRunner.py). Frontend display would extend [frontend/src/components/ChatWindow.jsx](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/components/ChatWindow.jsx) and [frontend/src/components/MarkdownRenderer.jsx](/home/manthan.kanade@sarvatra.in/Desktop/DeepContext/frontend/src/components/MarkdownRenderer.jsx). |
| Dependencies or prerequisites | Threshold calibration, structured logging, optional review dashboard support, and a decision on whether warnings are advisory-only or can suppress output under stricter policies. |

## 4. Technology Additions Required

| Group | Additions |
| --- | --- |
| Backend additions | JWT library such as `python-jose` or `PyJWT`; password hashing via `passlib` or `bcrypt`; ORM or migration tooling such as SQLAlchemy plus Alembic if the team wants to move beyond raw SQLite access; workspace and membership schema; WebSocket or SSE support; Redis pub/sub or a message broker pattern for ingestion progress; cross-encoder inference support through `sentence-transformers`; optional evaluation logging pipeline; document registry and version metadata tables. |
| Frontend additions | Auth screens and protected routing; token storage and refresh handling; workspace selector and admin membership UI; a WebSocket or SSE client abstraction; streamed answer rendering state; a dedicated document management page; richer table, filtering, and preview components; confidence badge and warning presentation. |
| Infrastructure additions | Managed or standardized ChromaDB HTTP deployment; persistent Redis suitable for both Celery and progress fan-out; secret management for JWT signing keys and Slack tokens; reverse proxy support for SSE or WebSockets; environment-based frontend configuration; optional migration from SQLite to PostgreSQL for multi-user concurrency; observability for background jobs, streaming, and vector DB health. |

## 5. Migration and Backward Compatibility Notes

Several of these enhancements are additive, but the identity and scoping work will require real data migration. Existing chat sessions are currently stored under `anonymous`, so a migration path must decide whether to assign them to a bootstrap admin, archive them as legacy sessions, or preserve them in a global legacy workspace. The same question applies to documents already stored in Chroma: they currently lack user ownership and, in many cases, workspace metadata.

The cleanest migration approach is to introduce new relational tables for users, roles, workspaces, memberships, documents, and versions while keeping the existing chat and retrieval flows available behind compatibility defaults during a transition period. Workspace scoping can initially map all legacy content into a single default workspace such as `general` or `legacy-shared`, allowing retrieval to continue while new uploads use fully scoped metadata.

| Enhancement | Compatibility impact |
| --- | --- |
| Authentication and RBAC | Requires schema changes and session ownership decisions; not backward-compatible without a legacy user strategy. |
| Workspace scoping | Requires metadata migration or a default workspace assignment for all existing documents and sessions. |
| Real-time ingestion progress | Additive; can coexist temporarily with polling. |
| Chroma HTTP standardization | Mostly additive because the current code already assumes HTTP Chroma, but operational rollout must ensure all processes use the same endpoint. |
| Document versioning | Requires document identity rules and may require cleanup of existing duplicate chunks. |
| Cross-encoder reranking | Additive and low-risk if feature-flagged. |
| Contextual chunk enrichment | A reindexing change; existing embeddings can remain temporarily, but best results require re-embedding the corpus. |
| Answer streaming | Additive if the non-streaming endpoint remains available during transition. |
| Document management UI | Additive on the frontend, but more useful once metadata and versioning are in place. |
| Hallucination detection | Additive if warning badges do not alter the response contract abruptly. |

## 6. Suggested Implementation Order

| Phase | Recommendation | Reason |
| --- | --- | --- |
| Phase 1 | Multi-user authentication with RBAC | Identity is the foundation for every later control, especially uploads, deletions, and workspace membership. |
| Phase 2 | Workspace scoping | Once users exist, data isolation should be introduced before the corpus grows further. |
| Phase 3 | Formalize ChromaDB HTTP architecture | Shared visibility and reliable vector operations are prerequisites for versioning and multi-user ingestion at scale. |
| Phase 4 | Document versioning and update support | This prevents duplicate corpus growth and creates the metadata backbone required by document management. |
| Phase 5 | Document management UI | After identity, scoping, and version metadata exist, the UI can expose a meaningful administration surface. |
| Phase 6 | Real-time ingestion progress | This improves operational UX and can be layered onto the now-stable ingestion architecture. |
| Phase 7 | Answer streaming to frontend | Streaming is highly visible product value, but it is easier to land once auth, routing, and event transport patterns are already established. |
| Phase 8 | Hybrid reranking with cross-encoder | Retrieval-quality work is best introduced after core platform boundaries are stable so evaluation is easier to interpret. |
| Phase 9 | Contextual chunk enrichment | This is a stronger retrieval upgrade but likely requires selective reindexing, so it should follow architectural stabilization. |
| Phase 10 | Evaluation and hallucination detection | Confidence instrumentation is most useful once retrieval, ranking, and streaming behavior have settled enough to calibrate thresholds meaningfully. |

This rollout order turns DeepContext into a secure, scoped, operationally visible platform before investing heavily in higher-order relevance and evaluation improvements. That sequencing reduces rework and ensures that quality improvements land on top of the right data and access model.
