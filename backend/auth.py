"""Password hashing, JWT creation/verification and auth dependencies."""
import hashlib
import os
import time

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt

from database import get_db

SECRET_KEY = os.environ.get("SECURECART_JWT_SECRET", "dev-only-change-me")
ALGORITHM = "HS256"
TOKEN_LIFETIME_SECONDS = 3600


# ---------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$", 1)
    attempt = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return attempt == digest


# --------------------------------------------------------------------- JWT
def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ------------------------------------------------------------ dependencies
def get_current_user(authorization: str = Header(default="")):
    """Any logged-in user. Returns the user row as a dict."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        payload = decode_token(authorization[len("Bearer "):])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    conn = get_db()
    row = conn.execute(
        "SELECT id, username, email, role FROM users WHERE id = ?", (payload["sub"],)
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return dict(row)


def require_admin(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user
