# AstroSense Migration Guide: Firebase → HuggingFace Spaces Session Storage

## What Changed

Your AstroSense project has been migrated from Firebase Cloud Storage to HuggingFace Spaces session storage. This keeps the same authentication and UI while simplifying the backend infrastructure.

---

## ✅ What Stayed the Same

- ✅ **JWT Authentication** - User registration, login, token-based access control
- ✅ **Frontend UI** - Space-themed design, responsiveness, animations
- ✅ **File Upload Workflow** - FITS file upload with validation
- ✅ **API Endpoints** - Same REST endpoints, same request/response formats
- ✅ **Per-User Isolation** - Each user's files stored separately

---

## 🔄 Key Changes

### Backend Storage

| Aspect | Before (Firebase) | After (Session Storage) |
|--------|-------------------|------------------------|
| Storage Type | Google Cloud Storage (persistent) | Local filesystem (temporary) |
| User Files Location | `astrosense-uploads/{user_id}/{filename}` | `/tmp/astrosense_uploads/{user_id}/{filename}` |
| Persistence | Persistent across sessions | Cleared when session ends |
| Cost | Pay-as-you-go | Free (part of HuggingFace Spaces) |
| Setup | Requires Firebase credentials | No additional setup |
| Best For | Production deployment | Development/prototyping |

### Dependencies Removed

```diff
- firebase-admin==6.2.0  # No longer needed
```

### Configuration Removed

```diff
- FIREBASE_API_KEY
- FIREBASE_PROJECT_ID
- FIREBASE_STORAGE_BUCKET
- FIREBASE_CREDENTIALS_PATH
- firebase_credentials.json
```

---

## 🎯 New Architecture

```
User Browser (http://localhost:5173)
    ↓ HTTP with JWT Token
FastAPI Backend (http://localhost:8000)
    ├─ [JWT AUTHENTICATION]
    │  ├─ Register/Login endpoints
    │  └─ Token validation on all protected routes
    │
    └─ [PER-USER STORAGE]
       ├─ /tmp/astrosense_uploads/
       │  ├─ {user_id_1}/
       │  │  ├─ 20240324_143022_file1.fits
       │  │  └─ 20240324_152015_file2.fits
       │  └─ {user_id_2}/
       │     └─ 20240324_160030_file3.fits
       │
       [ASTRONOMY PROCESSING PLACEHOLDER]
       └─ Processing pipeline accesses files from here
```

---

## 📝 Code Comments Reference

Comments have been added throughout the code to indicate:

### `[JWT AUTHENTICATION]`
**Location:** Every auth-related function and endpoint  
**Indicates:** User registration, login, token validation, password hashing  
**Examples:**
- `app/auth.py` - All JWT functions
- `app/main.py` - All auth endpoints and `get_current_user()` dependency
- `app/config.py` - JWT configuration settings

### `[PER-USER STORAGE]`
**Location:** Every file storage operation  
**Indicates:** User directory isolation, per-user file operations  
**Examples:**
- `app/storage.py` - `get_user_storage_path()`, `upload_fits_file()`, `list_user_files()`, `delete_user_file()`
- `app/main.py` - File upload, list, delete routes (all protected by JWT)

### `[ASTRONOMY PROCESSING PLACEHOLDER]`
**Location:** Where astronomy analysis should be added  
**Indicates:** Points where you'll plug in FITS processing logic  
**Examples:**
- `app/storage.py` - `get_file_for_processing()` function
- `app/main.py` - File upload/list route documentation
- Comments indicate "processing pipeline will use this" patterns

---

## 🚀 Running Locally (No Changes to Commands)

Backend setup is now **simpler** - no Firebase config needed:

```bash
cd server
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install -r requirements.txt  # Firebase-admin removed
python -m uvicorn app.main:app --reload
```

Frontend still runs the same:
```bash
cd client
npm install
npm run dev
```

---

## 📁 File Structure (What Changed)

```
server/
├── app/
│   ├── main.py                      ← Updated with comments
│   ├── auth.py                      ← Added JWT comments
│   ├── storage.py                   ← COMPLETE REWRITE (Firebase → Session)
│   ├── config.py                    ← Removed Firebase config
│   ├── firebase_config.py           ← Deprecated (kept for reference)
│   └── models.py                    ← Unchanged
├── requirements.txt                 ← firebase-admin REMOVED
├── .env.example                     ← Firebase config REMOVED
└── README.md                        ← Updated with session storage info
```

---

## 🔐 JWT Authentication (Unchanged)

All authentication still works exactly the same:

1. **Register:**
   ```
   POST /api/auth/register
   {"email": "user@example.com", "password": "pass", "username": "user"}
   ↓
   Returns: {"access_token": "eyJ...", "token_type": "bearer", "user_id": "uuid"}
   ```

2. **Login:**
   ```
   POST /api/auth/login
   {"email": "user@example.com", "password": "pass"}
   ↓
   Returns: {"access_token": "eyJ...", "token_type": "bearer", "user_id": "uuid"}
   ```

3. **Protected Requests:**
   ```
   POST /api/upload/fits
   Authorization: Bearer eyJ...
   [file data]
   ```

---

## 💾 Per-User Storage (How It Works)

### Directory Structure
```
/tmp/astrosense_uploads/           # Base (temporary)
├── 550e8400-e29b-41d4-a716.../  # User 1
│   ├── 20240324_143022_file1.fits
│   └── 20240324_152015_file2.fits
└── 6ba7b810-9dad-11d1-80b4.../  # User 2
    └── 20240324_160030_file3.fits
```

### Key Functions in `storage.py`

```python
def get_user_storage_path(user_id: str) -> Path:
    """Returns /tmp/astrosense_uploads/{user_id}/ - creates if needed"""

async def upload_fits_file(user_id: str, file) -> dict:
    """Saves file to user's directory, validates FITS format & size"""

async def list_user_files(user_id: str) -> list:
    """Lists only files in user's isolated directory"""

async def delete_user_file(user_id: str, filename: str) -> dict:
    """Deletes file from user's directory with path traversal protection"""

async def get_file_for_processing(user_id: str, filename: str) -> str:
    """Returns file path for astronomy processing pipeline [PLACEHOLDER]"""
```

---

## 🔬 [ASTRONOMY PROCESSING PLACEHOLDER] - Ready for Your Logic

Files are stored and ready for your processing pipeline. To add astronomy analysis:

### Option 1: Add a new endpoint in `app/main.py`

```python
@app.post("/api/process/fits/{filename}")
async def process_fits_file(
    filename: str,
    user_id: str = Depends(get_current_user)
):
    """[ASTRONOMY PROCESSING PLACEHOLDER]: Process FITS file"""
    # Get file path from storage
    from app.storage import get_file_for_processing
    file_path = await get_file_for_processing(user_id, filename)
    
    # TODO: Call your astronomy processing pipeline
    # result = await process_fits_with_cnn(file_path)
    
    return {"status": "processing", "file": filename}
```

### Option 2: Use in Colab

```python
# In your Colab notebook:
import requests

# Upload file through AstroSense
response = requests.post(
    "http://localhost:8000/api/upload/fits",
    headers={"Authorization": f"Bearer {token}"},
    files={"file": open("data.fits", "rb")}
)

# File is now at:
# /tmp/astrosense_uploads/{user_id}/{filename}

# Process it with your CNN:
# fits_path = "/tmp/astrosense_uploads/{user_id}/20240324_143022_data.fits"
# result = your_astronomy_pipeline(fits_path)
```

### Option 3: Batch processing endpoint

```python
@app.get("/api/process/batch")
async def batch_process(user_id: str = Depends(get_current_user)):
    """[ASTRONOMY PROCESSING PLACEHOLDER]: Process all user's files"""
    from app.storage import list_user_files, get_file_for_processing
    
    files = await list_user_files(user_id)
    results = []
    
    for file_info in files:
        file_path = await get_file_for_processing(user_id, file_info["name"])
        # TODO: Process each file
        # result = await process_fits_with_cnn(file_path)
        results.append({"file": file_info["name"], "status": "processed"})
    
    return {"processed": results}
```

---

## ⚡ Performance Notes

### Session Storage Benefits
- **Instant access** - No cloud latency
- **No costs** - Local temporary storage
- **Simple setup** - No auth configuration
- **Perfect for MVP** - Ideal for prototyping

### Session Storage Limitations
- **Temporary** - Cleared when session ends
- **Local only** - No multi-instance support
- **Size limits** - Depends on HuggingFace Spaces storage

### When to Upgrade
Move back to persistent storage (Firebase/GCS/S3) when:
- Users need files to persist across sessions
- You have 100+ concurrent users
- You want automatic backups
- You need geographic distribution

---

## 🔍 Testing the Changes

### Test JWT Auth (unchanged)
```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'

# Response: {"access_token":"eyJ...", "user_id":"uuid..."}

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'
```

### Test Per-User Storage
```bash
# Upload (replace TOKEN with actual token)
curl -X POST http://localhost:8000/api/upload/fits \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@test.fits"

# Response: {"filename":"test.fits", "path":"/tmp/astrosense_uploads/..."}

# List files
curl -X GET http://localhost:8000/api/files/list \
  -H "Authorization: Bearer TOKEN"

# Response: {"files": [...], "count": 1}
```

---

## 📚 Documentation Files

### Before You Start
- [README.md](../README.md) - Full project overview
- [SETUP.md](../SETUP.md) - Setup instructions

### During Development
- [INDEX.md](../INDEX.md) - Quick navigation
- [QUICKSTART.md](../QUICKSTART.md) - Quick reference
- [server/README.md](./README.md) - Backend API docs

### For This Migration
- This file (MIGRATION.md) - What changed and why
- [IMPLEMENTATION.md](../IMPLEMENTATION.md) - Architecture deep dive

---

## ✅ Verification Checklist

After migration, verify:

- [ ] Backend starts without Firebase errors
  ```bash
  cd server && python -m uvicorn app.main:app --reload
  ```

- [ ] API docs load
  ```bash
  Visit: http://localhost:8000/docs
  ```

- [ ] Registration works
  ```bash
  Register at: http://localhost:5173/register
  ```

- [ ] File upload works
  ```bash
  Upload FITS file on dashboard
  ```

- [ ] Files appear in temp storage
  ```bash
  ls /tmp/astrosense_uploads/
  ```

- [ ] API Docs show no Firebase references
  ```bash
  Check http://localhost:8000/docs
  ```

---

## 🎯 Summary

### What to Know

1. **JWT Auth:** Fully functional, no changes to usage
2. **File Storage:** Now temporary (per-session) instead of persistent
3. **Per-User:** Each user still has isolated storage
4. **Setup:** Simpler - no Firebase credentials needed
5. **Astronomy:** Ready for your processing pipeline (use `get_file_for_processing()`)

### What Changed in Code

- `storage.py` - Complete rewrite (Firebase → local filesystem)
- `config.py` - Removed Firebase settings
- `main.py` - Added detailed comments, removed Firebase init
- `auth.py` - Added detailed JWT comments
- `requirements.txt` - Removed firebase-admin
- `.env.example` - Removed Firebase config

### What Didn't Change

- Authentication flow
- Frontend code
- API endpoints
- Per-user isolation
- File validation

---

## 🚀 Next Steps

1. **Verify everything compiles:**
   ```bash
   cd server && python -m py_compile app/*.py
   cd server && python -m uvicorn app.main:app --reload
   ```

2. **Test the app:**
   - Register → Login → Upload → Verify file in `/tmp/astrosense_uploads/`

3. **Add astronomy processing:**
   - Create new endpoints referencing `[ASTRONOMY PROCESSING PLACEHOLDER]`
   - Use `get_file_for_processing()` to access uploaded files
   - Process with your CNN/analysis pipeline

4. **Deploy to HuggingFace Spaces:**
   - Push code to repo
   - Create `app.py` wrapper for Gradio if needed
   - Session storage works automatically

---

**That's it! Your AstroSense is ready for astronomy processing. 🚀⭐**
