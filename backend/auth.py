"""Password hashing, JWT creation/verification and auth dependencies."""
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Header, HTTPException
from jose import JWTError, jwt

from database import get_db

_ph = PasswordHasher()

# VULN-05: hardcoded JWT signing secret committed in source code (CWE-798)
SECRET_KEY = "securecart-secret-key-123"
ALGORITHM = "HS256"


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
    # VULN-06: no "exp" claim, so tokens never expire (CWE-613)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
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
