from fastapi import APIRouter, HTTPException, status

from ..auth import create_token, hash_password, verify_password
from ..database import execute, fetch_one
from ..schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    email = payload.email.strip().lower()
    user = fetch_one(
        "SELECT id, name, email, password_hash, role FROM users WHERE email = ?",
        (email,),
    )

    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas.")

    user_data = dict(user)
    return TokenResponse(
        access_token=create_token(user_data),
        role=user_data["role"],
        name=user_data["name"],
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> TokenResponse:
    email = payload.email.lower()
    exists = fetch_one("SELECT id FROM users WHERE email = ?", (email,))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail ja tem cadastro.")

    user_id = execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (payload.name.strip(), email, hash_password(payload.password), "member"),
    )
    user_data = {
        "id": user_id,
        "name": payload.name.strip(),
        "email": email,
        "role": "member",
    }
    return TokenResponse(
        access_token=create_token(user_data),
        role="member",
        name=user_data["name"],
    )
