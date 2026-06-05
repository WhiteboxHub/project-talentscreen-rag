"""File handling and validation utilities for TalentScreen."""

import os
import shutil
import uuid
from fastapi import UploadFile

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt', '.md'}

def is_allowed_extension(filename: str) -> bool:
    """Check if the file extension is supported."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def save_upload_file(upload_file: UploadFile, destination_directory: str) -> str:
    """Save an uploaded file to the local staging directory and return its path."""
    os.makedirs(destination_directory, exist_ok=True)
    file_id = str(uuid.uuid4())
    
    # Clean filename to avoid directory traversal
    safe_filename = os.path.basename(upload_file.filename)
    saved_filename = f"{file_id}_{safe_filename}"
    destination_path = os.path.join(destination_directory, saved_filename)
    
    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
        
    return destination_path
