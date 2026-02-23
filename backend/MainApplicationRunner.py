import os
import shutil
from fastapi import FastAPI,File,UploadFile,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingestor import DataIngestor
from rag_engine import DeepContextEngine

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
ingestor = DataIngestor()

class UserRequest(BaseModel):
    question:str
    
@app.post("/")
def run_server():
    return "DeepContext is working properly."

@app.post("/upload")
def upload_docs(file:UploadFile = File(...)):
    
    try:
        file_path = f"./data/{file.filename}"
        with open(file_path ,"wb") as buffer:
            shutil.copyfileobj(file.file,buffer)
            
    
        chunks = ingestor.ingestion_documents(file_path)
        if chunks:
            ids = [f"{file.filename}_{i}" for i in range(len(chunks))]
            engine.vector_db.add_documents(chunks,ids = ids)
            return {"message": f"Successfully ingested {file.filename}", "chunks": len(chunks)}
        
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    

@app.post("/get-answer")
def get_answer(question:UserRequest):
    result = engine.get_answer(question.question)
    
    return {
        "answer": result["answer"]
    }
        






