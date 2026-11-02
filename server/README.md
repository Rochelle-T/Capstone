# Installation and Setup Guide for AstroSense Backend

## Prerequisites
- Python 3.9+
- pip

## Setup Instructions

### 1. Create Virtual Environment
```bash
cd server
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy the example file
copy .env.example .env
# On macOS/Linux:
# cp .env.example .env

# Edit .env if needed (defaults are usually fine)
```

### 4. Run Development Server
```bash
python -m uvicorn app.main:app --reload
```

Server will run at: http://localhost:8000

### API Documentation
- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user info

### File Management
- `POST /api/upload/fits` - Upload FITS file
- `GET /api/files/list` - List user's files
- `DELETE /api/files/{filename}` - Delete file

### KIC model inference

`POST /api/analyze` runs both configured models for one KIC identifier. The
Stage 1 TensorFlow model uses its existing preprocessing, while the PyTorch
AttentionMIL model uses the Savitzky-Golay/gap-2.5 pipeline from
`kepler_pipeline 2.py`. FITS files are cached and reused; the second pipeline
also retrieves short-cadence files required by its training configuration.
Results are returned independently under `result.models.stage_1_cnn` and
`result.models.attention_mil`.

## Storage

### Session Storage Structure
Files are stored temporarily on HuggingFace Spaces with per-user isolation:
```
SESSION_STORAGE_BASE/
├── {user_id_1}/
│   ├── 20240324_143022_keplers_data.fits
│   └── 20240324_152015_stars_dataset.fits
└── {user_id_2}/
    └── 20240324_165045_candidate_planets.fits
```

[PER-USER STORAGE]: Each user has isolated storage at SESSION_STORAGE_BASE/{user_id}/

### Storage is Temporary
Files are stored in HuggingFace Spaces session storage or /tmp/astrosense_uploads
and are cleared when the session ends.

## Development Notes

### [JWT AUTHENTICATION]
- Uses PyJWT for token creation/validation
- Passwords hashed with bcrypt
- Tokens expire after 30 minutes (configurable)
- All file operations require valid JWT token

### [PER-USER STORAGE]
- Each user's files stored in isolated directory
- Users cannot access other users' files
- File paths validated to prevent directory traversal

### [ASTRONOMY PROCESSING PLACEHOLDER]
- Files are ready for astronomy processing pipeline
- Use `get_file_for_processing()` to access uploaded files
- Processing logic will be added later in Colab

## Future: Production Deployment

For production use:
1. Use PostgreSQL instead of in-memory user storage
2. Set strong SECRET_KEY
3. Enable HTTPS
4. Implement Cloud Storage (GCS, S3) instead of local storage
5. Add proper error logging and monitoring
