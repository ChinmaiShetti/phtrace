"""Password login, JWT bearer tokens and role checks."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import psycopg
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pydantic import BaseModel

from app import db
from app.config import get_settings

hasher = PasswordHash.recommended()
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

ROLES = ("operator", "investigator", "quality_manager", "admin")


class User(BaseModel):
    staff_id: int
    staff_name: str
    email: str
    role: str


def create_token(user: User) -> str:
    s = get_settings()
    payload = {"sub": str(user.staff_id), "role": user.role,
               "exp": datetime.now(UTC) + timedelta(minutes=s.jwt_expire_minutes)}
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def authenticate(email: str, password: str) -> User | None:
    with db.get_pool().connection() as conn:
        row = conn.execute("SELECT staff_id, staff_name, email, role, password_hash FROM staff "
                           "WHERE lower(email) = lower(%s) AND account_status = 'active'", [email]).fetchone()
    if row is None or not hasher.verify(password, row["password_hash"]):
        return None
    return User(**{k: row[k] for k in ("staff_id", "staff_name", "email", "role")})


def current_user(token: Annotated[str, Depends(oauth2)]) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                                 headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
        staff_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized from None
    with db.get_pool().connection() as conn:
        row = conn.execute("SELECT staff_id, staff_name, email, role FROM staff "
                           "WHERE staff_id = %s AND account_status = 'active'", [staff_id]).fetchone()
    if row is None:
        raise unauthorized
    return User(**row)


CurrentUser = Annotated[User, Depends(current_user)]


def require(*roles: str):
    """Dependency: the caller must hold one of the given roles."""
    def check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {', '.join(roles)}")
        return user
    return check


def get_db(user: CurrentUser) -> Iterator[psycopg.Connection]:
    yield from db.transaction(user.staff_id)


Db = Annotated[psycopg.Connection, Depends(get_db)]
