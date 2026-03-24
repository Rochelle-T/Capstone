# Project Structure

```
AstroSense/
│
├── client/                          # React Frontend (Vite)
│   ├── src/
│   │   ├── components/             # React components
│   │   ├── context/
│   │   │   └── AuthContext.jsx     # Auth state management
│   │   ├── pages/
│   │   │   ├── Login.jsx           # Login page
│   │   │   ├── Register.jsx        # Registration page
│   │   │   └── Dashboard.jsx       # Main app page
│   │   ├── services/
│   │   │   └── api.js              # Axios API client
│   │   ├── styles/
│   │   │   ├── Global.css          # Global space theme
│   │   │   ├── Auth.css            # Auth pages styling
│   │   │   └── Dashboard.css       # Dashboard styling
│   │   ├── App.jsx                 # Main app with routing
│   │   └── main.jsx                # Entry point
│   ├── public/                     # Static assets
│   ├── index.html                  # HTML template
│   ├── .env                        # Environment variables
│   ├── package.json
│   ├── vite.config.js
│   └── README.md
│
├── server/                          # FastAPI Backend
│   ├── app/
│   │   ├── main.py                # Main FastAPI app & routes
│   │   ├── auth.py                # JWT & password handling
│   │   ├── config.py              # Settings management
│   │   ├── models.py              # Pydantic data models
│   │   ├── storage.py             # Firebase Storage operations
│   │   ├── firebase_config.py     # Firebase initialization
│   │   └── __init__.py
│   ├── .env                       # Environment variables
│   ├── .env.example               # Environment template
│   ├── requirements.txt           # Python dependencies
│   ├── README.md                  # Backend documentation
│   └── firebase_credentials.json  # Firebase service account (gitignored)
│
├── .gitignore
├── README.md                      # Main project documentation
└── QUICKSTART.md                  # Quick start guide
```

## Key Files Reference

### Backend Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app initialization, routes, CORS config |
| `app/auth.py` | JWT token creation/validation, password hashing |
| `app/config.py` | Environment variable management with Pydantic |
| `app/models.py` | Request/response Pydantic models |
| `app/storage.py` | Firebase Cloud Storage operations |
| `app/firebase_config.py` | Firebase Admin SDK initialization |

### Frontend Files

| File | Purpose |
|------|---------|
| `src/App.jsx` | Main app component with routing setup |
| `src/main.jsx` | React app entry point |
| `src/context/AuthContext.jsx` | Auth state provider & logic |
| `src/services/api.js` | Axios instance & API methods |
| `src/pages/Login.jsx` | User login page |
| `src/pages/Register.jsx` | User registration page |
| `src/pages/Dashboard.jsx` | Main dashboard with file upload |
| `src/styles/*` | Space-themed CSS styling |

## File Storage Structure (Firebase Cloud Storage)

```
Google Cloud Storage Bucket (astrosense-bucket):
│
└── astrosense-uploads/
    ├── {user_id_uuid_1}/
    │   ├── 20240324_143022_keplers_data.fits
    │   ├── 20240324_152015_stars_dataset.fits
    │   └── 20240324_160030_exoplanet_targets.fits
    │
    ├── {user_id_uuid_2}/
    │   └── 20240324_165045_candidate_planets.fits
    │
    └── {user_id_uuid_3}/
        ├── 20240324_170100_spectral_analysis.fits
        └── 20240324_171200_light_curves.fits
```

## Environment Variables

### Server (.env)

```env
# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Firebase
FIREBASE_API_KEY=AIxxxxxx
FIREBASE_PROJECT_ID=astrosense-project
FIREBASE_STORAGE_BUCKET=astrosense-project.appspot.com
FIREBASE_CREDENTIALS_PATH=./firebase_credentials.json

# Server
HOST=0.0.0.0
PORT=8000
```

### Client (.env)

```env
VITE_API_URL=http://localhost:8000/api
```

## Dependencies

### Backend (requirements.txt)

- fastapi==0.104.1
- uvicorn==0.24.0
- python-jose==3.3.0
- passlib==1.7.4
- python-multipart==0.0.6
- pydantic==2.5.0
- firebase-admin==6.2.0
- PyJWT==2.8.1
- pydantic-settings==2.1.0

### Frontend (package.json)

- react
- react-router-dom
- axios
- vite

## Database Schema (Future - currently in-memory)

```
users:
├── user_id (UUID, PK)
├── email (String, unique)
├── username (String)
├── password_hash (String)
└── created_at (DateTime)

files_metadata:
├── file_id (UUID, PK)
├── user_id (UUID, FK)
├── filename (String)
├── size (Integer)
├── upload_date (DateTime)
└── storage_path (String)
```
