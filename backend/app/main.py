from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from app import db, errors
from app.auth import CurrentUser, authenticate, create_token
from app.config import get_settings
from app.routers import catalog, incidents, monitoring, reports, shipments


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.get_pool()
    yield
    db.close_pool()


app = FastAPI(title="PharmaTrace API", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins.split(","),
                   allow_methods=["*"], allow_headers=["*"])
errors.register(app)


@app.post("/api/auth/login", tags=["auth"])
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(401, "Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_token(user), "token_type": "bearer", "user": user}


@app.get("/api/auth/me", tags=["auth"])
def me(user: CurrentUser):
    return user


@app.get("/api/health", tags=["auth"])
def health():
    return {"status": "ok"}


for r in (catalog, shipments, monitoring, incidents, reports):
    app.include_router(r.router)
