# Multi-Storage Backend Setup Guide

AstroSense now supports **three storage backends**. Choose based on your needs:

## 🎯 Quick Decision Matrix

| Backend | Best For | Setup Time | Cost |
|---------|----------|------------|------|
| **LOCAL** | Development, Testing | < 1 min | Free |
| **HuggingFace** | Production on HF Spaces | Auto | Free |
| **Zenodo** | Production, Public Archive | ~ 5 min | Free |

---

## 1️⃣ LOCAL STORAGE (Default)

**Best for:** Development, testing locally

**Setup:**
- No configuration needed
- Files save to `./uploads/` directory
- Per-user isolation: `./uploads/{user_id}/{timestamp}_{filename}`

**In `.env`:**
```env
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./uploads
```

**Test it:**
1. Register a user
2. Upload a FITS file
3. Check `./uploads/` folder - file should be there! ✅

---

## 2️⃣ HUGGINGFACE SPACES

**Best for:** Production deployment on HuggingFace Spaces

**Setup:**
- **Zero configuration!** Auto-detects when running on HF Spaces
- Automatically uses `GRADIO_TEMP_DIR` environment variable
- Files stored in HF temporary directory (cleared per session)

**In `.env`:**
```env
STORAGE_BACKEND=huggingface
```

**What happens:**
- When deployed on HF Spaces, this automatically activates
- `GRADIO_TEMP_DIR` is set by HuggingFace (`/tmp` with special permissions)
- No API keys or tokens needed!

**Test it on HF:**
1. Create a Space on huggingface.co/spaces
2. Upload this repo
3. Register user
4. Upload FITS → automatically goes to HF temp storage
5. Files cleared when Space restarts ✅

---

## 3️⃣ ZENODO INTEGRATION 🌟

**Best for:** Production with persistent, citable data archives

### Step 1: Create Zenodo Account

1. Go to: **https://sandbox.zenodo.org/** (test environment)
   - OR **https://zenodo.org/** (production)
   - Click "Sign up"
   - Create account with email

### Step 2: Create API Token

1. After login, go to: **Settings → Personal access tokens**
   - For sandbox: https://sandbox.zenodo.org/account/settings/applications/tokens/new
   - For production: https://zenodo.org/account/settings/applications/tokens/new

2. Click **"New token"**

3. Give it a name: `AstroSense Upload`

4. **Select Scopes** (MUST select these exact ones):
   - ✅ `deposit:write` - upload files
   - ✅ `deposit:actions` - publish depositions
   
5. Click **"Create"**

6. **Copy the token** (looks like: `lFfqO6bNtC5N8pRxYzAoKqJwMnLpTvUs1FgHjBoP7mQ`)

### Step 3: Configure `.env`

```env
# Switch to Zenodo backend
STORAGE_BACKEND=zenodo

# Paste your token here
ZENODO_API_TOKEN=lFfqO6bNtC5N8pRxYzAoKqJwMnLpTvUs1FgHjBoP7mQ

# Use sandbox for testing (true = sandbox, false = production)
ZENODO_SANDBOX_MODE=true
```

### Step 4: Test Zenodo Upload

Current Status:
- ✅ Files upload to Zenodo automatically
- ✅ Each file gets a persistent URL
- ✅ Metadata includes user info, keywords, description
- ✅ Published automatically (public upload)
- ❌ No file listing (Zenodo limitation)
- ❌ No file deletion from API (Zenodo archives files)

**Test it:**
```bash
cd server
pip install -r requirements.txt  # Install 'requests' library
python -m uvicorn app.main:app --reload
```

Then:
1. Frontend: Register → Upload FITS
2. Check response: Should have `"backend": "zenodo"`
3. Visit the `"public_url"` link - file is live on Zenodo! 🎉

### Zenodo Response Example

```json
{
  "filename": "spectrum.fits",
  "stored_as": "12345678",
  "size": 1048576,
  "public_url": "https://sandbox.zenodo.org/record/12345678",
  "backend": "zenodo",
  "zenodo_record_id": 12345678,
  "uploaded_at": "2026-03-24T15:30:00.000000"
}
```

---

## 🔄 Switching Backends

Edit `.env` and change `STORAGE_BACKEND`:

```env
# Try Zenodo
STORAGE_BACKEND=zenodo
ZENODO_API_TOKEN=your_token_here

# Back to local
STORAGE_BACKEND=local
```

Restart the backend:
```bash
# Press Ctrl+C to stop
python -m uvicorn app.main:app --reload
# Automatically restarts!
```

**Each backend is independent** - files don't mix between backends.

---

## 🚀 Deployment Scenarios

### Scenario 1: Local Development
```env
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./uploads
```
✅ Works on Windows/Mac/Linux
✅ No internet needed
✅ Files stay local

### Scenario 2: HuggingFace Spaces (Recommended for MVP)
```env
STORAGE_BACKEND=huggingface
# GRADIO_TEMP_DIR auto-detected by HF
```
✅ Free hosting
✅ Auto-provisioned storage
✅ Share link with anyone
❌ Files cleared on restart

### Scenario 3: Production with Zenodo Archive
```env
STORAGE_BACKEND=zenodo
ZENODO_API_TOKEN=your_production_token
ZENODO_SANDBOX_MODE=false
```
✅ Persistent URLs
✅ Public citations available
✅ DOI support
✅ Professional archive
❌ Requires Zenodo account

### Scenario 4: Multi-Backend (Future)
```env
STORAGE_BACKEND=all
# Stages to local + HF + Zenodo simultaneously
```
🚧 Not yet implemented, see ASTRONOMY_PROCESSING.md

---

## 📋 Checklist

### Local Setup ✅
- [ ] Clone repository
- [ ] Create venv
- [ ] `pip install -r requirements.txt`
- [ ] Set `STORAGE_BACKEND=local` in `.env`
- [ ] Run: `python -m uvicorn app.main:app --reload`
- [ ] Test: Register + Upload

### HuggingFace Spaces Setup
- [ ] Create account on huggingface.co
- [ ] Create new Space (Public)
- [ ] Link this git repo
- [ ] Set `STORAGE_BACKEND=huggingface` in .env
- [ ] Deploy
- [ ] Test: Visit space URL, register + upload

### Zenodo Setup
- [ ] Create account at zenodo.org or sandbox.zenodo.org
- [ ] Go to Settings → Personal access tokens
- [ ] Create token with `deposit:write` + `deposit:actions` scopes
- [ ] Copy token
- [ ] Set `STORAGE_BACKEND=zenodo` in `.env`
- [ ] Set `ZENODO_API_TOKEN=your_token` in `.env`
- [ ] Set `ZENODO_SANDBOX_MODE=true` (for testing) or `false` (production)
- [ ] Restart backend
- [ ] Test: Register + Upload → Check public_url

---

## 🔍 Troubleshooting

### "Zenodo API token not configured"
**Solution:** Set `ZENODO_API_TOKEN` in `.env` and restart backend

### "Zenodo connection failed"
**Check:**
- Token is valid (not expired)
- Using correct scopes: `deposit:write` + `deposit:actions`
- `ZENODO_SANDBOX_MODE` matches your account (sandbox vs production)

### Files not uploading locally
**Check:**
- `./uploads/` directory exists and is writable
- File is `.fits`, `.fit`, or `.fts` extension
- File is < 500 MB
- User is authenticated (valid JWT token)

### HuggingFace not auto-detecting
**Check:**
- Deployed on actual HF Space (not local)
- `GRADIO_TEMP_DIR` environment variable is set
- Backend will auto-switch to `huggingface`

---

## 💡 Best Practices

1. **Use LOCAL for development**
   - Fastest feedback loop
   - No internet dependency
   - Easy to debug

2. **Use HUGGINGFACE for sharing MVP**
   - Free hosting
   - One-click deploy from GitHub
   - Works immediately

3. **Use ZENODO for production**
   - Permanent URLs
   - Academic citation support
   - Professional archive
   - Files won't disappear

4. **Never commit real tokens to git**
   - Always use `.env` file
   - Add to `.gitignore`
   - Use environment variables in CI/CD

---

## 📚 Next Steps

1. Choose your backend based on needs
2. Set up credentials (if Zenodo)
3. Update `.env` file
4. Restart backend
5. Test upload
6. Celebrate! 🎉

Questions? Check [ASTRONOMY_PROCESSING.md](ASTRONOMY_PROCESSING.md) for file access patterns in each backend.
