import json
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")

class ChatHistroyManager:
    def _ensure_citations_column(self, cursor):
        cursor.execute("PRAGMA table_info(chat_history)")
        columns = {row[1] for row in cursor.fetchall()}
        if "citations" not in columns:
            cursor.execute("ALTER TABLE chat_history ADD COLUMN citations TEXT")

    def save_messages(self, sessionId: str, role: str, content: str, citations=None):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        self._ensure_citations_column(cursor)
        
        cursor.execute(
            "INSERT INTO chat_history (session_id, role, content, citations) VALUES (?, ?, ?, ?)",
            (sessionId, role, content, json.dumps(citations) if citations else None)
        )
        conn.commit()
        conn.close()
        
    def get_history(self, sessionId: str, limit=200):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        self._ensure_citations_column(cursor)
        
        cursor.execute(
            "SELECT role, content, citations FROM chat_history WHERE session_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
            (sessionId, limit,)
        )
        
        result = cursor.fetchall()  
        conn.close()
        
        history = []
        for role, content, citations in reversed(result):
            parsed_citations = []
            if citations:
                try:
                    parsed_citations = json.loads(citations)
                except json.JSONDecodeError:
                    parsed_citations = []
            history.append({
                "role": role,
                "content": content,
                "citations": parsed_citations if role == "ai" else []
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
        
        
