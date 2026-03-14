import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")

class ChatHistroyManager:
    def save_messages(self, sessionId: str, role: str, content: str):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
            (sessionId, role, content,)
        )
        conn.commit()
        conn.close()
        
    def get_history(self, sessionId: str, limit=20):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
            (sessionId, limit,)
        )
        
        result = cursor.fetchall()
        conn.close()
        
        # Return a 2-element tuple: (role, content)
        history = []
        for role, content in result:
            history.append((role, content))
            
        return history
    
    def deleteChatBySession(self,sessionId:str):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM chat_history WHERE session_id = ?",
            (sessionId,)        
        )
        
        conn.commit()
        conn.close()
        
        
