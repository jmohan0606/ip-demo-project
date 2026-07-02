from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import initialize_db
from .routers import health, catalog, ingestion, graph

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_db()
    yield

app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(catalog.router)
app.include_router(ingestion.router)
app.include_router(graph.router)

@app.get("/")
def root():
    return {"name": settings.app_name, "version": "0.2.0", "docs": "/docs"}
