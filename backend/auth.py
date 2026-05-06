from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import Depends, Header, HTTPException, status

from .database import fetch_one

SECRET_KEY = os.getenv("AVIVA_SECRET_KEY", "troque-esta-chave-em-producao")
TOKEN_TTL_SECONDS = 60 * 60 * 12


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or base64.urlsafe_b64encode(os.urandom(16)).decode()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180_000)
    return f"pbkdf2_sha256${salt}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, salt, stored_digest = password_hash.split("$", 2)
    except ValueError:
      return False

    if algorithm != "pbkdf2_sha256":
      return False

    candidate = hash_password(password, salt).split("$", 2)[2]
    return hmac.compare_digest(candidate, stored_digest)


def _b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _b64decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding)


def create_token(user: dict[str, Any]) -> str:
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "name": user["name"],
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64encode(signature)}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        body, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido.") from exc

    expected = _b64encode(hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido.")

    payload = json.loads(_b64decode(body))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada.")
    return payload


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login necessário.")

    payload = decode_token(authorization.removeprefix("Bearer ").strip())
    user = fetch_one("SELECT id, name, email, role FROM users WHERE id = ?", (payload["sub"],))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário não encontrado.")
    return dict(user)


def require_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso restrito a administradores.")
    return user
