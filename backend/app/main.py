import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.database import engine
from app.core.config import settings
from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.services.workers import recover_interrupted, EXECUTOR
from app.services.frontend import mount_frontend

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app):
    recover_interrupted()
    if settings.seed_demo_data:
        from app.services.demo import seed_demo
        EXECUTOR.submit(seed_demo)
    yield
    EXECUTOR.shutdown(wait=True)


app=FastAPI(title='Avom • Resume Intelligence',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins,allow_credentials=True,allow_methods=['GET','POST','PATCH'],allow_headers=['Content-Type'])
app.include_router(router)
app.include_router(auth_router)


@app.exception_handler(Exception)
async def safe_error(request: Request,exc: Exception):
    logging.error('Request failed (%s)',type(exc).__name__)
    return JSONResponse(status_code=500,content={'detail':'An internal error occurred. Check server configuration and retry.'})


@app.get('/api/v1/health')
def health():
    try:
        with engine.connect() as db: db.execute(text('SELECT 1'))
        return {'status':'ok','database':'connected','semantic_model':settings.model_name,'model_loading':'cached on first matching request'}
    except Exception:
        return JSONResponse(status_code=503,content={'status':'unhealthy','database':'unavailable'})


mount_frontend(app, settings.frontend_dist)
