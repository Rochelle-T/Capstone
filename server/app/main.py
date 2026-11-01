"""
AstroSense FastAPI Backend

This module implements the RESTful API for the AstroSense exoplanet detection platform.

Key features:
- [JWT AUTHENTICATION]: User registration, login, and token-based API protection
- [PER-USER STORAGE]: FITS file uploads stored in isolated user directories
- [ASTRONOMY PROCESSING PLACEHOLDER]: Ready for astronomy analysis pipeline integration

Storage: HuggingFace Spaces session storage (temporary, per-session)
"""

from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
import uuid
from typing import Optional

from app.config import settings
from app.auth import create_access_token, decode_token, hash_password, verify_password
from app.models import UserRegister, UserLogin, TokenResponse
from app.persistence import add_user, get_user, user_exists, get_users_db
from app.exoplanet_analysis import pipeline
from services.inference_service import get_job, get_model_status, submit_kic, warm_model

# Initialize app
app = FastAPI(
    title="AstroSense API",
    description="Exoplanet Detection Platform with FITS File Upload",
    version="1.0.0"
)


@app.on_event("startup")
async def warm_inference_model():
    warm_model()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [JWT AUTHENTICATION]: Persistent user storage (loaded from JSON file)
# For production: Replace with PostgreSQL or other database
users_db = get_users_db()


# ============== JWT AUTHENTICATION DEPENDENCY ==============

async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """
    [JWT AUTHENTICATION]: Dependency that validates JWT token from Authorization header.
    
    Extracts Bearer token from "Authorization: Bearer {token}" header,
    decodes and validates it, then returns the user_id.
    
    Used to protect endpoints that require authentication.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.replace("Bearer ", "", 1)
    token_data = decode_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = token_data.get("user_id")
    # [JWT AUTHENTICATION]: Verify user exists in persistent storage
    if not get_user(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user_id


# ============== [JWT AUTHENTICATION]: AUTH ROUTES ==============

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """
    [JWT AUTHENTICATION]: Register a new user account.
    
    Creates a new user with email/password, stores credentials securely,
    and returns a JWT token for immediate authentication.
    """
    
    # Check if email already exists
    if user_exists(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # [JWT AUTHENTICATION]: Create new user with hashed password
    user_id = str(uuid.uuid4())
    password_hash = hash_password(user_data.password)
    username = user_data.username or user_data.email.split("@")[0]
    
    # Save to persistent storage
    add_user(user_id, user_data.email, password_hash, username)
    
    # [JWT AUTHENTICATION]: Generate JWT token with 30-minute expiry
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=access_token_expires
    )
    
    # [PER-USER STORAGE]: User's isolated storage directory is created automatically on first upload
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id
    }


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """
    [JWT AUTHENTICATION]: Authenticate user and return JWT token.
    
    Validates email/password credentials and returns a JWT token
    that must be included in subsequent API requests.
    """
    
    # [JWT AUTHENTICATION]: Find user by email
    user_id = None
    users_db_current = get_users_db()
    for uid, user in users_db_current.items():
        if user["email"] == user_data.email:
            user_id = uid
            break
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # [JWT AUTHENTICATION]: Verify password against stored hash
    user = users_db_current[user_id]
    if not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # [JWT AUTHENTICATION]: Generate new JWT token with 30-minute expiry
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id
    }


@app.get("/api/auth/me")
async def get_current_user_info(user_id: str = Depends(get_current_user)):
    """
    [JWT AUTHENTICATION]: Get current authenticated user's information.
    
    Requires valid JWT token in Authorization header.
    """
    user = get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return {
        "user_id": user_id,
        "email": user["email"],
        "username": user["username"]
    }


# ============== [ASTRONOMY PROCESSING]: EXOPLANET ANALYSIS ROUTES ==============

@app.post("/api/analyze")
async def analyze_kic(request: dict, user_id: str = Depends(get_current_user)):
    """Queue model inference for a user-provided KIC identifier."""
    kic = request.get("kic")
    if not kic:
        raise HTTPException(status_code=400, detail="Enter a KIC number to begin analysis.")
    try:
        job_id = submit_kic(str(kic))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/jobs/{job_id}")
async def analysis_job(job_id: str, user_id: str = Depends(get_current_user)):
    """Return queued KIC inference status and, when complete, its result."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    return job


@app.get("/api/model/status")
async def model_status(user_id: str = Depends(get_current_user)):
    """Return whether the configured inference model loaded at startup."""
    return get_model_status()

@app.get("/api/exoplanet/targets")
async def get_exoplanet_targets():
    """
    [ASTRONOMY PROCESSING]: Get list of available Kepler target systems
    
    Returns searchable targets for exoplanet analysis
    """
    targets = pipeline.search_targets()
    return {"targets": targets, "count": len(targets)}


@app.post("/api/exoplanet/fetch")
async def fetch_exoplanet_data(request: dict):
    """
    [ASTRONOMY PROCESSING]: Fetch and process Kepler light curve
    
    Steps:
    1. Downloads raw light curve from Kepler archive
    2. Returns time series data (time, flux, error)
    """
    target_name = request.get("target_name")
    if not target_name:
        raise HTTPException(status_code=400, detail="target_name required")
    
    result = pipeline.fetch_lightcurve(target_name)
    return result


@app.post("/api/exoplanet/detrend")
async def detrend_exoplanet_signal():
    """
    [ASTRONOMY PROCESSING]: Detrend and clean light curve
    
    Uses Savitzky-Golay filter (window=401) to remove systematics
    """
    result = pipeline.detrend_signal()
    return result


@app.post("/api/exoplanet/bls")
async def run_bls_analysis(request: dict):
    """
    [ASTRONOMY PROCESSING]: Box Least Squares transit detection
    
    Searches for periodic transits in light curve
    Period range options:
    - hot_jupiter: 0.5-10 days (default)
    - earth_like: 200-400 days
    - super_earth: 1-100 days
    """
    period_range = request.get("period_range", "hot_jupiter")
    
    period_ranges = {
        "hot_jupiter": (0.5, 10),
        "earth_like": (200, 400),
        "super_earth": (1, 100)
    }
    
    pr = period_ranges.get(period_range, (0.5, 10))
    result = pipeline.run_bls(period_range=pr)
    return result


@app.post("/api/exoplanet/phase-fold")
async def phase_fold_data():
    """
    [ASTRONOMY PROCESSING]: Phase-fold at detected orbital period
    
    Shows the transit signal folded at the orbital period
    """
    result = pipeline.phase_fold()
    return result


@app.get("/api/exoplanet/summary")
async def get_analysis_summary():
    """
    [ASTRONOMY PROCESSING]: Get summary statistics of analysis
    
    Returns:
    - Orbital period
    - Transit depth
    - Signal-to-Noise ratio
    - Data quality metrics
    """
    result = pipeline.get_summary_statistics()
    return result


@app.get("/api/exoplanet/plot/{plot_type}")
async def get_analysis_plot(plot_type: str):
    """
    [ASTRONOMY PROCESSING]: Get visualization as base64 image
    
    plot_type options:
    - raw_lc: Raw time-series flux
    - detrended_lc: Detrended signal
    - bls_periodogram: BLS power spectrum
    - folded_lc: Phase-folded transit
    
    Returns base64-encoded PNG image
    """
    if plot_type not in ["raw_lc", "detrended_lc", "bls_periodogram", "folded_lc"]:
        raise HTTPException(status_code=400, detail="Invalid plot_type")
    
    img_base64 = pipeline.generate_plot(plot_type)
    
    if img_base64.startswith("error:"):
        raise HTTPException(status_code=500, detail=img_base64.replace("error:", ""))
    
    return {"plot_type": plot_type, "image": img_base64, "format": "png"}


@app.post("/api/exoplanet/analyze")
async def run_full_analysis(request: dict):
    """
    [ASTRONOMY PROCESSING]: Run complete exoplanet analysis pipeline
    
    Automatically runs:
    1. Fetch light curve
    2. Detrend signal
    3. BLS analysis
    4. Phase folding
    5. Generate summary
    
    Returns all results and plot URLs
    """
    target_name = request.get("target_name")
    period_range = request.get("period_range", "hot_jupiter")
    
    if not target_name:
        raise HTTPException(status_code=400, detail="target_name required")
    
    try:
        # Reset pipeline for fresh analysis
        pipeline.reset()
        print(f"[ANALYZE] Starting analysis for {target_name}")
        
        # Step 1: Fetch
        fetch_result = pipeline.fetch_lightcurve(target_name)
        if fetch_result["status"] != "success":
            raise Exception(fetch_result.get("message", "Failed to fetch data"))
        
        # Step 2: Detrend
        detrend_result = pipeline.detrend_signal()
        if detrend_result["status"] != "success":
            raise Exception(detrend_result.get("message", "Failed to detrend"))
        
        # Step 3: BLS
        period_ranges = {
            "hot_jupiter": (0.5, 10),
            "earth_like": (200, 400),
            "super_earth": (1, 100)
        }
        pr = period_ranges.get(period_range, (0.5, 10))
        bls_result = pipeline.run_bls(period_range=pr)
        if bls_result["status"] != "success":
            raise Exception(bls_result.get("message", "Failed to run BLS"))
        
        # Step 4: Phase fold
        fold_result = pipeline.phase_fold()
        if fold_result["status"] != "success":
            raise Exception(fold_result.get("message", "Failed to phase fold"))
        
        # Step 5: Summary
        summary_result = pipeline.get_summary_statistics()
        
        # Generate plots
        plots = {}
        for plot_type in ["raw_lc", "detrended_lc", "bls_periodogram", "folded_lc"]:
            plot_img = pipeline.generate_plot(plot_type)
            if plot_img.startswith("error:"):
                print(f"[WARNING] Failed to generate {plot_type} plot")
                plots[plot_type] = None
            else:
                plots[plot_type] = plot_img
        
        print(f"[ANALYZE] ✓ Analysis complete for {target_name}")
        
        return {
            "status": "success",
            "target": target_name,
            "period_range": period_range,
            "fetch": fetch_result,
            "detrend": detrend_result,
            "bls": bls_result,
            "phase_fold": fold_result,
            "summary": summary_result,
            "plots": plots
        }
    except Exception as e:
        print(f"[ANALYZE ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== HEALTH CHECK ==============

@app.get("/api/health")
async def health_check():
    """Health check endpoint (no authentication required)."""
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
