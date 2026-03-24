"""
Multi-Backend Storage Manager

Supports three storage backends:
1. LOCAL: Filesystem storage (for development)
2. HUGGINGFACE: HuggingFace Spaces temporary storage (auto-detected)
3. ZENODO: Zenodo.org repository (production-grade)

[PER-USER STORAGE]: All backends maintain per-user isolation
[ASTRONOMY PROCESSING PLACEHOLDER]: Files accessible by processing pipeline
"""

import os
import json
import requests
import tempfile
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile, HTTPException
from app.config import settings

# ============== CONFIGURATION ==============

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
ALLOWED_EXTENSIONS = {'.fits', '.fit', '.fts'}

# Detect storage backend
STORAGE_BACKEND = settings.STORAGE_BACKEND.lower()
print(f"[STORAGE] Initialized with backend: {STORAGE_BACKEND.upper()}")

# HuggingFace auto-detection
GRADIO_TEMP_DIR = os.getenv("GRADIO_TEMP_DIR", None)
if GRADIO_TEMP_DIR:
    print(f"[STORAGE] HuggingFace Spaces detected: {GRADIO_TEMP_DIR}")
    STORAGE_BACKEND = "huggingface"

# Zenodo configuration
ZENODO_BASE_URL = "https://sandbox.zenodo.org/api" if settings.ZENODO_SANDBOX_MODE else "https://zenodo.org/api"
ZENODO_TOKEN = settings.ZENODO_API_TOKEN

# ============== LOCAL STORAGE ==============

def _local_get_user_storage_path(user_id: str) -> Path:
    """[PER-USER STORAGE]: Get user's local storage directory"""
    user_path = Path(settings.LOCAL_STORAGE_PATH) / user_id
    user_path.mkdir(parents=True, exist_ok=True)
    return user_path


async def _local_upload_fits_file(user_id: str, file: UploadFile) -> dict:
    """[PER-USER STORAGE]: Upload FITS to local filesystem"""
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    
    content = await file.read()
    file_size = len(content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Max: {MAX_FILE_SIZE / (1024*1024):.0f} MB")
    
    try:
        user_storage = _local_get_user_storage_path(user_id)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = user_storage / safe_filename
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return {
            "filename": file.filename,
            "stored_as": safe_filename,
            "size": file_size,
            "path": str(file_path),
            "public_url": f"/api/files/download/{safe_filename}",
            "uploaded_at": datetime.utcnow().isoformat(),
            "backend": "local"
        }
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")


async def _local_list_user_files(user_id: str) -> list:
    """[PER-USER STORAGE]: List user's local files"""
    user_storage = _local_get_user_storage_path(user_id)
    files = []
    
    if user_storage.exists():
        for file_path in user_storage.glob("*"):
            if file_path.is_file():
                files.append({
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
                })
    return files


# ============== HUGGINGFACE SPACES STORAGE ==============

def _hf_get_user_storage_path(user_id: str) -> Path:
    """[PER-USER STORAGE]: Get user's HF Spaces temporary storage directory"""
    user_path = Path(GRADIO_TEMP_DIR) / "astrosense_uploads" / user_id
    user_path.mkdir(parents=True, exist_ok=True)
    return user_path


async def _hf_upload_fits_file(user_id: str, file: UploadFile) -> dict:
    """[PER-USER STORAGE]: Upload FITS to HuggingFace Spaces temp storage"""
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    
    content = await file.read()
    file_size = len(content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Max: {MAX_FILE_SIZE / (1024*1024):.0f} MB")
    
    try:
        user_storage = _hf_get_user_storage_path(user_id)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = user_storage / safe_filename
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return {
            "filename": file.filename,
            "stored_as": safe_filename,
            "size": file_size,
            "path": str(file_path),
            "public_url": f"/api/files/download/{safe_filename}",
            "uploaded_at": datetime.utcnow().isoformat(),
            "backend": "huggingface"
        }
    except Exception as e:
        raise HTTPException(500, f"HuggingFace upload failed: {str(e)}")


async def _hf_list_user_files(user_id: str) -> list:
    """[PER-USER STORAGE]: List user's HF Spaces files"""
    user_storage = _hf_get_user_storage_path(user_id)
    files = []
    
    if user_storage.exists():
        for file_path in user_storage.glob("*"):
            if file_path.is_file():
                files.append({
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
                })
    return files


# ============== ZENODO STORAGE ==============

async def _zenodo_upload_fits_file(user_id: str, file: UploadFile) -> dict:
    """
    [PER-USER STORAGE]: Upload FITS to Zenodo.org
    [ASTRONOMY PROCESSING PLACEHOLDER]: Zenodo stores files with metadata for processing
    
    Returns Zenodo record ID and file URL for public access
    """
    if not ZENODO_TOKEN:
        raise HTTPException(500, "Zenodo API token not configured")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    
    content = await file.read()
    file_size = len(content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Max: {MAX_FILE_SIZE / (1024*1024):.0f} MB")
    
    try:
        headers = {"Authorization": f"Bearer {ZENODO_TOKEN}"}
        
        # Create deposition (upload container)
        metadata = {
            "metadata": {
                "title": f"AstroSense FITS - {file.filename}",
                "description": f"[PER-USER STORAGE] FITS file uploaded by user {user_id} via AstroSense",
                "creators": [{"name": "AstroSense User", "affiliation": "AstroSense Platform"}],
                "upload_type": "dataset",
                "keywords": ["astronomy", "FITS", "exoplanet", "spectroscopy"]
            }
        }
        
        # Create new deposition
        response = requests.post(
            f"{ZENODO_BASE_URL}/deposit/depositions",
            headers=headers,
            json=metadata
        )
        
        print(f"[ZENODO DEBUG] Deposition creation - Status: {response.status_code}, Response: {response.text[:500]}")
        
        if response.status_code not in [201, 200]:
            raise Exception(f"Zenodo deposition creation failed: Status {response.status_code} - {response.text}")
        
        try:
            deposition_id = response.json()["id"]
            print(f"[ZENODO DEBUG] Created deposition: {deposition_id}")
        except Exception as e:
            raise Exception(f"Could not parse deposition response: {response.text} - Error: {str(e)}")
        
        # Upload file to deposition
        files_dict = {'file': (file.filename, content)}
        upload_response = requests.post(
            f"{ZENODO_BASE_URL}/deposit/depositions/{deposition_id}/files",
            headers=headers,
            files=files_dict
        )
        
        print(f"[ZENODO DEBUG] File upload - Status: {upload_response.status_code}, Response: {upload_response.text[:500]}")
        
        if upload_response.status_code not in [201, 200]:
            raise Exception(f"Zenodo file upload failed: Status {upload_response.status_code} - {upload_response.text}")
        
        try:
            upload_json = upload_response.json()
            # Single file object (not array) - Zenodo returns direct file object
            file_id = upload_json.get("id")
            file_zenodo_url = upload_json.get("links", {}).get("self")
            print(f"[ZENODO DEBUG] Uploaded file: {file_id}")
        except Exception as e:
            raise Exception(f"Could not parse file upload response: {upload_response.text} - Error: {str(e)}")
        
        # Publish the deposition
        publish_response = requests.post(
            f"{ZENODO_BASE_URL}/deposit/depositions/{deposition_id}/actions/publish",
            headers=headers
        )
        
        print(f"[ZENODO DEBUG] Publish - Status: {publish_response.status_code}, Response: {publish_response.text[:500]}")
        
        if publish_response.status_code not in [202, 201, 200]:
            raise Exception(f"Zenodo publish failed: Status {publish_response.status_code} - {publish_response.text}")
        
        # [ASTRONOMY PROCESSING PLACEHOLDER]: File now published and accessible
        try:
            publish_json = publish_response.json()
            record_id = publish_json.get("record_id") or publish_json.get("id")
            print(f"[ZENODO DEBUG] Publish response keys: {publish_json.keys()}")
            print(f"[ZENODO DEBUG] Extracted record_id: {record_id}")
            
            if not record_id:
                # Fallback: extract from deposition if publish response doesn't have record_id
                print(f"[ZENODO DEBUG] No record_id in publish response, checking deposition...")
                deposition_check = requests.get(
                    f"{ZENODO_BASE_URL}/deposit/depositions/{deposition_id}",
                    headers=headers
                )
                deposition_data = deposition_check.json()
                record_id = deposition_data.get("record_id") or deposition_id
                print(f"[ZENODO DEBUG] Got record_id from deposition check: {record_id}")
        except Exception as e:
            # If we can't get record_id, use deposition_id as fallback
            record_id = deposition_id
            print(f"[ZENODO WARNING] Could not extract record_id: {str(e)}. Using deposition_id: {deposition_id}")
        
        zenodo_record_url = f"https://zenodo.org/record/{record_id}" if not settings.ZENODO_SANDBOX_MODE else f"https://sandbox.zenodo.org/record/{record_id}"
        
        return {
            "filename": file.filename,
            "stored_as": str(record_id),
            "size": file_size,
            "path": file_zenodo_url,
            "public_url": zenodo_record_url,
            "uploaded_at": datetime.utcnow().isoformat(),
            "backend": "zenodo",
            "zenodo_record_id": record_id,
            "metadata": {"user_id": user_id}
        }
    
    except requests.exceptions.RequestException as e:
        print(f"[ZENODO ERROR] Connection failed: {str(e)}")
        raise HTTPException(500, f"Zenodo connection failed: {str(e)}")
    except Exception as e:
        print(f"[ZENODO ERROR] Upload failed: {str(e)}")
        raise HTTPException(500, f"Zenodo upload failed: {str(e)}")


# ============== ROUTER FUNCTIONS ==============

async def upload_fits_file(user_id: str, file: UploadFile) -> dict:
    """
    [PER-USER STORAGE]: Route upload to configured backend
    [ASTRONOMY PROCESSING PLACEHOLDER]: File accessible at returned path
    """
    if STORAGE_BACKEND == "zenodo":
        return await _zenodo_upload_fits_file(user_id, file)
    elif STORAGE_BACKEND == "huggingface":
        return await _hf_upload_fits_file(user_id, file)
    else:  # default to local
        return await _local_upload_fits_file(user_id, file)


async def list_user_files(user_id: str) -> list:
    """[PER-USER STORAGE]: List user's files from configured backend"""
    if STORAGE_BACKEND == "huggingface":
        return await _hf_list_user_files(user_id)
    else:  # local is default, Zenodo doesn't list files
        return await _local_list_user_files(user_id)


async def delete_user_file(user_id: str, filename: str) -> dict:
    """[PER-USER STORAGE]: Delete file from storage"""
    if STORAGE_BACKEND == "zenodo":
        raise HTTPException(501, "Zenodo deletion not supported - files are archived")
    
    if STORAGE_BACKEND == "huggingface":
        user_storage = _hf_get_user_storage_path(user_id)
    else:
        user_storage = _local_get_user_storage_path(user_id)
    
    file_path = user_storage / filename
    
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    
    if not str(file_path.parent) == str(user_storage):
        raise HTTPException(403, "Access denied")
    
    try:
        file_path.unlink()
        return {"status": "deleted", "filename": filename}
    except Exception as e:
        raise HTTPException(500, f"Deletion failed: {str(e)}")


async def get_file_for_processing(user_id: str, filename: str) -> str:
    """
    [ASTRONOMY PROCESSING PLACEHOLDER]: Get file path/URL for astronomy processing
    For local/HF: returns filesystem path
    For Zenodo: returns download URL
    """
    if STORAGE_BACKEND == "zenodo":
        # Return Zenodo record URL for processing
        return f"https://zenodo.org/api/records/{filename}/files" if not settings.ZENODO_SANDBOX_MODE else f"https://sandbox.zenodo.org/api/records/{filename}/files"
    elif STORAGE_BACKEND == "huggingface":
        user_storage = _hf_get_user_storage_path(user_id)
    else:
        user_storage = _local_get_user_storage_path(user_id)
    
    file_path = user_storage / filename
    
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    
    return str(file_path)

