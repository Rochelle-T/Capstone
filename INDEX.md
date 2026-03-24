# 📚 AstroSense Documentation Index

## Quick Navigation

### 🚀 **Getting Started**
Start here if you're new to the project:
- [**SETUP.md**](./SETUP.md) - Complete step-by-step installation
- [**QUICKSTART.md**](./QUICKSTART.md) - Quick command reference

### 📖 **Understanding the Project**
Learn how everything fits together:
- [**README.md**](./README.md) - Full project documentation
- [**IMPLEMENTATION.md**](./IMPLEMENTATION.md) - What was built and why
- [**STRUCTURE.md**](./STRUCTURE.md) - Detailed file structure

### 🔧 **Technical Reference**
Deep dive into specific components:
- [**server/README.md**](./server/README.md) - Backend API documentation
- [**API Docs** (Live)](http://localhost:8000/docs) - Interactive API documentation (after running backend)

### 🎯 **For the Impatient**

```bash
# Just want to run it? Do this:

# Terminal 1:
cd server
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your Firebase credentials
python -m uvicorn app.main:app --reload

# Terminal 2:
cd client
npm install
npm run dev

# Then visit: http://localhost:5173/
```

---

## 📋 What You Have

### ✅ Backend (FastAPI)
- JWT authentication
- User registration & login
- FITS file upload to Firebase
- Per-user file storage
- File listing & deletion
- Environment-based configuration

### ✅ Frontend (React)
- Beautiful space-themed UI
- User authentication pages
- Dashboard with file upload
- Responsive design
- Protected routes

### ✅ Infrastructure
- Firebase Cloud Storage integration
- Free tier: 5GB storage, 1GB/day downloads
- Per-user file isolation
- JWT token management

---

## 🔑 Before Running

### Required: Firebase Project

1. Create project at https://console.firebase.google.com/
2. Enable Cloud Storage
3. Download service account JSON
4. Save as `server/firebase_credentials.json`
5. Update `server/.env`

⏱️ **Takes ~5-10 minutes**

---

## 📂 File Organization

```
SETUP.md ...................... ← Start here
├─ QUICKSTART.md .............. (Quick ref)
├─ IMPLEMENTATION.md .......... (What was built)
├─ STRUCTURE.md ............... (File structure)
├─ README.md .................. (Full docs)
│
├─ server/ ..................... (Backend)
│  ├─ requirements.txt
│  ├─ .env.example ← Copy to .env and edit
│  ├─ app/
│  │  ├─ main.py ............ (API endpoints)
│  │  ├─ auth.py ............ (JWT logic)
│  │  ├─ storage.py ......... (Firebase ops)
│  │  └─ ...
│  └─ README.md
│
└─ client/ ..................... (Frontend)
   ├─ .env ..................... (API URL)
   ├─ src/
   │  ├─ pages/
   │  │  ├─ Login.jsx
   │  │  ├─ Register.jsx
   │  │  └─ Dashboard.jsx
   │  ├─ styles/
   │  │  ├─ Global.css
   │  │  ├─ Auth.css
   │  │  └─ Dashboard.css
   │  └─ ...
   └─ package.json
```

---

## 🚀 Architecture at a Glance

```
┌──────────────────┐
│  React Frontend  │ http://localhost:5173
│  (Vite)          │
└────────┬─────────┘
         │ HTTP/REST
         ↓
┌──────────────────┐
│  FastAPI Backend │ http://localhost:8000
│                  │ [Docs: /docs]
└────────┬─────────┘
         │ gRPC/HTTP
         ↓
┌──────────────────┐
│ Firebase Services│
│ - Storage        │
│ - Auth           │
│ - Firestore      │
└──────────────────┘
```

---

## ✨ Key Features

| Feature | Status | Details |
|---------|--------|---------|
| User Registration | ✅ | Email + Password + Username |
| User Login | ✅ | JWT token (30 min expiry) |
| File Upload | ✅ | FITS format, 500MB max, per-user |
| File Browser | ✅ | List with size, date |
| File Deletion | ✅ | With confirmation dialog |
| Drag & Drop | ✅ | Intuitive UI/UX |
| Space Theme | ✅ | Dark mode with animations |
| Responsive | ✅ | Mobile, tablet, desktop |
| Protected Routes | ✅ | Auto redirect if not logged in |

---

## 🧪 Testing Your Setup

After starting both servers (`npm run dev` + `python -m uvicorn...`):

1. ✅ Visit http://localhost:5173
2. ✅ Click "Sign up"
3. ✅ Create test account
4. ✅ Upload a `.fits` file
5. ✅ See it in "Your Files"
6. Check Firebase Console to verify upload

---

## 📞 Getting Help

### Problem: Can't start backend
→ Check [SETUP.md - Troubleshooting](./SETUP.md#-troubleshooting)

### Problem: Firebase not connecting
→ See [SETUP.md - Firebase Configuration](./SETUP.md#1-firebase-configuration-5-10-minutes)

### Problem: CORS errors
→ Check [SETUP.md - Troubleshooting](./SETUP.md#-troubleshooting)

### Problem: Upload fails
→ Ensure file is `.fits` format and < 500MB

### Want API details?
→ Check [server/README.md](./server/README.md#api-endpoints)

---

## 🎯 Recommended Learning Path

1. **Read:** [SETUP.md](./SETUP.md) - Get it running
2. **Explore:** [Dashboard.jsx](./client/src/pages/Dashboard.jsx) - Frontend logic
3. **Understand:** [main.py](./server/app/main.py) - Backend API
4. **Deploy:** Follow production checklist in [README.md](./README.md)

---

## 🔐 Security Notes

- ✅ Passwords are hashed with bcrypt
- ✅ JWT tokens expire after 30 minutes
- ✅ Each user's files are isolated
- ✅ CORS is configured
- ✅ File types validated (FITS only)
- ✅ File sizes checked (500MB max)

**For production:** Update SECRET_KEY, enable HTTPS, set proper CORS origins

---

## 🎨 Design Inspiration

Your AstroFusion hackathon UI theme is reflected in:
- Dark background with animated stars
- Cyan (#00d9ff) and purple (#7c3aed) gradients
- Smooth animations and transitions
- Modern card-based layouts
- Professional typography

---

## 📊 Next Steps After Setup

### Immediate (1-2 hours):
- [ ] Get it running locally
- [ ] Test registration & upload
- [ ] Verify Firebase integration

### Short-term (1-2 days):
- [ ] Familiarize with code structure
- [ ] Try modifying UI colors/fonts
- [ ] Add a new API endpoint

### Medium-term (1 week):
- [ ] Add data analysis features
- [ ] Integrate astronomy APIs
- [ ] Upgrade to PostgreSQL

### Long-term (ongoing):
- [ ] Deploy to production
- [ ] Add advanced features
- [ ] Build team collaboration

---

## 🚀 Success Criteria

You'll know it's working when:
- ✅ Frontend loads at localhost:5173
- ✅ Can register & login
- ✅ Can upload FITS file
- ✅ File appears in list
- ✅ File visible in Firebase Console
- ✅ Can delete files
- ✅ API docs load at localhost:8000/docs

---

## 📝 Notes

- This is a **full-stack MVP** ready for production optimization
- Backend is **stateless** and horizontally scalable
- Frontend is **responsive** and mobile-ready
- All code is **well-documented** and follows best practices
- **Free Firebase tier** is sufficient for development/MVP

---

## 🎉 Ready to Start?

### Next Command:
```bash
# Read the setup guide
cat SETUP.md
```

Or just jump in:
```bash
cd server && python -m venv venv && .\venv\Scripts\activate && pip install -r requirements.txt
# Then in new terminal:
cd client && npm install && npm run dev
```

---

**Welcome to AstroSense! 🚀⭐**

*Built with FastAPI, React, Vite, and Firebase*

---

Last Updated: March 24, 2025
