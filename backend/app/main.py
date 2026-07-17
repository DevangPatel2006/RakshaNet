import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import SessionLocal
from app.db.init_db import init_db
from app.routers import auth, complaints, cases, counterfeit, graph, evidence, alerts, geo, transactions, admin, speech
from app.services.event_bus import get_event_bus

app = FastAPI(title="RakshaNet Core API Gateway")

cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

# Enable CORS preflight checks and cross-origin access
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global Error Hook: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "A security infrastructure pipeline error occurred. Audit logs recorded."}
    )

@app.on_event("startup")
def startup_event():
    # Security verification
    if settings.ENV != "dev":
        if settings.JWT_SECRET == "supersecretkeyforrakshanetdev":
            raise RuntimeError(
                f"CRITICAL SECURITY ERROR: Application is running in non-development mode (ENV={settings.ENV}), but the default JWT_SECRET ('supersecretkeyforrakshanetdev') is still in use! Startup aborted."
            )
        if settings.NEO4J_PASSWORD == "neo4jpassword":
            raise RuntimeError(
                f"CRITICAL SECURITY ERROR: Application is running in non-development mode (ENV={settings.ENV}), but the default NEO4J_PASSWORD ('neo4jpassword') is still in use! Startup aborted."
            )
    else:
        if settings.JWT_SECRET == "supersecretkeyforrakshanetdev":
            print("WARNING: Default development JWT_SECRET in use. Do not use this in production environments!")
        if settings.NEO4J_PASSWORD == "neo4jpassword":
            print("WARNING: Default development NEO4J_PASSWORD in use. Do not use this in production environments!")

    # Initialize Postgres DB Schema and seed defaults
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()

    # Run Redis Streams background consumer task
    event_bus = get_event_bus()
    loop = asyncio.get_event_loop()
    loop.create_task(event_bus.start_consumer(SessionLocal))

# Include API gateways
app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(cases.router)
app.include_router(counterfeit.router)
app.include_router(graph.router)
app.include_router(evidence.router)
app.include_router(alerts.router)  # Handles WS /alerts/stream
app.include_router(geo.router)
app.include_router(transactions.router)
app.include_router(admin.router)
app.include_router(speech.router)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "RakshaNet API Gateway"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
