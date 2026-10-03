import json
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import logging
from pathlib import Path
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
    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        logging.error(f"Schema file not found at {schema_path}")
        return

    schema_sql = schema_path.read_text(encoding="utf-8")

    logging.info("Initializing database schema from schema.sql...")
    with get_db_cursor() as cur:
        cur.execute(schema_sql)
    logging.info("Database schema initialized successfully.")


def save_convo_content_to_db(user_id: str, content: types.Content) -> dict:
    """
    Saves a single conversation element to the database.
    :param user_id: user's ID
    :param content: the conversation Content object to be saved
    :return: a dictionary of the element inserted into the DB
    """
    content_dict = content.to_dict() if hasattr(content, "to_dict") else content
    role = content_dict.get("role", "user")

    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO conversation_history (user_id, role, content)
            VALUES (%s, %s, %s::jsonb)
            RETURNING id, user_id, role, content, created_at;
            """,
            (user_id, role, json.dumps(content_dict))
        )
        record = cur.fetchone()
        logging.debug(f"Saved conversation record ID {record['id']} for user_id {user_id}")

    return dict(record)

def save_convo_batch_to_db(user_id: str, content_batch: list) -> list:
    """
    Saves a sequence of conversation items (user question, tool calls, tool responses, model response)
    to the database in a single atomic transaction.
    :param user_id: User's ID
    :param content_batch: list of Content objects to record to the database, in the order they should be committed.
    :return: a list of the elements inserted into the DB
    """
    if not content_batch:
        return []

    # Prepare parameter tuples for bulk insertion: (user_id, role, jsonb_content)
    records_to_insert = []
    for item in content_batch:
        content_dict = item.to_dict() if hasattr(item, "to_dict") else item
        role = content_dict.get("role", "user")
        records_to_insert.append((user_id, role, json.dumps(content_dict)))

    query = """
        INSERT INTO conversation_history (user_id, role, content)
        VALUES %s
        RETURNING id, user_id, role, content, created_at;
    """
    with get_db_cursor() as cur:
        execute_values(
            cur,
            query,
            records_to_insert,
            template="(%s, %s, %s::jsonb)"
        )
        saved_records = cur.fetchall()
        logging.debug(f"Saved batch of {len(saved_records)} records for user_id {user_id}")

    return [dict(r) for r in saved_records]


def load_history_from_db(user_id: str, limit: int = 50, session_hours: int = 4) -> list[types.Content]:
    """
    Loads recent conversation context for a user by user ID, bounded by a maximum turn limit and an inactivity cutoff
    window. Guarantees the history payload starts with a 'user' message, as required by the Gemini API.

    :param user_id: user's ID.
    :param limit: Maximum number of recent messages to retrieve.
    :param session_hours: Number of hours after which a session is considered expired.
    :return: A list of types.Content objects ordered chronologically (Oldest -> Newest).
    """

    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT content 
            FROM conversation_history
            WHERE user_id = %s
              AND created_at >= NOW() - (%s || ' hours')::INTERVAL
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (user_id, str(session_hours), limit))
        rows = cur.fetchall()

    if not rows:
        return []

    # Reconstruct Content objects chronologically (oldest -> newest)
    history = [types.Content(**row['content']) for row in reversed(rows)]

    # Fast-forward past any boundary artifacts at the start of the window
    # A valid Gemini history payload MUST start with role="user" that is NOT a tool response.
    start_idx = 0
    while start_idx < len(history):
        first = history[start_idx]

        # Drop model messages
        if first.role != "user":
            start_idx += 1
            continue

        # Drop orphaned function_responses
        has_tool_response = any(
            hasattr(part, "function_response") and part.function_response is not None
            for part in (first.parts or [])
        )
        if has_tool_response:
            start_idx += 1
            continue

        break

    return history[start_idx:]


def check_if_user_exists(phone_num: str) -> bool:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 
                FROM users 
                WHERE phone_number = %s
            );
            """,
            (phone_num,)
        )
        result = cur.fetchone()
    return result['exists']


def get_or_create_user(phone_num: str) -> dict:
    """
    Fetch or create a new user if no user with the phone number exists.
    We do a no-op on conflict to secure the lock and execute the return statement.
    :param phone_num: user's phone number
    :return: the new user object
    """
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (phone_number)
            VALUES (%s)
            ON CONFLICT (phone_number) 
            DO UPDATE SET phone_number = EXCLUDED.phone_number
            RETURNING id, phone_number, created_at, is_opted_out, opted_out_at;
            """,
            (phone_num,)
        )
        new_user = cur.fetchone()
        return dict(new_user)

def update_user_opt_out_status(user_id: int, opt_out: bool) -> None:
    """
    Sets the opt-out status for a user.
    When opting out, records the opt_out_at timestamp.
    When re-subscribing (opt_out=False), clears opted_out_at.
    """
    with get_db_cursor() as cur:
        if opt_out:
            cur.execute(
                """
                UPDATE users 
                SET is_opted_out = TRUE, 
                    opted_out_at = CURRENT_TIMESTAMP
                WHERE id = %s;
                """,
                (user_id,)
            )
        else:
            cur.execute(
                """
                UPDATE users 
                SET is_opted_out = FALSE, 
                    opted_out_at = NULL
                WHERE id = %s;
                """,
                (user_id,)
            )
