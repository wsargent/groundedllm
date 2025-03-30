import uvicorn
from hayhooks.settings import settings
from fastapi import Request
from hayhooks import create_app

hayhooks = create_app()

@hayhooks.get("/health")
async def health():
    return {"message": "OK!"}

if __name__ == "__main__":
    uvicorn.run("app:hayhooks", host=settings.host, port=settings.port)