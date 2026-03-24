# Quick Start Guide

## Running AstroSense Locally

### Option 1: Run Both Servers from One Terminal (Windows PowerShell)

```powershell
# Open PowerShell and navigate to the project root

# Terminal 1: Start the backend
cd server
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# In a new PowerShell window, Terminal 2: Start the frontend
cd client
npm install
npm run dev
```

### Option 2: Using VS Code Tasks

1. Open VS Code at the project root
2. Press `Ctrl+Shift+D` to open Task Runner
3. Select "Run Backend" to start FastAPI server
4. Open another terminal and run: `cd client && npm run dev`

---

## Environment Setup

### Backend (.env file)

```env
# JWT Configuration
SECRET_KEY=your-super-secret-key-change-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Firebase Configuration
FIREBASE_API_KEY=your_firebase_api_key
FIREBASE_PROJECT_ID=your_firebase_project_id
FIREBASE_STORAGE_BUCKET=your_firebase_bucket.appspot.com
FIREBASE_CREDENTIALS_PATH=./firebase_credentials.json

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### Frontend (.env file)

```env
VITE_API_URL=http://localhost:8000/api
```

---

## Firebase Setup (5 minutes)

1. Go to https://console.firebase.google.com/
2. Click "Create a project" → Enter "AstroSense" → Continue
3. Skip analytics (or enable, your choice)
4. Navigate to "Storage" tab → Click "Create bucket"
5. Start in test mode → Choose region → Create
6. Go to "Project Settings" (⚙️ icon) → Service accounts
7. Click "Generate new private key" → Save `firebase_credentials.json`
8. Move `firebase_credentials.json` to `/server/` directory
9. Copy project details into `.env` file

---

## Test the Application

### Backend API Test (Postman or curl)

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "username": "testuser"
  }'

# Response:
# {
#   "access_token": "eyJ0eXAi...",
#   "token_type": "bearer",
#   "user_id": "uuid..."
# }

# 2. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'

# 3. List Files (replace TOKEN with actual token)
curl -X GET http://localhost:8000/api/files/list \
  -H "Authorization: Bearer TOKEN"
```

### Frontend UI Test

1. Go to http://localhost:5173/
2. Click "Sign up" → Create test account
3. Upload a test FITS file (or any file with .fits extension)
4. See file appear in "Your Files" section
5. Click delete to remove file

---

## Ports

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Cannot import firebase_admin" | Run `pip install -r requirements.txt` in activated venv |
| CORS errors | Restart both servers, check .env files |
| "Firebase credentials not found" | Ensure firebase_credentials.json is in /server/ |
| Upload fails | Check file has .fits extension, size < 500MB |
| Can't login after register | Clear localStorage in browser, check token in Console |

---

## Next Steps

After verifying the app works:

1. **Add data analysis features**: Spectral analysis, object detection
2. **Integrate with astronomy APIs**: SIMBAD, NED
3. **Add visualization**: Light curves, spectra plots
4. **Database upgrade**: Switch from in-memory to PostgreSQL
5. **Deployment**: Deploy to Vercel (frontend) + Render/Railway (backend)

---

## Architecture Diagram

```
┌─────────────────────┐
│   React Frontend    │
│  (Port 5173)        │
│ - Login/Register    │
│ - Dashboard         │
│ - File Upload       │
└──────────┬──────────┘
           │ HTTP/REST
           ↓
┌─────────────────────┐
│  FastAPI Backend    │
│  (Port 8000)        │
│ - JWT Auth          │
│ - File Management   │
└──────────┬──────────┘
           │ gRPC/REST
           ↓
┌─────────────────────┐
│ Firebase Services   │
│ - Authentication    │
│ - Cloud Storage     │
│ - Database          │
└─────────────────────┘
```

