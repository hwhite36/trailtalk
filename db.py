import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from os import getenv
from contextlib import contextmanager
from google.genai import types

db_pool = None

def init_db_pool():
    """
    We use a pool to manage all connections to our database, allowing for playing nice with multithreading / gunicorn
    """
    global db_pool
    try:
        db_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=getenv("DATABASE_URL")
        )
        logging.info("Database connection pool initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize database connection pool: {e}")
        raise e

@contextmanager
def get_db_cursor():
    """
    Custom context manager (use via 'with get_db_cursor:' ) that checks out a connection, yields a cursor,
    commits transactions, and returns the connection back to the pool.
    """
    conn = db_pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        yield cur
        conn.commit()
        cur.close()
    except Exception as e:
        conn.rollback()
        logging.error(f"Database error during transaction: {e}")
        raise e
    finally:
        db_pool.putconn(conn)

def init_db_schema():
    logging.info("Initializing database schema...")

    with get_db_cursor() as cur:
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id SERIAL PRIMARY KEY,
                        sender_id VARCHAR(50) NOT NULL,
                        role VARCHAR(20) NOT NULL,
                        content JSONB NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
    
                    CREATE INDEX IF NOT EXISTS idx_sender_id ON conversation_history(sender_id);
                """)
        logging.info("Database schema initialized successfully.")

def save_convo_content_to_db(sender_id: str, content: types.Content):
    content_dict = content.to_dict() if hasattr(content, "to_dict") else content

    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO conversation_history (sender_id, role, content)
            VALUES (%s, %s, %s);
            """,
            (sender_id, content.role, json.dumps(content_dict))
        )

def load_history_from_db(sender_id: str, limit: int = 100) -> list[types.Content]:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT content FROM conversation_history 
            WHERE sender_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s;
            """,
            (sender_id, limit)
        )
        rows = cur.fetchall()

    # Reconstruct Content objects chronologically (DB stores as DESC so we must reverse)
    return [types.Content(**row['content']) for row in reversed(rows)]