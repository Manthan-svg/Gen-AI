import os
import sqlite3
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from auth import create_access_token,verify_password,verify_token,hash_password

router = APIRouter()

class UserAuth(BaseModel):
    username:str
    password:str
    department: str = "General"
    
    
def getDBConnection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")
    conn = sqlite3.connect(db_path)
    return conn
    
@router.post("/signup")
def sign_up(user:UserAuth):
    conn =getDBConnection()
    cursor = conn.cursor()
    
    try:
        hashedPass = hash_password(user.password)
        result = cursor.execute(
            "INSERT INTO users (username, hashed_password, department) VALUES (?, ?, ?)",
            (user.username,hashedPass,user.department)
        )

        if result :
            token = create_access_token(data={
                "sub":user.username,
                "dept":user.department
            })
        
        conn.commit()
        return {"message": "User created successfully" ,"Access-Token":token,"user":user}
    
    except sqlite3.InternalError:
        raise HTTPException(status_code=400,detail="Username already exists") 

    finally:
        conn.close()
        

@router.post("/login")
def login(user:UserAuth):
    conn = getDBConnection()
    cursor = conn.cursor()  
    
    try:
        cursor.execute("SELECT hashed_password,department FROM users WHERE username = ?" , (user.username,))
        result = cursor.fetchone()
        
        if not result :
            return {"message":"Unable to Login User!Please SignUp."}
        
        if result and verify_password(user.password,result[0]):
            token = create_access_token(data={
                "sub":user.username,
                "dept":result[1]
            })        
            return {
                "message":"User Login Successgully..",
                "Token":token,
                "user":user
            }
        
    except Exception as e:
        raise HTTPException(status_code=401,detail=str(e))
    finally:
        conn.close()
    
