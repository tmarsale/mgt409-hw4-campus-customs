"""Customer accounts: registration, login, logout, and "who am I".

Passwords use exactly the scheme already in the `users` table:

    pbkdf2_sha256$<salt>$<hex digest>

where the digest is PBKDF2-HMAC-SHA256 over the UTF-8 password, with the salt
string's UTF-8 bytes as the salt, 120,000 iterations, and a 32-byte output written
as 64 hex characters. Plaintext passwords are never stored or logged.

Login state is a random session token kept in an HttpOnly cookie, so page scripts
cannot read it; the server keeps only a SHA-256 of each token. Sessions live in
memory, so restarting the backend signs everyone out.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator, model_validator

from db import connect

# --- Password hashing (must match the existing accounts exactly) ----------------

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_HEX_CHARS = 32  # 16 random bytes written as hex; the salt *string* is what gets hashed


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(SALT_HEX_CHARS // 2)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS).hex()
    return f"{ALGORITHM}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    candidate = hash_password(password, salt).split("$")[2]
    return hmac.compare_digest(candidate, digest)  # constant-time comparison


# Checked against when an email doesn't exist, so a wrong email takes as long as a wrong password.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))

# --- Sessions -----------------------------------------------------------------------

COOKIE_NAME = "cc_session"
SESSION_SECONDS = 8 * 60 * 60
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"  # set true when served over HTTPS
_sessions: dict[str, tuple[int, float]] = {}  # sha256(token) -> (user_id, expires_at)


def _token_key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _start_session(response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    _sessions[_token_key(token)] = (user_id, time.time() + SESSION_SECONDS)
    response.set_cookie(
        COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True, samesite="lax", secure=COOKIE_SECURE, path="/"
    )


def _session_user_id(token: str | None) -> int | None:
    if not token:
        return None
    entry = _sessions.get(_token_key(token))
    if entry is None:
        return None
    user_id, expires_at = entry
    if expires_at < time.time():
        _sessions.pop(_token_key(token), None)
        return None
    return user_id


# --- Failed-login throttling ----------------------------------------------------------

MAX_FAILURES = 5
FAILURE_WINDOW_SECONDS = 15 * 60
_failures: dict[str, deque[float]] = defaultdict(deque)


def _too_many_failures(key: str) -> bool:
    attempts = _failures[key]
    while attempts and attempts[0] < time.time() - FAILURE_WINDOW_SECONDS:
        attempts.popleft()
    return len(attempts) >= MAX_FAILURES


# --- Validation ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
NAME_RE = re.compile(r"^[^\W\d_](?:[^\W\d_]|[ '\-.])*$")  # letters, with spaces, hyphens, apostrophes, periods
MIN_PASSWORD, MAX_PASSWORD = 8, 128


def _clean_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not EMAIL_RE.match(value):
        raise ValueError("Enter a valid email address.")
    return value


class RegisterIn(BaseModel):
    first_name: str = Field(max_length=200)
    last_name: str = Field(max_length=200)
    email: str = Field(max_length=320)
    password: str = Field(max_length=1000)
    confirm_password: str = Field(max_length=1000)

    @field_validator("first_name", "last_name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("This field is required.")
        if len(value) > 50 or not NAME_RE.match(value):
            raise ValueError("Use letters only (spaces, hyphens, and apostrophes are fine), up to 50 characters.")
        return value

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return _clean_email(value)

    @field_validator("password")
    @classmethod
    def strong_enough(cls, value: str) -> str:
        if len(value) < MIN_PASSWORD or not value.strip():
            raise ValueError(f"Use at least {MIN_PASSWORD} characters.")
        if len(value) > MAX_PASSWORD:
            raise ValueError(f"Use at most {MAX_PASSWORD} characters.")
        return value

    @model_validator(mode="after")
    def passwords_match(self) -> RegisterIn:
        if self.password != self.confirm_password:
            raise ValueError("Passwords don't match.")
        return self


class LoginIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD)


class UserOut(BaseModel):
    """What the website may know about the signed-in customer. Never includes the password hash."""

    id: int
    first_name: str
    last_name: str
    email: str


def _user_out(row: sqlite3.Row) -> UserOut:
    # Older rows may lack first/last name; fall back to splitting the full name.
    first, _, last = (row["name"] or "").partition(" ")
    return UserOut(id=row["id"], first_name=row["first_name"] or first, last_name=row["last_name"] or last, email=row["email"])


# --- Endpoints ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/auth", tags=["accounts"])
INVALID_LOGIN = "Incorrect email or password."
DUPLICATE_EMAIL = "An account with this email already exists. Try logging in."


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, response: Response) -> UserOut:
    password_hash = hash_password(body.password)
    try:
        # The only place the database is opened for writing. One transaction: the duplicate
        # check and the insert succeed or fail together.
        with connect(write=True) as conn, conn:
            if conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (body.email,)).fetchone():
                raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE_EMAIL)
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
                (f"{body.first_name} {body.last_name}", body.email, password_hash, body.first_name, body.last_name),
            )
            row = conn.execute("SELECT id, name, email, first_name, last_name FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:  # the UNIQUE(email) rule caught a simultaneous registration
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE_EMAIL) from None
    _start_session(response, row["id"])  # a new customer is signed in straight away
    return _user_out(row)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, response: Response) -> UserOut:
    email = body.email.strip().lower()
    throttle_key = f"{request.client.host if request.client else '?'}|{email}"
    if _too_many_failures(throttle_key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts. Please wait 15 minutes and try again.")

    with connect() as conn:
        row = conn.execute(
            "SELECT id, name, email, first_name, last_name, password_hash FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()

    # Always run one full hash check, so response time doesn't reveal whether the email exists.
    ok = verify_password(body.password, row["password_hash"] if row else _DUMMY_HASH) and row is not None
    if not ok:
        _failures[throttle_key].append(time.time())
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_LOGIN)
    _failures.pop(throttle_key, None)
    _start_session(response, row["id"])
    return _user_out(row)


@router.get("/me", response_model=UserOut | None)
def me(cc_session: Annotated[str | None, Cookie()] = None) -> UserOut | None:
    """The signed-in customer, or null when nobody is signed in (a normal state, not an error)."""
    user_id = _session_user_id(cc_session)
    if user_id is None:
        return None
    with connect() as conn:
        row = conn.execute("SELECT id, name, email, first_name, last_name FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user_out(row) if row else None


def signed_in_user(cc_session: str | None) -> UserOut | None:
    """The customer behind a session cookie (id, names, email; never the password hash), or None."""
    user_id = _session_user_id(cc_session)
    if user_id is None:
        return None
    with connect() as conn:
        row = conn.execute("SELECT id, name, email, first_name, last_name FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user_out(row) if row else None


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, cc_session: Annotated[str | None, Cookie()] = None) -> None:
    if cc_session:
        _sessions.pop(_token_key(cc_session), None)
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=COOKIE_SECURE)
