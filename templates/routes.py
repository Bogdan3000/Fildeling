from fastapi import APIRouter, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import shutil
import os

router = APIRouter()

# Папка для хранения загруженных файлов
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def get_upload_page(request: Request):
    # Считываем список файлов в директории
    files = os.listdir(UPLOAD_FOLDER)
    return templates.TemplateResponse("upload.html", {"request": request, "files": files})


@router.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)

    # Сохраняем файл на сервере
    with open(file_location, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"filename": file.filename, "location": file_location}
