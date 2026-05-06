from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import initialize_database
from .routers import admin, auth, events

app = FastAPI(title="Aviva Ministerio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_origin_regex=r"^(http://(127\.0\.0\.1|localhost):\d+|https://.*\.vercel\.app)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "Aviva Ministerio API"}


app.include_router(auth.router)
app.include_router(events.router)
app.include_router(admin.router)
