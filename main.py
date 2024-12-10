from fastapi import FastAPI
from templates.routes import router

app = FastAPI()

app.include_router(router)
