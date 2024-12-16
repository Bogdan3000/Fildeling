from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from templates.routes import router
import os
import subprocess

app = FastAPI()

# Подключаем статику для доступа к загруженным файлам
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем маршруты из routes.py
app.include_router(router)

# Обработка вебхука
@app.post("/webhook")
async def github_webhook(request: Request):
    try:
        # Обработка данных с GitHub
        data = await request.json()

        # Логика обработки данных репозитория
        if data and data["ref"] == 'refs/heads/main':
            os.chdir('/home/ubuntu/Fildeling')

            git_url = f"https://github.com/Bogdan3000/Fildeling.git"
            subprocess.run(['git', 'pull', git_url])

            # Перезапуск службы
            subprocess.run(['systemctl', 'restart', 'bot.service'])

        return {"message": "Received"}
    except Exception as e:
        return {"error": str(e)}
