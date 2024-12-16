import subprocess

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import shutil
import os
import json
import uuid

router = APIRouter()

UPLOAD_FOLDER = "uploads"
PASSWORDS_FILE = "passwords.json"
FILENAMES_FILE = "filenames.json"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
templates = Jinja2Templates(directory="templates")

# Load existing passwords and filenames
if os.path.exists(PASSWORDS_FILE):
    with open(PASSWORDS_FILE, "r") as f:
        file_passwords = json.load(f)
else:
    file_passwords = {}

if os.path.exists(FILENAMES_FILE):
    with open(FILENAMES_FILE, "r") as f:
        filenames_mapping = json.load(f)
else:
    filenames_mapping = {}

@router.get("/", response_class=HTMLResponse)
async def get_upload_page(request: Request, error: str = None):
    files = [
        {
            "name": file_info["name"],
            "server_name": file_info["server_name"],
            "is_protected": f in file_passwords
        }
        for f, file_info in filenames_mapping.items()
    ]
    print(f"Files: {files}")  # Логируем файлы
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "files": files,
        "filenames_mapping": filenames_mapping,
        "error": error
    })

@router.post("/uploadfile/")
async def upload_file(files: list[UploadFile] = File(...), password: str = Form(None)):
    for file in files:
        original_filename = file.filename
        random_filename = str(uuid.uuid4())  # случайное имя файла на сервере
        file_location = os.path.join(UPLOAD_FOLDER, random_filename)

        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Store the password if provided
        if password:
            file_passwords[random_filename] = password
            with open(PASSWORDS_FILE, "w") as f:
                json.dump(file_passwords, f)

        # Store the original filename mapping along with the server name
        filenames_mapping[random_filename] = {
            "name": original_filename,
            "server_name": random_filename
        }
        with open(FILENAMES_FILE, "w") as f:
            json.dump(filenames_mapping, f)

    # Redirect to the main page after upload
    return RedirectResponse(url="/", status_code=303)

@router.post("/deletefile/")
async def delete_file(request: Request, filename: str = Form(...), password: str = Form(None)):
    # Find the random filename by the original filename
    random_filename = next((k for k, v in filenames_mapping.items() if v["name"] == filename), None)
    if not random_filename:
        return RedirectResponse(url="/?error=File+not+found", status_code=303)

    file_location = os.path.join(UPLOAD_FOLDER, random_filename)

    # Check if the file is protected with a password
    if random_filename in file_passwords:
        if not password:
            return templates.TemplateResponse("upload.html", {
                "request": request,
                "error": "Password is required to delete this file",
                "delete_filename": filename
            })

        if file_passwords[random_filename] != password:
            return RedirectResponse(url="/?error=Incorrect+password", status_code=303)

    # Remove the file if password is correct or not required
    os.remove(file_location)
    file_passwords.pop(random_filename, None)
    filenames_mapping.pop(random_filename, None)

    # Save changes to the files
    with open(PASSWORDS_FILE, "w") as f:
        json.dump(file_passwords, f)
    with open(FILENAMES_FILE, "w") as f:
        json.dump(filenames_mapping, f)

    return RedirectResponse(url="/", status_code=303)

@router.get("/download/{filename}")
async def download_file(filename: str):
    # Find the random filename by the original filename
    random_filename = next((k for k, v in filenames_mapping.items() if v["name"] == filename), None)
    if not random_filename:
        raise HTTPException(status_code=404, detail="File not found")

    file_location = os.path.join(UPLOAD_FOLDER, random_filename)

    if not os.path.exists(file_location):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_location, filename=filename)

@router.post("/webhook")
async def github_webhook(request: Request):
    try:
        # Обработка данных с GitHub
        data = await request.json()

        # Логика обработки данных репозитория
        if data and data["ref"] == 'refs/heads/main':
            os.chdir('/home/ubuntu/Fildeling')

            git_url = f"https://github.com/Bogdan3000/Fildeling.git"
            a = subprocess.run(['git', 'pull', git_url])
            print(a.stdout)
            # Перезапуск службы
            a = subprocess.run(['systemctl', 'restart', 'bot.service'])
            print(a.stdout)

        return {"message": "Received"}
    except Exception as e:
        return {"error": str(e)}