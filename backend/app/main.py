from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.process import router as process_router
from app.routes.device_actions import router as device_router
from app.services.rag_service import init_rag

app = FastAPI(title="Neura AI Agent", version="2.0.0", description="Smart AI Assistant with Phone Control")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(process_router, prefix="/api/v1", tags=["process"])
app.include_router(device_router, prefix="/api/v1", tags=["device_actions"])


@app.on_event("startup")
async def startup_event():
    init_rag()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Neura"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
