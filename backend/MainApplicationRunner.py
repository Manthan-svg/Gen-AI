from datetime import datetime
import os
import shutil
import requests
from fastapi import Request

from celery_worker import process_document_task
from celery.result import AsyncResult
from chat_history_manager import ChatHistroyManager
from chat_session_manager import ChatSessionManager
from database import initDB
import supervisor
from fastapi import FastAPI,File,UploadFile,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_engine import DeepContextEngine


SLACK_BOT_TOKEN=os.getenv("SLACK_BOT_TOKEN")

app = FastAPI(title="DeepContext API")


origin = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origin,            # Allows requests from your React app
    allow_credentials=True,           # Allows cookies/auth headers
    allow_methods=["*"],              # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],              # Allows all headers
)

engine = DeepContextEngine()
supervisor = supervisor.Supervisor()
history_manager = ChatHistroyManager()
session_manager = ChatSessionManager()

class UserRequest(BaseModel):
    question:str
    sessionId:str


class ChatSessionCreateRequest(BaseModel):
    sessionId: str
    title: str = "New Chat"


class ChatSessionUpdateRequest(BaseModel):
    title: str | None = None
    lastMessageAt: str | None = None
    lastMessagePreview: str | None = None
    

    
@app.post("/")
def run_server():
    return "DeepContext is working properly."


@app.on_event("startup")
def bootstrap_app():
    initDB()

@app.post("/upload")
def upload_docs(file: UploadFile = File(...)):
    
    try:
        file_path = f"./data/{file.filename}"
        with open(file_path ,"wb") as buffer:
            shutil.copyfileobj(file.file,buffer)
            
        
        task = process_document_task.delay(file_path)
        
        return {
            "message": "Upload successful. Audit started in background.",
            "job_id": task.id
        }
        
    except Exception as e:  
        print(e)
        raise HTTPException(status_code=500,detail=str(e))
    

@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    
    from celery_worker import app as celery_app
    result = AsyncResult(job_id,app=celery_app)
    
    if result.state == "SUCCESS":
        status = "completed"
    elif result.state == "FAILURE":
        status = "failed"   
    else:
        status = "processing"

    return {
        "job_id": job_id,
        "status": status,
        "result": result.result if result.state == "SUCCESS" else None
    }
 
@app.get("/retriveAllDocuments")
def getAllDocuments():
    try:
        vector_db = engine.get_vector_db(refresh=True)
        data = vector_db.get()
        
        docs = []
        seen = set()
        
        for d in data.get("metadatas",[]):
            if d.get('source_name') not in seen:
                docs.append({
                    "name": d.get('source_name'),
                    "status": d.get('status', 'unknown'),
                    "time": d.get('ingested_at', 'N/A'),
                })
                seen.add(d.get('source_name'))
                

        return {
            "message": "Success" if docs else "No files found",
            "files": docs 
        }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
    

@app.delete("/deleteDocument/{sourceName}")
def deleteDocument(sourceName: str):
    try:
        vector_db = engine.get_vector_db(refresh=True)
        data = vector_db.get()

        ids = data.get("ids", [])
        metadatas = data.get("metadatas", [])
        normalized_source_name = sourceName.strip().casefold()

        matching_ids = [
            doc_id
            for doc_id, metadata in zip(ids, metadatas)
            if isinstance(metadata, dict)
            and str(metadata.get("source_name", "")).strip().casefold() == normalized_source_name
        ]

        if not matching_ids:
            raise HTTPException(status_code=404, detail=f"Document not found: {sourceName}")

        vector_db.delete(ids=matching_ids)
        engine._try_persist()
        
        return {
            "message":"Document deleted successfully.",
            "sourceName":sourceName,
            "deletedCount": len(matching_ids),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
        
        


@app.get("/chat-sessions")
def get_chat_sessions():
    return {
        "message": "Success",
        "sessions": session_manager.list_sessions("anonymous")
    }


@app.post("/chat-sessions")
def create_chat_session(payload: ChatSessionCreateRequest):
    session = session_manager.create_session(
        "anonymous",
        payload.sessionId,
        payload.title or "New Chat",
    )
    return {
        "message": "Chat session created successfully.",
        "session": session
    }


@app.patch("/chat-sessions/{sessionId}")
def update_chat_session(sessionId: str, payload: ChatSessionUpdateRequest):
    session = session_manager.update_session(
        "anonymous",
        sessionId,
        title=payload.title,
        last_message_at=payload.lastMessageAt,
        last_message_preview=payload.lastMessagePreview,
    )
    return {
        "message": "Chat session updated successfully.",
        "session": session
    }


# ─── AFTER ───────────────────────────────────────────────────────────────────
_SAVE_SKIP_PHRASES = [
    "i don't know", "i do not know", "no information",
    "not available", "no relevant", "cannot find",
    "not mentioned", "not provided", "no details",
    "couldn't find any relevant"
]

@app.post("/get-answer")
def get_answer(question: UserRequest):
    username = "anonymous"
    session_manager.ensure_session(username, question.sessionId)
    history = history_manager.get_history(question.sessionId)
    result = engine.get_answer(question.question, history)

    answer_text = result["answer"]
    citations = result.get("citations", [])
    diagrams = result.get("diagrams",[])
    was_retrieved = result.get("retrieved", True)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Always save the human message
    history_manager.save_messages(question.sessionId, "human", question.question)
    session_manager.update_session(
        username,
        question.sessionId,
        last_message_at=now,
        last_message_preview=question.question
    )
  
    # Only save AI answer to history if it's meaningful.
    # A "I don't know" when docs WERE retrieved is a model failure — don't poison history.
    answer_lower = answer_text.lower().strip()
    is_bad_answer = any(phrase in answer_lower for phrase in _SAVE_SKIP_PHRASES)

    if not (is_bad_answer and was_retrieved):
        history_manager.save_messages(question.sessionId, "ai", answer_text, citations=citations,diagrams=diagrams)
        session_manager.update_session(
            username,
            question.sessionId,
            last_message_at=now,
            last_message_preview=answer_text
        )
    else:
        print(f"⚠️ Skipping history save — model returned weak answer despite retrieved docs.")

    return {
        "answer": answer_text,
        "citations": citations,
        "diagrams":diagrams
    }
     
@app.post("/get-history/{sessionId}")
async def getAllChatHistory(sessionId:str):
    chatHistory = history_manager.get_history(sessionId)
    if len(chatHistory) > 0:
        return {
            "message":"Successfully Retrived Chat History.",
            "chat-history":chatHistory
        }
    else:   
        return {
            "message":"No history for this User found."
        }
    
    
@app.post("/delete-chat/{sessionId}")
async def deleteChatBySessionId(sessionId:str):
    session_manager.delete_session("anonymous", sessionId)
    
    return {
        "message":"Chat Deleted Successfully.."
    }


    
    
@app.post("/slack/events")
async def slack_events(request: Request):
    
    data = await request.json()

    if "challenge" in data:
        return {"challenge" : data["challenge"]}


    event = data.get("event",{})
    
    if event.get("type") == "file_shared":
        file_id = event.get("file_id")

        file_info = requests.get(
            f"https://slack.com/api/files.info?file={file_id}",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        ).json()
        
        if file_info.get("ok"):
            file_data = file_info["file"]
            file_url = file_data.get("url_private_download") # Use the download URL
            
            # Find the channel from the 'shares' object
            shares = file_data.get("shares", {})
            public_shares = shares.get("public", {})
            private_shares = shares.get("private", {})
            
            all_shares = {**public_shares, **private_shares}
            if all_shares:
                # Pass to Celery
                process_document_task.delay(
                    file_url, 
                    is_slack_upload=True,
                    slack_token=SLACK_BOT_TOKEN
                )
       
