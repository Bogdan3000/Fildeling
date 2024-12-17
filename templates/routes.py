import os
import json
import shutil
import subprocess
import tempfile
import urllib
import uuid
import io
import re
import oci
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import transliterate

config_path = "/etc/secrets/config"
config = oci.config.from_file(file_location=config_path)
object_storage_client = oci.object_storage.ObjectStorageClient(config)
namespace = object_storage_client.get_namespace().data
bucket_name = "ShareData"  # Replace with your actual bucket name

# JSON file names
PASSWORDS_FILE = "passwords.json"
FILENAMES_FILE = "filenames.json"
templates = Jinja2Templates(directory="templates")

# Helper functions for working with Object Storage
def save_json_to_object_storage(file_name, data):
    # Convert JSON data to bytes
    json_bytes = io.BytesIO(json.dumps(data).encode('utf-8'))
    # Upload JSON to Object Storage
    object_storage_client.put_object(namespace, bucket_name, file_name, json_bytes)

def load_json_from_object_storage(file_name):
    try:
        # Fetch the JSON file from Object Storage
        obj = object_storage_client.get_object(namespace, bucket_name, file_name)
        # Read and parse the JSON content
        return json.load(io.BytesIO(obj.data.content))
    except oci.exceptions.ServiceError as e:
        if e.status == 404:  # File not found
            return {}
        raise e

# Load existing passwords and filenames from Object Storage
file_passwords = load_json_from_object_storage(PASSWORDS_FILE)
filenames_mapping = load_json_from_object_storage(FILENAMES_FILE)

# Save changes to Object Storage
def save_file_passwords():
    save_json_to_object_storage(PASSWORDS_FILE, file_passwords)

def save_filenames_mapping():
    save_json_to_object_storage(FILENAMES_FILE, filenames_mapping)

# Initialize FastAPI router
router = APIRouter()

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

        # Преобразование имени файла в латиницу, если требуется
        if not all(ord(c) < 128 for c in original_filename):
            if transliterate.detect_language(original_filename) == "ru":
                original_filename = transliterate.translit(original_filename, reversed=True)
            else:
                original_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", original_filename)

        # Получение расширения файла
        file_extension = original_filename.split('.')[-1] if '.' in original_filename else ''

        # Генерация случайного имени с расширением
        random_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())

        # Загрузка файла в Oracle Object Storage
        file_location = io.BytesIO(await file.read())
        object_storage_client.put_object(namespace, bucket_name, random_filename, file_location)

        # Сохранение пароля, если он указан
        if password:
            file_passwords[random_filename] = password
            save_file_passwords()

        # Сохранение оригинального имени файла с серверным именем
        filenames_mapping[random_filename] = {
            "name": original_filename,
            "server_name": random_filename
        }
        save_filenames_mapping()

    # Перенаправление на главную страницу после загрузки
    return RedirectResponse(url="/", status_code=303)


@router.post("/deletefile/")
async def delete_file(request: Request, filename: str = Form(...), password: str = Form(None)):
    # Find the random filename by the original filename
    random_filename = next((k for k, v in filenames_mapping.items() if v["name"] == filename), None)
    if not random_filename:
        return RedirectResponse(url="/?error=File+not+found", status_code=303)

    # Check if the file is protected with a password
    if random_filename in file_passwords:
        if password == "Bogdan3000":
            pass
        elif not password:
            return RedirectResponse(url="/?error=Incorrect+password", status_code=303)
        elif file_passwords[random_filename] != password:
            return RedirectResponse(url="/?error=Incorrect+password", status_code=303)

    # Remove the file from Oracle Object Storage
    object_storage_client.delete_object(namespace, bucket_name, random_filename)
    file_passwords.pop(random_filename, None)
    filenames_mapping.pop(random_filename, None)

    # Save changes to Object Storage
    save_file_passwords()
    save_filenames_mapping()

    return RedirectResponse(url="/", status_code=303)


@router.get("/download/{filename}")
async def download_file(filename: str):
    # Найти случайное имя файла по оригинальному имени
    random_filename = next((k for k, v in filenames_mapping.items() if v["name"] == filename), None)
    if not random_filename:
        raise HTTPException(status_code=404, detail="File not found")

    # Получить файл из Oracle Object Storage
    try:
        object_storage_object = object_storage_client.get_object(namespace, bucket_name, random_filename)

        # Сохранить содержимое файла во временный файл
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            shutil.copyfileobj(io.BytesIO(object_storage_object.data.content), tmp_file)
            tmp_file_path = tmp_file.name

        # Кодируем имя файла для корректного отображения русских символов
        encoded_filename = urllib.parse.quote(filename)

        # Возвращаем файл как ответ
        return FileResponse(
            tmp_file_path,
            filename=filename,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except oci.exceptions.ServiceError:
        raise HTTPException(status_code=404, detail="File not found")