import json
import sqlite3

class ChatHistroyManager:
    def save_messages(self, sessionId: str, role: str, content: str, sources=None):
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        # Convert sources list to a JSON string for storage
        sources_json = json.dumps(sources) if sources else "[]"
        
        cursor.execute(
            "INSERT INTO chat_history (session_id, role, content, sources) VALUES (?, ?, ?, ?)",
            (sessionId, role, content, sources_json)
        )
        conn.commit()
        conn.close()
        
    def get_history(self, sessionId: str, limit=20):
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        # Retrieve the sources column too
        cursor.execute(
            "SELECT role, content, sources FROM chat_history WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
            (sessionId, limit)
        )
        
        result = cursor.fetchall()
        conn.close()
        
        # Return a 3-element tuple: (role, content, sources_list)
        history = []
        for role, content, sources_json in result:
            # Convert the JSON string back into a Python list
            sources_list = json.loads(sources_json) if sources_json else []
            history.append((role, content, sources_list))
            
        return history
    
    def deleteChatBySession(self,sessionId:str):
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM chat_history WHERE session_id = ?",
            (sessionId,)        
        )
        
        conn.commit()
        conn.close()
        
        