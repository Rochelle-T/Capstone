# AstroSense - Complete Setup Guide

## 🚀 Quick Start (For the Impatient)

```bash
# Terminal 1: Backend
cd server
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# Terminal 2: Frontend
cd client
npm install
npm run dev
```

Then visit: **http://localhost:5173/**

---

## 📋 Step-by-Step Setup

### 1. Firebase Configuration (5-10 minutes)

**Why Firebase?** Free tier includes 5GB storage, 1GB daily downloads, and easy authentication.

1. Create a Firebase project:
   - Go to https://console.firebase.google.com/
   - Click **"Add Project"** → Name it **"AstroSense"**
   - Disable Analytics (or keep it) → Create

2. Enable Cloud Storage:
   - Go to **Storage** tab
   - Click **"Create bucket"**
   - Choose **"Start in test mode"** (for development)
   - Select your region → Create

3. Get Service Account Credentials:
   - Click ⚙️ **Settings** → **Project settings**
   - Go to **Service accounts** tab
   - Under Firebase SDK, click **"Generate new private key"**
   - Save the JSON file as **`firebase_credentials.json`**
   - Move it to **`AstroSense/server/`** folder

4. Get Firebase Details:
   - In Project Settings, find your **Project ID**
   - In Storage, find your **Bucket name** (ends with `.appspot.com`)
   - Update `server/.env` with these values

### 2. Backend Setup

```bash
cd server

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and fill in values
copy .env.example .env
# Edit .env and add your Firebase credentials

# Run the server
python -m uvicorn app.main:app --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [1234]
```

✓ **Backend ready at:** http://localhost:8000/docs

### 3. Frontend Setup

```bash
cd client

# Install dependencies
npm install

# Start dev server
npm run dev
```

**Expected output:**
```
VITE v8.0.2 ready in 1515 ms

➜  Local:   http://localhost:5173/
```

✓ **Frontend ready at:** http://localhost:5173/

---

## 🧪 Testing the Application

### 1. Try Registration

1. Open http://localhost:5173/ in your browser
2. Click **"Sign up"**
3. Fill in:
   - **Email:** test@example.com
   - **Username:** testuser
   - **Password:** password123
   - **Confirm Password:** password123
4. Click **"Create Account"**
5. You should be redirected to Dashboard ✓

### 2. Upload a FITS File

1. Create a test FITS file (or rename any file to `.fits`):
   ```bash
   # Create empty test file
   echo "test" > sample.fits
   ```

2. On Dashboard, drag & drop the file into the **"Drop your FITS files here"** box
3. Or click **"Select Files"** button
4. File should appear in **"Your Files"** section ✓

### 3. Verify in Firebase

1. Go to https://console.firebase.google.com/
2. Select your project → **Storage** tab
3. Navigate to **`astrosense-uploads/{your-user-id}/`**
4. Your uploaded file should be there ✓

### 4. API Testing (Optional - with Postman or curl)

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "api@test.com",
    "password": "password123"
  }'

# Response will include access_token - save it

# Get current user (replace TOKEN)
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer TOKEN"

# List files
curl -X GET http://localhost:8000/api/files/list \
  -H "Authorization: Bearer TOKEN"
```

---

## 📁 Project Files Overview

```
AstroSense/
├── server/                      # Backend (FastAPI)
│   ├── app/
│   │   ├── main.py            # Main API & routes
│   │   ├── auth.py            # JWT authentication
│   │   ├── storage.py         # File upload/download
│   │   ├── firebase_config.py # Firebase setup
│   │   ├── config.py          # Settings
│   │   └── models.py          # Data models
│   ├── requirements.txt
│   ├── .env                   # Your secrets here
│   └── README.md
│
├── client/                      # Frontend (React)
│   ├── src/
│   │   ├── pages/             # Login, Register, Dashboard
│   │   ├── context/           # Auth context
│   │   ├── services/          # API calls
│   │   ├── styles/            # Space theme CSS
│   │   ├── App.jsx            # Main component
│   │   └── main.jsx           # Entry point
│   ├── .env                   # Frontend config
│   └── package.json
│
├── README.md                  # Full documentation
├── QUICKSTART.md              # Quick reference
└── SETUP.md                   # This file
```

---

## 🔑 Environment Variables

### Backend (`server/.env`)

```env
# Generate a secure SECRET_KEY: 
# Python: import secrets; print(secrets.token_urlsafe(32))
SECRET_KEY=your-random-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# From Firebase Project Settings
FIREBASE_PROJECT_ID=astrosense-abc123
FIREBASE_STORAGE_BUCKET=astrosense-abc123.appspot.com
FIREBASE_CREDENTIALS_PATH=./firebase_credentials.json

HOST=0.0.0.0
PORT=8000
```

### Frontend (`client/.env`)

```env
VITE_API_URL=http://localhost:8000/api
```

---

## ⚠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| CORS Error | Restart both servers, check `ALLOWED_ORIGINS` in `server/app/config.py` |
| "firebase_credentials.json not found" | Download it from Firebase Console, save to `server/` |
| Upload fails | Use valid FITS file (.fits, .fit, or .fts), max 500MB |
| "Connection refused" | Ensure backend is running on 8000, frontend on 5173 |
| "Invalid token" | Clear localStorage: DevTools → Application → localStorage → Clear |
| npm permission errors | Try: `npm cache clean --force` or run with admin privileges |
| Python module not found | Ensure virtualenv is activated: `.\venv\Scripts\activate` |

---

## 🎯 Architecture

```
User Browser
    ↓
React App (Vite)
    ↓ HTTP/REST
FastAPI Server
    ↓
Firebase Services
    ├── Authentication
    └── Cloud Storage
```

**Data Flow:**
1. User registers → Backend creates JWT token → Stored locally
2. User uploads FITS → Sent to Backend → Saved to Firebase Storage
3. Files organized by user ID: `astrosense-uploads/{user_id}/{filename}`

---

## 📝 API Endpoints Summary

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/api/auth/register` | ❌ | Create account |
| POST | `/api/auth/login` | ❌ | Login & get token |
| GET | `/api/auth/me` | ✅ | Current user info |
| POST | `/api/upload/fits` | ✅ | Upload FITS file |
| GET | `/api/files/list` | ✅ | List user files |
| DELETE | `/api/files/{filename}` | ✅ | Delete file |
| GET | `/api/health` | ❌ | Health check |

---

## 🚀 Production Checklist

Before deploying:

- [ ] Set random `SECRET_KEY` in production
- [ ] Enable HTTPS everywhere
- [ ] Use environment-specific `.env` files
- [ ] Migrate to PostgreSQL for user data
- [ ] Set up proper logging
- [ ] Enable Firebase Security Rules
- [ ] Update CORS allowed origins
- [ ] Add rate limiting
- [ ] Set up error monitoring
- [ ] Configure backups

---

## 📞 Need Help?

1. Check logs: Browser DevTools (F12) and terminal output
2. Review [README.md](../README.md) for detailed docs
3. Check [QUICKSTART.md](../QUICKSTART.md) for quick reference
4. Verify all `.env` files are configured

---

**You're all set! 🎉**

Next, explore adding:
- Spectral analysis features
- Team collaboration
- Data visualization
- Advanced search

Happy coding! 🚀
