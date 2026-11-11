"""Password hashing, JWT creation/verification and auth dependencies."""
import os
import time

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from dotenv import load_dotenv
from fastapi import Header, HTTPException
from jose import JWTError, jwt

from database import get_db

_ph = PasswordHasher()

# VULN-05 FIXED: the JWT signing secret is loaded from the environment, never
# committed to source (CWE-798). load_dotenv() reads backend/.env if present
# (see backend/.env.example); it is a no-op if the file doesn't exist. The app
# refuses to start if the secret is missing either way, so a deployment can
# never silently fall back to a default/guessable value.
load_dotenv()
try:
    SECRET_KEY = os.environ["SECURECART_JWT_SECRET"]
except KeyError as exc:
    raise RuntimeError(
        "SECURECART_JWT_SECRET is not set. Copy backend/.env.example to "
        "backend/.env and set a long random value "
        '(e.g. `python3 -c "import secrets; print(secrets.token_hex(32))"`), '
        "or export SECURECART_JWT_SECRET directly."
    ) from exc

ALGORITHM = "HS256"
# VULN-06 FIXED: short-lived tokens (CWE-613). A stolen/leaked token is only
# useful for this long.
TOKEN_LIFETIME_SECONDS = 30 * 60


# ---------------------------------------------------------------- passwords
# VULN-03 FIXED: Argon2id, salted automatically per-hash by argon2-cffi
# (CWE-328 / CWE-759). `_ph.hash()` embeds a random salt and the algorithm
# parameters in its output, so no salt column is needed.
def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, stored: str) -> bool:
    try:
        return _ph.verify(stored, password)
    except VerifyMismatchError:
        return False


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
