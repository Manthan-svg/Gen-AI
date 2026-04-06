import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")

def initDB():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
    
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                citations TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )            
        ''')

        cursor.execute("PRAGMA table_info(chat_history)")
        columns = {row[1] for row in cursor.fetchall()}
        if "citations" not in columns:
            cursor.execute("ALTER TABLE chat_history ADD COLUMN citations TEXT")
        if "diagrams" not in columns:
            cursor.execute("ALTER TABLE chat_history ADD COLUMN diagrams TEXT")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                username TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_message_at DATETIME,
                last_message_preview TEXT
            )
        ''')
        
        

        conn.commit()
        conn.close()
    except Exception as e:
        return {"message":e}
    
    

    
    
    


    
    

    
    
