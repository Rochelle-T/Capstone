# AstroSense - Exoplanet Detection Platform

## Overview

AstroSense is a modern web application for exoplanet detection and astronomical data analysis. It features:

- **JWT Authentication**: Secure user registration and login
- **KIC-Based Inference**: Retrieve Kepler light curves by KIC and score transit windows with the trained CNN
- **Space-Themed UI**: Modern, responsive interface inspired by astronomical themes
- **Real-time File Management**: List, upload, and delete FITS files

## Architecture

```
AstroSense/
├── client/                 # React Frontend (Vite)
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── context/       # Auth context
│   │   ├── pages/         # Page components (Login, Register, Dashboard)
│   │   ├── services/      # API service layer
│   │   ├── styles/        # CSS styling (space theme)
│   │   ├── App.jsx        # Main app component with routing
│   │   └── main.jsx       # Entry point
│   └── ...
│
└── server/                 # FastAPI Backend
    ├── app/
    │   ├── main.py        # FastAPI application & routes
    │   ├── auth.py        # JWT authentication logic
    │   ├── config.py      # Configuration management
    │   ├── models.py      # Pydantic models
    │   ├── storage.py     # Firebase Storage operations
    │   └── firebase_config.py  # Firebase initialization
    ├── requirements.txt
    └── .env              # Environment variables
```

## Features

### Authentication
- User registration with email and password
- Secure login with JWT tokens
- Token-based API authentication
- 30-minute token expiration (configurable)

### KIC Analysis
- Enter a Kepler Input Catalog (KIC) identifier
- Retrieve long-cadence data from MAST
- Preprocess it with the training-compatible pipeline
- Run the CNN in a background job and review the stitched light curve

### Frontend
- Modern dark space theme
- Responsive design (mobile, tablet, desktop)
- Real-time upload feedback
- Protected routes for authenticated users
- Clean navigation and user info display

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+
- Firebase project (free tier available)

### Backend Setup

1. **Navigate to server directory**
   ```bash
   cd server
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Firebase**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a new project
   - Enable Cloud Storage
   - Download service account JSON
   - Save as `firebase_credentials.json` in server directory

5. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Firebase credentials
   ```

6. **Run development server**
   ```bash
   python -m uvicorn app.main:app --reload
   ```
   
   Server runs at: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Frontend Setup

1. **Navigate to client directory**
   ```bash
   cd client
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure API endpoint** (already set in `.env`)
   ```bash
   # .env should contain:
   VITE_API_URL=http://localhost:8000/api
   ```

4. **Run development server**
   ```bash
   npm run dev
   ```
   
   Frontend runs at: http://localhost:5173

## API Endpoints

### Authentication

- **POST** `/api/auth/register` - Register new user
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword",
    "username": "optional-username"
  }
  ```

- **POST** `/api/auth/login` - Login user
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword"
  }
  ```

- **GET** `/api/auth/me` - Get current user info (requires auth)

- **POST** `/api/analyze` - Queue KIC model inference (requires auth)
- **GET** `/api/jobs/{job_id}` - Poll an inference job (requires auth)
- **GET** `/api/model/status` - Confirm the model loaded at startup (requires auth)

- **GET** `/api/health` - Health check

## Security Features

- **JWT Tokens**: Secure, time-limited authentication
- **Password Hashing**: Bcrypt password hashing
- **Per-User File Isolation**: Files stored in `astrosense-uploads/{user_id}/` directories
- **CORS Protection**: Configured CORS headers
- **Token Validation**: All protected endpoints validate JWT

## Database & Storage

- **Authentication**: In-memory storage (MVP) - can be upgraded to PostgreSQL/Firestore
- **File Storage**: Firebase Cloud Storage with per-user directory structure
- **Scalability**: Firebase free tier: 5GB storage, 1GB/day download

## Development Notes

### For Production Deployment

1. **Replace in-memory user storage** with persistent database (PostgreSQL, Firestore)
2. **Update SECRET_KEY** in server `.env`
3. **Enable HTTPS** for all connections
4. **Set CORS allowed origins** appropriately
5. **Use environment-specific configurations**
6. **Set up proper error logging**

### File Structure in Cloud Storage

```
astrosense-uploads/
├── {user_id_1}/
│   ├── 20250324_143022_keplers_data.fits
│   └── 20250324_152015_stars_data.fits
└── {user_id_2}/
    └── 20250324_160030_exoplanet_candidates.fits
```

## Troubleshooting

### CORS Errors
- Ensure frontend URL is in `settings.ALLOWED_ORIGINS` in `server/app/config.py`
- Check that both frontend and backend are running

### Confirm model integration

When the backend starts, the log should contain `Application startup complete` after TensorFlow loads. After signing in, open the dashboard and check the **MODEL STATUS** card. It should show `Loaded`.

You can also open `http://localhost:8000/docs`, authorize with a bearer token, and call `GET /api/model/status`. A successful response contains `"available": true`. To test the complete path, submit KIC `9850966` from **Analysis** and poll the job until its status is `done`.

### Firebase Connection Issues
- Verify `firebase_credentials.json` exists and is valid
- Check Firebase project ID and storage bucket in `.env`
- Ensure Cloud Storage bucket is created in Firebase Console

### Authentication Failed
- Clear localStorage in browser dev tools
- Check that token is being sent in Authorization header
- Verify JWT_SECRET_KEY is consistent

### File Upload Issues
- Ensure file has valid FITS extension (.fits, .fit, or .fts)
- Check file size doesn't exceed 500MB
- Verify user has available storage quota

## License

MIT

## Support

For issues or questions, please create an issue in the repository.
