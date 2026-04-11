from fastapi import FastAPI

app = FastAPI(title="Personal TARS")


@app.get("/health")
async def health():
    return {"status": "ok"}
