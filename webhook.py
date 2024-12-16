from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import uvicorn
import subprocess

app = FastAPI()

@app.post("/webhook")
async def github_webhook(request: Request):
    try:
        # Обработка данных с GitHub
        data = await request.json()

        # Логика обработки данных репозитория
        if data and data["ref"] == 'refs/heads/main':
            os.chdir('/home/ubuntu/fildeling')

            git_url = f"https://github.com/Bogdan3000/Fildeling.git"
            subprocess.run(['git', 'pull', git_url])

            # Перезапуск службы
            subprocess.run(['systemctl', 'restart', 'bot.service'])

        return JSONResponse(content={"message": "Received"}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=2345)
