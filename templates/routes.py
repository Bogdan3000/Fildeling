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
            "name": filenames_mapping.get(f, f),
            "is_protected": f in file_passwords
        }
        for f in os.listdir(UPLOAD_FOLDER)
    ]
    return templates.TemplateResponse("upload.html", {"request": request, "files": files, "error": error})

@router.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...), password: str = Form(None)):
    original_filename = file.filename
    random_filename = str(uuid.uuid4())
    file_location = os.path.join(UPLOAD_FOLDER, random_filename)

    with open(file_location, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Store the password if provided
    if password:
        file_passwords[random_filename] = password
        with open(PASSWORDS_FILE, "w") as f:
            json.dump(file_passwords, f)

    # Store the original filename mapping
    filenames_mapping[random_filename] = original_filename
    with open(FILENAMES_FILE, "w") as f:
        json.dump(filenames_mapping, f)

    # Redirect to the main page after upload
    return RedirectResponse(url="/", status_code=303)

@router.post("/deletefile/")
async def delete_file(request: Request, filename: str = Form(...), password: str = Form(None)):
    # Find the random filename from the original filename
    random_filename = next((k for k, v in filenames_mapping.items() if v == filename), None)
    if not random_filename:
        raise HTTPException(status_code=404, detail="File not found")

    file_location = os.path.join(UPLOAD_FOLDER, random_filename)

    # Check password if it exists
    if random_filename in file_passwords:
        if file_passwords[random_filename] != password:
            error_message = "Incorrect password"
            files = [filenames_mapping.get(f, f) for f in os.listdir(UPLOAD_FOLDER)]
            return templates.TemplateResponse("upload.html", {"request": request, "files": files, "error": error_message})

    # Delete the file
    os.remove(file_location)
    file_passwords.pop(random_filename, None)
    filenames_mapping.pop(random_filename, None)
    with open(PASSWORDS_FILE, "w") as f:
        json.dump(file_passwords, f)
    with open(FILENAMES_FILE, "w") as f:
        json.dump(filenames_mapping, f)

    return RedirectResponse(url="/", status_code=303)

@router.get("/download/{filename}")
async def download_file(filename: str):
    # Find the random filename from the original filename
    random_filename = next((k for k, v in filenames_mapping.items() if v == filename), None)
    if not random_filename:
        raise HTTPException(status_code=404, detail="File not found")

    file_location = os.path.join(UPLOAD_FOLDER, random_filename)

    if not os.path.exists(file_location):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_location, filename=filename)