from fastapi import FastAPI
from templates.routes import router

app = FastAPI()

# Подключение маршрутов из templates/routes.py
app.include_router(router)
