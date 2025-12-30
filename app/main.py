import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.config import settings
from app.logging_conf import configure_logging
from app.telemetry import setup_telemetry

configure_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry(settings.app_name)
    logger.info("Application starting up", extra={"environment": settings.environment})
    yield
    logger.info("Application shutting down")

app = FastAPI(title=settings.app_name, lifespan=lifespan)

if settings.enable_telemetry:
    FastAPIInstrumentor.instrument_app(app)

@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    # Trace ID from OTel if available
    span = trace.get_current_span()
    trace_context = span.get_span_context()
    trace_id = format(trace_context.trace_id, "032x") if trace_context.is_valid else None
    
    extra = {"request_id": request_id}
    if trace_id:
        extra["trace_id"] = trace_id

    # Manually adding context to the logger adapter would be ideal here if using LoggerAdapter
    # For global logger, it's harder in async without context vars. 
    # For simplicity in this template, we assume logs inside endpoints will grab context if needed 
    # or use middleware to set contextvars.
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.get("/health/live")
async def health_live():
    return {"status": "alive"}

@app.get("/health/ready")
async def health_ready():
    # In a real app, check DB connection here
    return {"status": "ready"}

@app.get("/metrics")
async def metrics_endpoint():
    return {"status": "OTLP Export Enabled"}

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Hello from Backend Service"}
