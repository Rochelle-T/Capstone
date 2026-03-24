# Astronomy Processing Integration Guide

This guide shows you exactly where and how to plug in your astronomy analysis pipeline later.

---

## 🔬 Where Astronomy Processing Will Go

### [ASTRONOMY PROCESSING PLACEHOLDER] Markers

Comments throughout the codebase mark integration points:

**In `app/storage.py`:**
```python
async def get_file_for_processing(user_id: str, filename: str) -> str:
    """
    Get file path for astronomy processing.
    [ASTRONOMY PROCESSING PLACEHOLDER]: Processing pipeline will use this to access uploaded files
    
    Returns the full path to the file for processing.
    """
    user_storage = get_user_storage_path(user_id)
    file_path = user_storage / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )
    
    return str(file_path)
```

**In `app/main.py`:**
```python
@app.post("/api/upload/fits", response_model=FileUploadResponse)
async def upload_fits(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    [JWT AUTHENTICATION]: Upload a FITS file (requires valid JWT token).
    [PER-USER STORAGE]: File stored in user's isolated session storage directory.
    [ASTRONOMY PROCESSING PLACEHOLDER]: Uploaded file can be accessed by astronomy processing pipeline later.
    """
```

---

## 📋 Three Integration Approaches

### Approach 1: Backend Processing Endpoint (Recommended for Real-time)

Add this new endpoint to `app/main.py`:

```python
from typing import Dict, Any

@app.post("/api/analyze/fits/{filename}")
async def analyze_fits_file(
    filename: str,
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    [ASTRONOMY PROCESSING PLACEHOLDER]: Analyze a FITS file with astronomy pipeline.
    
    [JWT AUTHENTICATION]: Requires valid JWT token
    [PER-USER STORAGE]: Accesses file from user's isolated directory
    
    Process Steps:
    1. Get file path from session storage
    2. Load FITS file with astropy
    3. Convert 2D → 1D (if needed)
    4. Run CNN model inference
    5. Return predictions
    
    Returns: Analysis results including predictions
    """
    
    # Get file path [ASTRONOMY PROCESSING PLACEHOLDER]
    from app.storage import get_file_for_processing
    file_path = await get_file_for_processing(user_id, filename)
    
    # TODO: Import your astronomy processing functions
    # from astronomy_pipeline import process_fits_cnn
    
    try:
        # TODO: Add your processing logic here
        # results = await process_fits_cnn(file_path)
        
        # Placeholder response
        results = {
            "filename": filename,
            "status": "processing",
            "message": "Astronomy processing pipeline not yet implemented"
        }
        
        return results
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@app.get("/api/results/{filename}")
async def get_analysis_results(
    filename: str,
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    [ASTRONOMY PROCESSING PLACEHOLDER]: Get stored results of previous analysis.
    
    Returns: Cached processing results
    """
    # TODO: Implement results storage and retrieval
    # Results could be cached in memory, Redis, or file system
    
    return {
        "filename": filename,
        "results": "Results storage not yet implemented"
    }
```

Then update your frontend to call this endpoint after upload:

```javascript
// In client/src/pages/Dashboard.jsx

const handleFileUpload = async (file) => {
  // ... existing upload code ...
  
  // After successful upload, start analysis
  try {
    const analysisResponse = await axios.post(
      `/api/analyze/fits/${file.name}`,
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );
    console.log("Analysis results:", analysisResponse.data);
  } catch (error) {
    console.error("Analysis failed:", error);
  }
};
```

---

### Approach 2: Batch Processing Endpoint (For Multiple Files)

Add this endpoint to `app/main.py`:

```python
@app.post("/api/process/batch")
async def batch_process_files(
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    [ASTRONOMY PROCESSING PLACEHOLDER]: Process all uploaded files in batch.
    
    Useful for processing large datasets or when you want to run all analyses together.
    """
    
    from app.storage import list_user_files, get_file_for_processing
    
    try:
        # Get all user's files [PER-USER STORAGE]
        files = await list_user_files(user_id)
        
        results = []
        
        for file_info in files:
            # Get path for processing [ASTRONOMY PROCESSING PLACEHOLDER]
            file_path = await get_file_for_processing(user_id, file_info["name"])
            
            # TODO: Add your batch processing logic
            # result = await your_astronomy_pipeline(file_path)
            
            results.append({
                "filename": file_info["name"],
                "size": file_info["size"],
                "status": "queued"  # Will be "processing" or "completed"
                # "analysis": result  # Add results here
            })
        
        return {
            "total_files": len(files),
            "batch_id": str(uuid.uuid4()),
            "results": results,
            "status": "processing"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )
```

---

### Approach 3: External Processing (For Colab/Jupyter)

If you want to process files from external scripts (like Colab):

**Create `app/api_client.py` in your project:**

```python
"""
Client library for accessing AstroSense API from external scripts (e.g., Colab)
"""

import requests
from typing import Optional, Dict, Any
from pathlib import Path

class AstroSenseClient:
    """Client for AstroSense API with astronomy processing support"""
    
    def __init__(self, api_url: str = "http://localhost:8000/api"):
        self.api_url = api_url
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
    
    def register(self, email: str, password: str) -> str:
        """Register and get JWT token"""
        response = requests.post(
            f"{self.api_url}/auth/register",
            json={"email": email, "password": password}
        )
        data = response.json()
        self.token = data["access_token"]
        self.user_id = data["user_id"]
        return self.token
    
    def login(self, email: str, password: str) -> str:
        """Login and get JWT token"""
        response = requests.post(
            f"{self.api_url}/auth/login",
            json={"email": email, "password": password}
        )
        data = response.json()
        self.token = data["access_token"]
        self.user_id = data["user_id"]
        return self.token
    
    def upload_fits(self, file_path: str) -> Dict[str, Any]:
        """
        Upload FITS file.
        [ASTRONOMY PROCESSING PLACEHOLDER]: File accessible at returned path
        """
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{self.api_url}/upload/fits",
                headers={"Authorization": f"Bearer {self.token}"},
                files={"file": f}
            )
        return response.json()
    
    def list_files(self) -> Dict[str, Any]:
        """List uploaded files"""
        response = requests.get(
            f"{self.api_url}/files/list",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        return response.json()
    
    def get_file_path(self, filename: str) -> str:
        """
        [ASTRONOMY PROCESSING PLACEHOLDER]: Get path to file for processing.
        
        Returns full path that can be passed to your astronomy pipeline.
        """
        # In production, you might have an endpoint for this
        # For now, construct the path based on known storage structure
        return f"/tmp/astrosense_uploads/{self.user_id}/{filename}"


# Usage in Colab:
if __name__ == "__main__":
    # Initialize client
    client = AstroSenseClient()
    
    # Register/Login
    client.register("user@example.com", "password")
    
    # Upload FITS file
    upload_result = client.upload_fits("my_data.fits")
    print(f"Uploaded: {upload_result['filename']}")
    
    # Get file path for processing [ASTRONOMY PROCESSING PLACEHOLDER]
    file_path = client.get_file_path(upload_result['stored_as'])
    
    # Now use in your astronomy pipeline
    # result = my_cnn_model.predict(file_path)
    # 2D_spectrum = load_fits(file_path)
    # 1D_spectrum = convert_2d_to_1d(2D_spectrum)
    # predictions = model.predict(1D_spectrum)
```

**Usage in Colab:**

```python
# In Colab cell 1: Upload code
from api_client import AstroSenseClient

client = AstroSenseClient("http://localhost:8000/api")
client.register("colab@test.com", "password")

# Upload a FITS file
result = client.upload_fits("sample_spectrum.fits")
file_path = client.get_file_path(result['stored_as'])
print(f"File stored at: {file_path}")

# In Colab cell 2: Processing code
# [ASTRONOMY PROCESSING PLACEHOLDER]: Process the file
from astropy.io import fits
import numpy as np
from tensorflow import keras

model = keras.models.load_model('my_exoplanet_model.h5')

# Load FITS file [ASTRONOMY PROCESSING PLACEHOLDER]
hdu_list = fits.open(file_path)
data_2d = hdu_list[0].data

# Convert 2D → 1D if needed [ASTRONOMY PROCESSING PLACEHOLDER]
spectrum_1d = np.mean(data_2d, axis=0)

# Run inference [ASTRONOMY PROCESSING PLACEHOLDER]
predictions = model.predict(np.expand_dims(spectrum_1d, axis=0))
print(f"Exoplanet detection: {predictions}")
```

---

## 🔌 Integration Checklist

### Step 1: Decide on Approach
- [ ] Real-time processing (Approach 1 - recommended)
- [ ] Batch processing (Approach 2)
- [ ] External processing (Approach 3 - for Colab)

### Step 2: Import Your Astronomy Code
```python
# Add to app/main.py or new file
from your_astronomy_module import (
    process_fits_cnn,
    convert_2d_to_1d,
    run_exoplanet_detection
)
```

### Step 3: Replace TODO Comments
Find and replace all instances of:
```python
# TODO: Add your processing logic here
```

With your actual processing code.

### Step 4: Test with Sample File
- Upload a test FITS file
- Trigger processing
- Verify results appear

### Step 5: Add Results Caching (Optional)
```python
# Cache results to avoid reprocessing
from functools import lru_cache

@lru_cache(maxsize=128)
def process_and_cache(file_path: str):
    return your_cnn_model.predict(file_path)
```

---

## 📦 Expected Processing Functions

Based on your description, you'll likely need functions like:

```python
async def process_fits_file(file_path: str) -> Dict[str, Any]:
    """
    [ASTRONOMY PROCESSING PLACEHOLDER]: Main processing pipeline.
    
    Input: Path to FITS file
    Steps:
    1. Load FITS file with astropy
    2. Extract spectral data (2D array)
    3. Convert to 1D spectrum if needed
    4. Normalize and preprocess
    5. Run CNN model
    6. Return predictions and metadata
    """
    from astropy.io import fits
    
    # Load FITS
    with fits.open(file_path) as hdul:
        data = hdul[0].data
    
    # TODO: Convert 2D → 1D
    # spectrum_1d = your_conversion_function(data)
    
    # TODO: Run CNN
    # predictions = your_model.predict(spectrum_1d)
    
    return {
        "file": file_path,
        "status": "processed",
        "predictions": {},  # predictions
        "metadata": {}
    }
```

---

## 🧪 Testing Processing Integration

### Test Endpoint with curl
```bash
# Trigger analysis
curl -X POST http://localhost:8000/api/analyze/fits/myfile.fits \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get results
curl -X GET http://localhost:8000/api/results/myfile.fits \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test with Python
```python
import requests

headers = {"Authorization": f"Bearer {token}"}

# Upload file
files = {"file": open("data.fits", "rb")}
response = requests.post(
    "http://localhost:8000/api/upload/fits",
    headers=headers,
    files=files
)
uploaded = response.json()

# Analyze it
response = requests.post(
    f"http://localhost:8000/api/analyze/fits/{uploaded['stored_as']}",
    headers=headers
)
results = response.json()
print(results)
```

---

## 📍 Key Functions to Know

### In `app/storage.py`

```python
# Get path for your processing
file_path = await get_file_for_processing(user_id, filename)
# Returns: "/tmp/astrosense_uploads/{user_id}/{filename}"

# List all user's files for batch processing
files = await list_user_files(user_id)
# Returns: [{"name": "...", "size": ..., "path": "..."}, ...]

# Get user's base storage directory
user_dir = get_user_storage_path(user_id)
# Returns: Path("/tmp/astrosense_uploads/{user_id}/")
```

### In `app/main.py`

```python
# All file endpoints are protected with JWT [JWT AUTHENTICATION]
@app.post("/api/upload/fits")
async def upload_fits(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)  # [JWT AUTHENTICATION]
):
    # user_id guaranteed valid here
    # file_path will be in /tmp/astrosense_uploads/{user_id}/
```

---

## 🎯 Once Your Processing Is Ready

1. **Test locally:**
   ```bash
   python -m uvicorn app.main:app --reload
   # Upload file, trigger processing, check results
   ```

2. **Deploy to HuggingFace Spaces:**
   - Push code to repo
   - Spaces automatically detects `app.py` or uses your API
   - Has persistent `/tmp` storage per session

3. **Scale up:**
   - Add request queuing (Celery/RQ)
   - Store results in persistent database
   - Add result pagination
   - Implement progress tracking

---

## 💡 Pro Tips

### Processing Performance
```python
# Use async for file I/O
async def load_fits_async(path):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fits.open, path)
```

### Large Files
```python
# Stream large files to avoid memory issues
async def process_large_fits(file_path: str, chunk_size: int = 1024):
    with fits.open(file_path, memmap=True) as hdul:
        # Process chunks if needed
        data = hdul[0].data
```

### Error Handling
```python
try:
    results = await process_fits_file(file_path)
except AstropyIOError as e:
    raise HTTPException(400, f"Invalid FITS: {e}")
except ModelError as e:
    raise HTTPException(500, f"Processing failed: {e}")
```

---

## 🚀 Next Steps

1. Search for `[ASTRONOMY PROCESSING PLACEHOLDER]` in all files
2. Replace with your processing logic
3. Test with sample FITS files
4. Deploy to HuggingFace Spaces

That's it! Your AstroSense is ready for your astronomy pipeline. 🌌🚀
