# DeepContext

DeepContext is a department-aware enterprise knowledge assistant that ingests internal documents, audits them against existing knowledge, stores verified content in a retrieval system, and answers user questions through a secure chat interface.

The platform combines document ingestion, OCR-assisted extraction for image-heavy files, hybrid retrieval, conflict detection, meeting summarization, and session-based chat history into a single workflow designed for internal knowledge operations.

## Overview

DeepContext is built for teams that need to:

- upload business documents into a searchable knowledge base
- keep knowledge segmented by department
- detect contradictions between newly uploaded content and existing records
- ask natural-language questions over approved content
- preserve chat sessions for ongoing investigative workflows
- render AI answers with readable markdown formatting, including lists, tables, and code blocks
- optionally ingest files shared through Slack

## Key Capabilities

- Department-scoped access control using JWT-based authentication
- Asynchronous document ingestion using FastAPI, Celery, and Redis
- Support for text files, PDFs, scanned PDFs, and standalone images
- OCR-style extraction for image files and scanned PDF pages using a multimodal LLM prompt
- Hybrid retrieval using vector similarity plus BM25 lexical ranking
- Conflict detection between new content and previously stored departmental knowledge
- Meeting transcript summarization with participants, decisions, action items, and fatigue signals
- Persistent vector storage with ChromaDB
- Persistent user and chat history storage with SQLite
- React-based chat interface with session history, markdown-rendered AI responses, and file upload workflow
- Lightweight small-talk handling for greetings, thanks, farewells, and simple assistant-help prompts
- Slack event hook for background ingestion of shared files

## How The System Works

### 1. User authentication

Users sign up or log in from the frontend. The backend stores users in SQLite and issues a JWT containing the username and department. The department claim is then used to scope both ingestion and retrieval.

### 2. Document upload

The frontend uploads documents to the `/upload` endpoint. The API stores the file under `./data/` and dispatches a Celery job so ingestion runs asynchronously and does not block the user interface.

### 3. Ingestion and extraction

The ingestion layer handles files based on file type:

- `txt` and `md`: loaded as text
- text-based `pdf`: extracted through `PyPDFLoader`
- scanned `pdf`: converted page-by-page to images, then processed through a vision/OCR prompt
- `jpg`, `jpeg`, `png`: processed directly through the same vision/OCR prompt

For image-heavy content, DeepContext does not store raw image embeddings. Instead, it converts visual content into retrieval-friendly text first, then indexes that extracted text.

### 4. Chunking and metadata

Extracted content is cleaned, split into chunks, and enriched with metadata such as:

- source file name
- file path
- ingestion timestamp
- department
- audit status
- version

### 5. Conflict audit

Before storage, new chunks are compared with the most relevant existing departmental knowledge. A conflict agent flags only direct contradictions, not omissions or expected role-based differences. Documents are marked as `verified` or `conflict` and surfaced accordingly in the UI.

### 6. Knowledge storage

Processed chunks are stored in ChromaDB with metadata. Chat history and user records are stored in SQLite. Background processing state is handled by Celery with Redis as broker and result backend.

### 7. Question answering

When a user asks a question:

- short conversational inputs such as greetings or `help` are handled before retrieval with fixed assistant replies
- recent chat history is normalized
- the query is retrieved against the department-specific knowledge base
- hybrid search combines semantic retrieval and BM25 lexical ranking
- the best chunks are fused and passed to the LLM as context
- the answer is generated only from retrieved context for knowledge questions
- assistant responses are rendered in the UI as markdown with support for headings, lists, tables, links, blockquotes, and code blocks

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
    |
    +--> Celery Worker --> Redis
    |         |
    |         +--> DataIngestor
    |         +--> ConflictAgent
    |         +--> MeetingAgent
    |         +--> ChromaDB
    |
    +--> DeepContextEngine
              |
              +--> HuggingFace Embeddings
              +--> ChromaDB
              +--> BM25
              +--> Groq LLM
```

## Repository Structure

```text
DeepContext/
├── backend/
│   ├── MainApplicationRunner.py   # FastAPI application and API routes
│   ├── ingestor.py                # Document extraction, OCR-style vision flow, chunking
│   ├── rag_engine.py              # Hybrid retrieval and answer generation
│   ├── supervisor.py              # Ingestion orchestration and audit pipeline
│   ├── celery_worker.py           # Background worker for document processing
│   ├── auth.py                    # Token generation and password hashing
│   ├── auth_routes.py             # Signup and login routes
│   ├── chat_history_manager.py    # SQLite-backed conversation history
│   ├── database.py                # SQLite schema initialization
│   ├── meeting_agent.py           # Transcript summarization workflow
│   ├── conflictAgent.py           # Contradiction detection workflow
│   └── requirements.txt
└── frontend/
    ├── src/App.jsx                # Main authenticated app shell
    ├── src/components/ChatWindow.jsx
    ├── src/components/ChatHistoryDrawer.jsx
    ├── src/components/LoginComponent.jsx
    ├── src/components/SignupComponent.jsx
    ├── src/utils/api.util.js      # Axios client and auth header injection
    └── package.json
```

## Supported Document Types

| File type | Supported | Processing strategy |
| --- | --- | --- |
| `.txt` | Yes | Direct text load |
| `.md` | Yes | Direct text load |
| Text-based `.pdf` | Yes | Native PDF text extraction |
| Scanned `.pdf` | Yes | PDF to images, then OCR-style extraction |
| `.jpg`, `.jpeg`, `.png` | Yes | Direct OCR-style extraction |

## Important Behavior For Mixed Text + Image Documents

DeepContext supports hybrid document content, but with a specific implementation model:

- standalone images are converted to text during ingestion
- scanned PDFs are converted to page images and then converted to text
- text-based PDFs use direct text extraction

This means the platform is multimodal during ingestion, but text-centric during retrieval.

Practical implication:

- if a PDF contains selectable text and also embedded screenshots, charts, or diagrams, the current pipeline primarily relies on the extracted text layer
- image-only information embedded inside an otherwise text-based PDF may not be fully captured unless the file is effectively treated as scanned

## Technology Stack

### Frontend

- React 19
- Vite
- React Router
- Axios
- react-markdown
- remark-gfm
- Tailwind CSS

### Backend

- FastAPI
- LangChain
- ChromaDB
- HuggingFace sentence-transformer embeddings
- Groq-hosted LLMs
- Celery
- Redis
- SQLite

## Prerequisites

Before running the project locally, ensure you have:

- Python 3.10+
- Node.js 18+
- Redis running locally on `localhost:6379`
- Poppler installed for `pdf2image` support
- A valid Groq API key

Depending on your environment, you may also need Python packages used by the codebase in addition to those already pinned in `backend/requirements.txt`, such as:

- `pdf2image`
- `Pillow`
- `passlib[bcrypt]`
- `python-jose`

## Environment Variables

Create a `.env` file in the backend environment with the following variables:

```env
GROQ_API_KEY=your_groq_api_key
SLACK_BOT_TOKEN=your_slack_bot_token_optional
```

`SLACK_BOT_TOKEN` is only required if you want Slack-based ingestion.

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
pip install pdf2image Pillow passlib[bcrypt] python-jose
```

Initialize SQLite:

```bash
python -c "from database import initDB; initDB()"
```

Create the upload directory if it does not already exist:

```bash
mkdir -p data
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

## Running The Application

After all services are started:

1. Open the frontend in the browser
2. Sign up or log in
3. Upload a document
4. Wait for the background job to complete
5. Ask questions in the chat window
6. Review document verification or conflict status in the sidebar

## Core API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/signup` | Register a new user |
| `POST` | `/login` | Authenticate a user |
| `POST` | `/upload` | Upload a document for background processing |
| `GET` | `/job-status/{job_id}` | Check background ingestion status |
| `GET` | `/retriveAllDocuments` | List uploaded documents for the current department |
| `POST` | `/get-answer` | Ask a question against the department knowledge base |
| `POST` | `/get-history/{sessionId}` | Retrieve chat history for a session |
| `POST` | `/delete-chat/{sessionId}` | Delete a chat session |
| `POST` | `/slack/events` | Receive Slack file-share events |

## Department-Aware Security Model

Each user carries a department claim in the JWT. That claim is used to:

- scope document ingestion metadata
- restrict retrieval queries to documents from the same department
- maintain department-specific knowledge boundaries inside a shared deployment

This creates lightweight multitenancy at the department level.

## Chat And Retrieval Design

The question-answering pipeline uses:

- sentence-transformer embeddings for semantic retrieval
- BM25 for lexical relevance
- reciprocal rank fusion to merge both rankings
- an LLM answer layer constrained to retrieved context

The chat system also stores session history in SQLite and uses recent messages to reformulate follow-up questions into standalone queries before retrieval.

## Meeting Transcript Workflow

Files with names containing `meeting` or `transcript` follow a dedicated path:

- content is ingested
- transcript text is aggregated
- a meeting agent produces a structured report
- the summary is stored as a high-value knowledge record

The report includes:

- participants
- summary
- decisions
- action items
- fatigue warning

## Slack Integration

DeepContext includes a Slack event endpoint that listens for `file_shared` events. When configured:

- Slack file metadata is fetched
- the file is downloaded with the bot token
- the Slack channel name is mapped to a department
- the file is sent through the same asynchronous ingestion pipeline

## Current Limitations

- Embedded images inside otherwise text-based PDFs are not fully analyzed in the current pipeline.
- SQLite is suitable for development and small deployments, but not ideal for high-scale concurrent production workloads.
- Authentication secrets are currently code-defined and should be externalized for production deployment.
- File validation, upload size limits, and stronger operational hardening should be added before production use.
- The frontend currently assumes a local backend URL and would benefit from environment-based configuration.

## Production Hardening Recommendations

- Move secrets to environment variables or a secrets manager
- Replace SQLite with PostgreSQL for multi-user production workloads
- Add object storage for uploaded documents
- Add document type validation and antivirus scanning
- Add structured logging, metrics, and health checks
- Containerize the API, worker, Redis, and frontend
- Add CI/CD pipelines and automated tests
- Add role-based access control beyond department scoping

## Why DeepContext

DeepContext is useful when an organization needs a practical internal AI layer over operational documents without losing control of departmental boundaries, document quality, or traceability. It is especially suited to internal knowledge operations, audit workflows, policy assistance, meeting intelligence, and controlled enterprise search.

## License

Add your project license here.
