# DeepContext

DeepContext is a department-aware enterprise knowledge assistant for internal documents. It ingests business files, stores department-scoped knowledge in ChromaDB, and answers questions through a secure chat UI with markdown rendering, source citations, and diagram support.

The current codebase combines:

- JWT-based authentication with department scoping
- asynchronous document ingestion with FastAPI, Celery, and Redis
- hybrid retrieval using vector search plus BM25
- OCR-style extraction for image-heavy content
- persistent chat history and named chat sessions in SQLite
- diagram extraction and rendering for Mermaid and PlantUML content
- Slack-triggered background ingestion for shared files

## Overview

DeepContext is built for teams that need to:

- upload internal documents into a searchable knowledge base
- isolate retrieval results by department
- ask natural-language questions against approved content
- keep separate multi-session chat histories per user
- render AI answers with markdown, citations, and diagrams
- ingest files from Slack with the same backend pipeline

## Key Capabilities

- Department-scoped access control using JWT claims
- FastAPI backend with Celery background ingestion jobs
- ChromaDB knowledge storage with SQLite-backed users, chat history, and chat sessions
- Hybrid retrieval using sentence-transformer embeddings plus BM25 rank fusion
- OCR-style vision extraction for scanned PDFs and image uploads
- Meeting transcript summarization flow for files containing `meeting` or `transcript`
- Markdown-rendered answers with headings, lists, tables, links, quotes, and code blocks
- Inline citation generation with grouped source cards in the UI
- Diagram-aware ingestion for Mermaid and PlantUML source content
- Diagram-aware answers that can return rendered Mermaid or PlantUML diagrams directly
- Lightweight small-talk handling for greetings, thanks, farewells, and help prompts
- Chat history drawer with new-chat creation, per-session previews, and session deletion

## How It Works

### 1. Authentication and department scoping

Users sign up or log in from the frontend. The backend stores users in SQLite and issues a JWT containing the username and department. That department value is used to scope both ingestion metadata and retrieval queries.

### 2. Document upload and background processing

The frontend uploads files to `/upload`. The API writes the file to `backend/data/` and dispatches a Celery task so ingestion runs asynchronously without blocking the UI.

### 3. Extraction and ingestion

The ingestion layer chooses a strategy based on file type:

- `.txt`, `.md`, `.puml`, `.mmd`, `.mermaid`: direct text loading
- text-based `.pdf`: native PDF text extraction
- scanned `.pdf`: page conversion plus vision/OCR prompting
- `.jpg`, `.jpeg`, `.png`: direct vision/OCR prompting

For image-heavy inputs, DeepContext converts visual content into retrieval-friendly text before indexing.

During ingestion, the system also detects diagram blocks:

- PlantUML blocks using `@startuml ... @enduml`
- Mermaid blocks inside fenced code blocks
- raw Mermaid files in `.mmd` and `.mermaid`

Detected diagrams are stored as separate retrievable records alongside cleaned text chunks.

### 4. Storage

DeepContext persists:

- users in SQLite
- chat history in SQLite
- chat session metadata in SQLite
- document chunks and diagram records in ChromaDB
- job state in Redis through Celery

### 5. Question answering

When a user asks a question:

- very short conversational prompts can be answered as small talk without retrieval
- recent chat history is normalized for follow-up handling
- the latest question may be rewritten into a standalone question
- hybrid retrieval pulls department-scoped chunks from ChromaDB and BM25
- if the prompt asks for a diagram, relevant Mermaid or PlantUML records are returned directly
- otherwise the LLM answers from retrieved context only
- the answer is normalized into markdown
- claim-level citations are attached to the response
- the frontend renders markdown, diagrams, and grouped source cards

## Architecture

```text
React Frontend
    |
    v
FastAPI Backend
    |
    +--> SQLite
    |      - users
    |      - chat_history
    |      - chat_sessions
    |
    +--> Celery Worker --> Redis
    |         |
    |         +--> Supervisor
    |         +--> DataIngestor
    |         +--> MeetingAgent
    |         +--> ChromaDB
    |
    +--> DeepContextEngine
              |
              +--> HuggingFace Embeddings
              +--> ChromaDB
              +--> BM25
              +--> Groq LLM
              +--> Diagram Detection
```

## Repository Structure

```text
DeepContext/
├── backend/
│   ├── MainApplicationRunner.py   # FastAPI app and API routes
│   ├── ingestor.py                # File extraction, OCR-style ingestion, diagram parsing
│   ├── rag_engine.py              # Hybrid retrieval, answer generation, citation logic
│   ├── diagram_utils.py           # Diagram detection and PlantUML URL generation
│   ├── supervisor.py              # Ingestion orchestration and meeting/file branching
│   ├── celery_worker.py           # Background document processing
│   ├── chat_history_manager.py    # SQLite-backed message history with citations/diagrams
│   ├── chat_session_manager.py    # SQLite-backed chat session metadata
│   ├── database.py                # SQLite schema initialization and migrations
│   ├── meeting_agent.py           # Meeting transcript summarization
│   ├── auth.py                    # JWT and password helpers
│   ├── auth_routes.py             # Signup and login routes
│   └── requirements.txt
└── frontend/
    ├── src/App.jsx
    ├── src/components/ChatWindow.jsx
    ├── src/components/ChatHistoryDrawer.jsx
    ├── src/components/MarkdownRenderer.jsx
    ├── src/components/DiagramRenderer.jsx
    ├── src/components/LoginComponent.jsx
    ├── src/components/SignupComponent.jsx
    ├── src/utils/chatSessions.util.js
    ├── src/utils/api.util.js
    └── package.json
```

## Supported Document Types

| File type | Supported | Processing strategy |
| --- | --- | --- |
| `.txt` | Yes | Direct text load |
| `.md` | Yes | Direct text load |
| `.puml` | Yes | Text load plus PlantUML extraction |
| `.mmd` | Yes | Text load plus Mermaid extraction |
| `.mermaid` | Yes | Text load plus Mermaid extraction |
| Text-based `.pdf` | Yes | Native PDF text extraction |
| Scanned `.pdf` | Yes | Page images plus vision/OCR extraction |
| `.jpg`, `.jpeg`, `.png` | Yes | Vision/OCR extraction |

## Diagram Support

DeepContext now supports diagram-aware retrieval and UI rendering:

- Mermaid diagrams are rendered client-side in the frontend
- PlantUML diagrams are displayed through generated `plantuml.com` image URLs
- diagram records are stored separately from surrounding text chunks
- diagram questions can return diagrams even when no prose answer is needed
- diagram responses still include source citations

Examples of supported asks:

- "Show me the architecture diagram"
- "Render the Mermaid flowchart from the onboarding doc"
- "Do we have a UML diagram for this process?"

## Chat Sessions and History

Chat is no longer modeled as a single flat history per user. The current application supports multiple sessions per user, with:

- explicit session creation
- session titles
- preview text from the latest message
- created-at and last-message timestamps
- history retrieval per session
- session deletion from the UI

Older `chat_history`-only conversations are also synced into `chat_sessions` when needed.

## Technology Stack

### Frontend

- React 19
- Vite
- React Router
- Axios
- react-markdown
- remark-gfm
- Mermaid
- Tailwind CSS 4

### Backend

- FastAPI
- Celery
- Redis
- LangChain
- ChromaDB
- HuggingFace sentence-transformer embeddings
- Groq-hosted LLMs
- SQLite
- pdf2image
- Pillow

## Prerequisites

Before running the project locally, ensure you have:

- Python 3.10+
- Node.js 18+
- Redis running locally on `localhost:6379`
- Poppler installed for `pdf2image`
- a valid `GROQ_API_KEY`
- the HuggingFace embedding model available locally, because retrieval uses `local_files_only=True`

Depending on your environment, you may also need these Python packages in addition to those pinned in `backend/requirements.txt`:

- `pdf2image`
- `Pillow`
- `passlib[bcrypt]`
- `python-jose`
- `celery`
- `redis`
- `python-multipart`
- `overrides`

## Environment Variables

Create a `.env` file for the backend with:

```env
GROQ_API_KEY=your_groq_api_key
SLACK_BOT_TOKEN=your_optional_slack_bot_token
```

`SLACK_BOT_TOKEN` is only required for Slack-based ingestion.

## Local Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd DeepContext
```

### 2. Set up the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pdf2image Pillow passlib[bcrypt] python-jose celery redis python-multipart overrides
mkdir -p data
python -c "from database import initDB; initDB()"
```

Start the API:

```bash
uvicorn MainApplicationRunner:app --host 0.0.0.0 --port 2020 --reload
```

### 3. Start Redis

```bash
redis-server
```

### 4. Start the Celery worker

Open a second terminal:

```bash
cd backend
source .venv/bin/activate
celery -A celery_worker.app worker --loglevel=info
```

### 5. Set up the frontend

Open a third terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend at `http://localhost:2020`.

## Running the Application

After all services are started:

1. Open the frontend.
2. Sign up or log in.
3. Upload a supported document.
4. Wait for the ingestion job to complete.
5. Start a new chat or reopen an existing session.
6. Ask document questions, including diagram-oriented prompts if relevant.
7. Review citations, rendered diagrams, and document status in the UI.

## Core API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/signup` | Register a new user |
| `POST` | `/login` | Authenticate a user |
| `POST` | `/upload` | Upload a document for background processing |
| `GET` | `/job-status/{job_id}` | Check ingestion job status |
| `GET` | `/retriveAllDocuments` | List department-visible ingested documents |
| `GET` | `/chat-sessions` | List chat sessions for the current user |
| `POST` | `/chat-sessions` | Create a chat session |
| `PATCH` | `/chat-sessions/{sessionId}` | Update title or preview metadata for a session |
| `POST` | `/get-answer` | Ask a question against the department knowledge base |
| `POST` | `/get-history/{sessionId}` | Retrieve chat history for one session |
| `POST` | `/delete-chat/{sessionId}` | Delete a session and its messages |
| `POST` | `/slack/events` | Receive Slack file-share events |

## Meeting Transcript Workflow

Files whose names contain `meeting` or `transcript` follow a dedicated path:

- the content is ingested
- the text is aggregated into a full transcript body
- the meeting agent produces a structured summary
- the summary is stored as a high-value knowledge record in ChromaDB

The generated report includes:

- participants
- summary
- decisions
- action items
- fatigue warning

## Slack Integration

DeepContext includes a Slack event endpoint for `file_shared` events. When configured:

- the backend fetches Slack file metadata
- the file is downloaded with the bot token
- the channel name is mapped to a department
- the same Celery ingestion pipeline processes the file

## Current Limitations

- Embedded images inside otherwise text-based PDFs are still not deeply analyzed unless the PDF behaves like a scanned document.
- PlantUML rendering depends on public `plantuml.com` image generation.
- The embedding model must already exist in the local HuggingFace cache because retrieval is configured with `local_files_only=True`.
- SQLite is fine for local and lightweight use, but it is not ideal for larger concurrent production workloads.
- Authentication secrets are still code-defined in parts of the backend and should be fully externalized before production use.
- File validation, upload size limits, and stronger operational hardening are still needed.
- The frontend is still pinned to a local backend URL instead of environment-based configuration.

## Production Hardening Ideas

- move secrets to environment variables or a secrets manager
- replace SQLite with PostgreSQL
- add object storage for uploaded documents
- add file validation, size limits, and malware scanning
- add structured logging, metrics, and health checks
- containerize the API, worker, Redis, and frontend
- add automated tests and CI/CD
- expand authorization beyond department-only scoping

## License

Add your project license here.
