from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from templates.routes import router

app = FastAPI()

# Настроим маршруты для статических файлов
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настроим маршрут для .well-known/acme-challenge/
app.mount("/.well-known", StaticFiles(directory="/path/to/acme-challenge"), name="acme-challenge")

# Включаем маршруты из другого файла
app.include_router(router)
