from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from templates.routes import router

app = FastAPI()

# Настроим маршруты для статических файлов
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")


# Включаем маршруты из другого файла
app.include_router(router)
