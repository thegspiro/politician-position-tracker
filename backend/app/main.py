from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import issues, politicians, statements

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Politician Position Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(politicians.router)
app.include_router(issues.router)
app.include_router(statements.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
