import sqlite3
import hashlib
import secrets
import os

if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/users.db"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def init_db():
    """Initializes the database and creates default accounts."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            has_access BOOLEAN DEFAULT 0
        )
    ''')
    
    # Migration: Add has_access if it doesn't exist in an existing table
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN has_access BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists

    cursor.execute("SELECT * FROM users;")
    for userdata in cursor.fetchall():
        print(userdata)
    
    # Create default admin and coder accounts if they don't exist
    default_users = [
        ("admin", "password")
    ]
    
    for username, password in default_users:
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if not cursor.fetchone():
            pw_hash = hashlib.sha256(password.encode()).hexdigest()
            api_key = secrets.token_hex(16)
            # Default admin/coder to has_access=1
            cursor.execute(
                "INSERT INTO users (username, password_hash, api_key, has_access) VALUES (?, ?, ?, ?)",
                (username, pw_hash, api_key, 1)
            )
            print(f":> Created default user '{username}' with API Key: {api_key}")
        else:
            # Migration/Patch: Ensure existing admin/coder have access enabled
            cursor.execute("UPDATE users SET has_access = 1 WHERE username = ?", (username,))

            
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    """Registers a new user and returns their API key."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    pw_hash = hash_password(password)
    api_key = secrets.token_hex(16)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, api_key, has_access) VALUES (?, ?, ?, ?)",
            (username, pw_hash, api_key, 1)
        )
        conn.commit()
        return api_key
    except sqlite3.IntegrityError:
        return None  # User already exists
    finally:
        conn.close()

def authenticate(username, password, api_key=None):
    """Checks if the credentials match. api_key is optional for login."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    pw_hash = hash_password(password)
    
    if api_key:
        cursor.execute(
            "SELECT id FROM users WHERE username = ? AND password_hash = ? AND api_key = ?",
            (username, pw_hash, api_key)
        )
    else:
        cursor.execute(
            "SELECT id FROM users WHERE username = ? AND password_hash = ?",
            (username, pw_hash)
        )
        
    user = cursor.fetchone()
    conn.close()
    return user is not None

def get_user_data(username):
    """Retrieves all user info for the dashboard."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT username, api_key, has_access FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def toggle_access(username, state):
    """Toggles the has_access state for a user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET has_access = ? WHERE username = ?", (1 if state else 0, username))
    conn.commit()
    conn.close()

def check_access(username, api_key):
    """Verifies user exists and has_access is true (or admin/coder)."""
    if username.lower() in ["admin", "coder"]:
        return True
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT has_access FROM users WHERE username = ? AND api_key = ?", (username, api_key))
    row = cursor.fetchone()
    conn.close()
    return row and row[0] == 1

def is_authorized(username):
    """Legacy check - use check_access instead for more robust validation."""
    return username.lower() in ["admin", "coder"]

if __name__ == "__main__":
    init_db()
