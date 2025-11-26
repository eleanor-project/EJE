"""
EJE REST API - FastAPI wrapper for the Ethics Jurisprudence Engine

This provides a production-ready REST API for the EJE decision engine,
suitable for integration with external systems and pilot partner demos.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional
import logging
import os
from datetime import datetime
from contextlib import asynccontextmanager

# Import EJE core components
import sys
sys.path.insert(0, '/app/src')

from ejc.core.decision_engine import EthicalReasoningEngine
from ejc.exceptions import CriticException
from ejc.utils.logging import get_logger

# Configure logging
logger = get_logger("EJC.API")

# Global engine instance (initialized on startup)
engine: Optional[EthicalReasoningEngine] = None


# Pydantic models for API request/response
class CaseInput(BaseModel):
    """Input case for ethical evaluation"""
    text: str = Field(..., description="The scenario or decision to evaluate")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    domain: Optional[str] = Field(default="general", description="Domain (e.g., healthcare, finance, government)")
    priority: Optional[str] = Field(default="normal", description="Priority level: low, normal, high, critical")
    
    @validator('text')
    def text_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Case text cannot be empty')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Should we approve this loan application for a customer with borderline credit?",
                "context": {
                    "customer_age": 45,
                    "requested_amount": 50000,
                    "credit_score": 680
                },
                "domain": "finance",
                "priority": "normal"
            }
        }


class DecisionResponse(BaseModel):
    """Response containing the ethical decision"""
    request_id: str
    timestamp: str
    input: Dict[str, Any]
    final_decision: Dict[str, Any]
    critic_outputs: List[Dict[str, Any]]
    precedent_refs: List[Dict[str, Any]]
    from_cache: Optional[bool] = False


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str
    critics_loaded: int
    cache_enabled: bool
    database_connected: bool


class StatsResponse(BaseModel):
    """System statistics response"""
    cache_stats: Dict[str, Any]
    security_stats: Dict[str, Any]
    uptime_seconds: float


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global engine
    
    # Startup
    logger.info("Starting EJE API server...")
    config_path = os.getenv("EJE_CONFIG_PATH", "/app/config/global.yaml")
    
    try:
        engine = EthicalReasoningEngine(config_path)
        logger.info(f"Decision engine initialized with {len(engine.critics)} critics")
    except Exception as e:
        logger.error(f"Failed to initialize decision engine: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down EJE API server...")
    engine = None


# Create FastAPI application
app = FastAPI(
    title="Ethical Jurisprudence Core (EJC)
    Part of the Mutual Intelligence Framework (MIF) API",
    description="Multi-critic, precedent-driven ethical oversight for AI systems",
    version="1.3.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get engine instance
def get_engine() -> EthicalReasoningEngine:
    """Dependency to get the global engine instance"""
    if engine is None:
        raise HTTPException(status_code=503, detail="Decision engine not initialized")
    return engine


# API Endpoints

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Ethical Jurisprudence Core (EJC)
    Part of the Mutual Intelligence Framework (MIF) API",
        "version": "1.3.0",
        "status": "operational",
        "documentation": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(eng: EthicalReasoningEngine = Depends(get_engine)):
    """
    Health check endpoint for monitoring and load balancers
    """
    try:
        # Check database connectivity
        db_connected = True
        try:
            eng.audit.get_recent_decisions(limit=1)
        except:
            db_connected = False
        
        return HealthResponse(
            status="healthy" if db_connected else "degraded",
            timestamp=datetime.utcnow().isoformat(),
            version="1.3.0",
            critics_loaded=len(eng.critics),
            cache_enabled=eng.cache_enabled,
            database_connected=db_connected
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.post("/evaluate", response_model=DecisionResponse, tags=["Decisions"])
async def evaluate_case(
    case: CaseInput,
    background_tasks: BackgroundTasks,
    eng: EthicalReasoningEngine = Depends(get_engine)
):
    """
    Evaluate a case using all configured critics
    
    This endpoint processes the input case through multiple ethical critics,
    aggregates their opinions, checks for similar precedents, and returns
    a comprehensive decision bundle with full audit trail.
    
    **Process:**
    1. Validate input case
    2. Execute all critics in parallel
    3. Aggregate verdicts using weighted voting
    4. Retrieve similar precedents
    5. Log decision to audit trail
    6. Return complete decision bundle
    """
    try:
        # Convert Pydantic model to dict for engine
        case_dict = case.dict()
        
        # Evaluate using the decision engine
        logger.info(f"Processing evaluation request for domain: {case.domain}")
        result = eng.evaluate(case_dict)
        
        # Return formatted response
        return DecisionResponse(**result)
        
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except CriticException as e:
        logger.error(f"Critic execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Critic error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during evaluation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/stats", response_model=StatsResponse, tags=["Monitoring"])
async def get_statistics(eng: EthicalReasoningEngine = Depends(get_engine)):
    """
    Get system statistics including cache performance and plugin security metrics
    """
    try:
        return StatsResponse(
            cache_stats=eng.get_cache_stats(),
            security_stats=eng.get_security_stats(),
            uptime_seconds=(datetime.utcnow() - datetime.fromisoformat("2024-01-01T00:00:00")).total_seconds()
        )
    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.get("/precedents", tags=["Precedents"])
async def search_precedents(
    query: str,
    limit: int = 5,
    eng: EthicalReasoningEngine = Depends(get_engine)
):
    """
    Search for similar precedents based on a query
    
    Uses semantic similarity to find relevant past decisions
    """
    try:
        # Create a case dict for lookup
        case = {"text": query}
        precedents = eng.pm.lookup(case, limit=limit)
        
        return {
            "query": query,
            "matches": precedents,
            "count": len(precedents)
        }
    except Exception as e:
        logger.error(f"Error searching precedents: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/critics", tags=["Configuration"])
async def list_critics(eng: EthicalReasoningEngine = Depends(get_engine)):
    """
    List all loaded critics with their configurations
    """
    try:
        critics_info = []
        for critic in eng.critics:
            critic_name = critic.__class__.__name__
            critics_info.append({
                "name": critic_name,
                "weight": eng.weights.get(critic_name, 1.0),
                "priority": eng.priorities.get(critic_name),
                "type": type(critic).__name__
            })
        
        return {
            "critics": critics_info,
            "total": len(critics_info)
        }
    except Exception as e:
        logger.error(f"Error listing critics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list critics: {str(e)}")


@app.get("/config", tags=["Configuration"])
async def get_configuration(eng: EthicalReasoningEngine = Depends(get_engine)):
    """
    Get current engine configuration (sanitized - no API keys)
    """
    try:
        config_safe = {k: v for k, v in eng.config.items() if 'key' not in k.lower() and 'secret' not in k.lower()}
        return {
            "configuration": config_safe,
            "critics_loaded": len(eng.critics),
            "cache_enabled": eng.cache_enabled
        }
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
