from calendar import c
from datetime import datetime
import os
from shlex import join
import shutil
import requests
from fastapi import Request

from auth import ALGORITHM, SECRET_KEY
from jose import jwt
from celery_worker import process_document_task
from celery.result import AsyncResult
from chat_history_manager import ChatHistroyManager
from chat_session_manager import ChatSessionManager
from database import initDB
import supervisor
from auth_routes import router as auth_router
from fastapi import FastAPI,File,UploadFile,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import BackgroundTasks
from pydantic import BaseModel
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from ingestor import DataIngestor
from rag_engine import DeepContextEngine


SLACK_BOT_TOKEN=os.getenv("SLACK_BOT_TOKEN")

app = FastAPI(title="DeepContext API")
app.include_router(auth_router,tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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

processing_jobs = {}


engine = DeepContextEngine()
ingestor = DataIngestor()
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

def get_current_user_dept(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        dept = payload.get("dept")
        if dept is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return dept
    except:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        dept = payload.get("dept")
        if username is None or dept is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "department": dept}
    except:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

@app.post("/upload")
def upload_docs(background_tasks:BackgroundTasks ,file:UploadFile = File(...),user_dept:str = Depends(get_current_user_dept)):
    
    try:
        file_path = f"./data/{file.filename}"
        with open(file_path ,"wb") as buffer:
            shutil.copyfileobj(file.file,buffer)
            
        
        task = process_document_task.delay(file_path,user_dept)
        
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
def getAllDocuments(user_dept: str = Depends(get_current_user_dept)):
    try:
        vector_db = engine.get_vector_db(refresh=True)
        data = vector_db.get(where={"department":user_dept})
        
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


@app.get("/chat-sessions")
def get_chat_sessions(current_user: dict = Depends(get_current_user)):
    return {
        "message": "Success",
        "sessions": session_manager.list_sessions(current_user["username"])
    }


@app.post("/chat-sessions")
def create_chat_session(payload: ChatSessionCreateRequest, current_user: dict = Depends(get_current_user)):
    session = session_manager.create_session(
        current_user["username"],
        payload.sessionId,
        payload.title or "New Chat",
    )
    return {
        "message": "Chat session created successfully.",
        "session": session
    }


@app.patch("/chat-sessions/{sessionId}")
def update_chat_session(sessionId: str, payload: ChatSessionUpdateRequest, current_user: dict = Depends(get_current_user)):
    session = session_manager.update_session(
        current_user["username"],
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
def get_answer(question: UserRequest, current_user: dict = Depends(get_current_user)):
    user_dept = current_user["department"]
    username = current_user["username"]
    session_manager.ensure_session(username, question.sessionId)
    history = history_manager.get_history(question.sessionId)
    result = engine.get_answer(question.question, user_dept, history)

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
async def getAllChatHistory(sessionId:str, current_user: dict = Depends(get_current_user)):
    if not session_manager.get_session(current_user["username"], sessionId):
        session_manager.list_sessions(current_user["username"])
    if not session_manager.get_session(current_user["username"], sessionId):
        raise HTTPException(status_code=404, detail="Chat session not found")
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
async def deleteChatBySessionId(sessionId:str, current_user: dict = Depends(get_current_user)):
    session_manager.delete_session(current_user["username"], sessionId)
    
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
            
            # Extract first channel ID available
            all_shares = {**public_shares, **private_shares}
            channel_id = list(all_shares.keys())[0] if all_shares else None

            if channel_id:
                # Get the Department (Channel Name)
                channel_info = requests.get(
                    f"https://slack.com/api/conversations.info?channel={channel_id}",
                    headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
                ).json()
                
                slack_dept = channel_info["channel"]["name"].capitalize() if channel_info.get("ok") else "General"
                # Pass to Celery
                process_document_task.delay(
                    file_url, 
                    user_dept=slack_dept, 
                    is_slack_upload=True,
                    slack_token=SLACK_BOT_TOKEN
                )
       
