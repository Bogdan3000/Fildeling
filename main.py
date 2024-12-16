from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from templates.routes import router

app = FastAPI()

# Подключаем статику для доступа к загруженным файлам
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")
# Подключаем маршруты из routes.py
app.include_router(router)
