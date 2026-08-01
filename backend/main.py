from fastapi import FastAPI
from api.routes import router as report_router

app = FastAPI(
    title="AI 8D Report Platform Backend",
    description="Backend API for the 8D Report platform leveraging LLMs.",
    version="1.0.0"
)

# Include the report router with a prefix
app.include_router(report_router, prefix="/api/v1/report", tags=["report"])

@app.get("/")
async def root():
    return {"message": "Welcome to AI 8D Report Platform API"}

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
