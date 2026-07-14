"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import auth, comments, tasks, users

app = FastAPI(
    title="Task Manager API",
    description="Modern FastAPI rewrite of the original py4web task manager.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(comments.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
