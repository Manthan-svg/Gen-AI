import json
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")

class ChatHistroyManager:
    def save_messages(self, sessionId: str, role: str, content: str, diagrams=None):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        self._ensure_diagrams_column(cursor)
        
        cursor.execute(
            "INSERT INTO chat_history (session_id, role, content, diagrams) VALUES (?, ?, ?, ?)",
            (sessionId, role, content, json.dumps(diagrams) if diagrams else None)
        )
        conn.commit()
        conn.close()
        
    def _ensure_diagrams_column(self, cursor):
        cursor.execute("PRAGMA table_info(chat_history)")
        columns = {row[1] for row in cursor.fetchall()}
        if "diagrams" not in columns:
            cursor.execute("ALTER TABLE chat_history ADD COLUMN diagrams TEXT")
        
    def get_history(self, sessionId: str, limit=200):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        self._ensure_diagrams_column(cursor)
        
        cursor.execute(
            "SELECT role, content, diagrams FROM chat_history WHERE session_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
            (sessionId, limit,)
        )
        
        result = cursor.fetchall()  
        conn.close()
        
        history = []
        for role, content, diagrams_raw in reversed(result):
            parsed_diagrams = []
            if diagrams_raw:
                try:
                    parsed_diagrams = json.loads(diagrams_raw)
                except json.JSONDecodeError:
                    parsed_diagrams = []
            history.append({
                "role": role,
                "content": content,
                "diagrams" : parsed_diagrams if role == "ai" else []
            })
            
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
        
        
