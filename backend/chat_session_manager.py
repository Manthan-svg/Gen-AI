import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")


class ChatSessionManager:
    def _connect(self):
        return sqlite3.connect(DB_PATH)

    def _legacy_patterns(self, username: str):
        normalized = str(username or "").strip()
        if not normalized:
            return None
        return (
            f"session_{normalized}",
            f"session_{normalized}_%",
        )

    def _sync_legacy_sessions(self, username: str):
        patterns = self._legacy_patterns(username)
        if not patterns:
            return

        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM chat_sessions WHERE username = ?",
            (username,),
        )
        existing_count = cursor.fetchone()[0]
        if existing_count > 0:
            conn.close()
            return

        cursor.execute(
            """
            SELECT
                session_id,
                MIN(timestamp) AS created_at,
                MAX(timestamp) AS last_message_at,
                MAX(CASE WHEN role = 'human' THEN content ELSE '' END) AS preview
            FROM chat_history
            WHERE session_id = ? OR session_id LIKE ?
            GROUP BY session_id
            ORDER BY COALESCE(MAX(timestamp), MIN(timestamp)) DESC
            """,
            patterns,
        )
        rows = cursor.fetchall()

        for index, (session_id, created_at, last_message_at, preview) in enumerate(rows, start=1):
            cursor.execute(
                """
                INSERT OR IGNORE INTO chat_sessions
                (session_id, username, title, created_at, last_message_at, last_message_preview)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    username,
                    f"Chat {index}",
                    created_at,
                    last_message_at,
                    (preview or "").strip(),
                ),
            )

        conn.commit()
        conn.close()

    def list_sessions(self, username: str):
        self._sync_legacy_sessions(username)

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id, title, created_at, last_message_at, last_message_preview
            FROM chat_sessions
            WHERE username = ?
            ORDER BY COALESCE(last_message_at, created_at) DESC, id DESC
            """,
            (username,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "sessionId": row[0],
                "title": row[1],
                "createdAt": row[2],
                "lastMessageAt": row[3],
                "lastMessagePreview": row[4] or "",
            }
            for row in rows
        ]

    def get_session(self, username: str, session_id: str):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT session_id, title, created_at, last_message_at, last_message_preview
            FROM chat_sessions
            WHERE username = ? AND session_id = ?
            """,
            (username, session_id),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "sessionId": row[0],
            "title": row[1],
            "createdAt": row[2],
            "lastMessageAt": row[3],
            "lastMessagePreview": row[4] or "",
        }

    def create_session(self, username: str, session_id: str, title: str):
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO chat_sessions
            (session_id, username, title, created_at, last_message_at, last_message_preview)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, username, title, now, None, ""),
        )
        conn.commit()
        conn.close()
        return self.get_session(username, session_id)

    def ensure_session(self, username: str, session_id: str, title: str = "New Chat"):
        existing = self.get_session(username, session_id)
        if existing:
            return existing
        return self.create_session(username, session_id, title)

    def update_session(
        self,
        username: str,
        session_id: str,
        title=None,
        last_message_at=None,
        last_message_preview=None,
    ):
        self.ensure_session(username, session_id)

        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if last_message_at is not None:
            updates.append("last_message_at = ?")
            params.append(last_message_at)
        if last_message_preview is not None:
            updates.append("last_message_preview = ?")
            params.append(last_message_preview)

        if not updates:
            return self.get_session(username, session_id)

        params.extend([username, session_id])

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            f"""
            UPDATE chat_sessions
            SET {", ".join(updates)}
            WHERE username = ? AND session_id = ?
            """,
            params,
        )
        conn.commit()
        conn.close()
        return self.get_session(username, session_id)

    def delete_session(self, username: str, session_id: str):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM chat_sessions WHERE username = ? AND session_id = ?",
            (username, session_id),
        )
        cursor.execute(
            "DELETE FROM chat_history WHERE session_id = ?",
            (session_id,),
        )
        conn.commit()
        conn.close()
