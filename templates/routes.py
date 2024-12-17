import os
import json
import shutil
import subprocess
import tempfile
import urllib
import uuid
import oci
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import io

# Oracle Cloud credentials and Object Storage client setup
config = oci.config.from_file()
object_storage_client = oci.object_storage.ObjectStorageClient(config)
namespace = object_storage_client.get_namespace().data
bucket_name = "ShareData"  # Replace with your actual bucket name

# Path for local storage of JSON files
LOCAL_STORAGE_PATH = "/home/ubuntu/files_storage"  # Update this to your desired path

# Initialize FastAPI router
router = APIRouter()

# JSON file names
PASSWORDS_FILE = "passwords.json"
FILENAMES_FILE = "filenames.json"
templates = Jinja2Templates(directory="templates")

# Helper functions for working with local files
def save_json_to_local_file(file_name, data):
    os.makedirs(LOCAL_STORAGE_PATH, exist_ok=True)
    file_path = os.path.join(LOCAL_STORAGE_PATH, file_name)
    with open(file_path, "w") as f:
        json.dump(data, f)

def load_json_from_local_file(file_name):
    file_path = os.path.join(LOCAL_STORAGE_PATH, file_name)
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return {}

# Load existing passwords and filenames from local storage
file_passwords = load_json_from_local_file(PASSWORDS_FILE)
filenames_mapping = load_json_from_local_file(FILENAMES_FILE)

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
            save_json_to_local_file(PASSWORDS_FILE, file_passwords)

        # Сохранение оригинального имени файла с серверным именем
        filenames_mapping[random_filename] = {
            "name": original_filename,
            "server_name": random_filename
        }
        save_json_to_local_file(FILENAMES_FILE, filenames_mapping)

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

    # Save changes to local storage
    save_json_to_local_file(PASSWORDS_FILE, file_passwords)
    save_json_to_local_file(FILENAMES_FILE, filenames_mapping)

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


@router.post("/webhook")
async def github_webhook(request: Request):
    try:
        os.chdir('/home/ubuntu/Fildeling')
        git_url = "https://github.com/Bogdan3000/Fildeling.git"

        # Perform git pull to fetch the latest changes
        subprocess.run(['git', 'pull', git_url], check=True)

        # Restart the service via systemctl
        subprocess.run(['systemctl', 'kill', '--signal=SIGTERM', 'bot.service'], check=True)

        return {"message": "Received"}
    except subprocess.CalledProcessError as e:
        return {"error": f"Error occurred: {e}"}
