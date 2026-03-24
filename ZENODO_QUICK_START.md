# 🚀 AstroSense Multi-Backend Storage - QUICK START

## ⚡ 3 Steps to Enable Zenodo + HuggingFace

### Step 1: Get Your Zenodo Token (5 minutes)

1. Go to: **https://sandbox.zenodo.org/account/settings/applications/tokens/new**
2. Create new token named "AstroSense"
3. **Select BOTH scopes:**
   - ✅ `deposit:write`
   - ✅ `deposit:actions`
4. Click Create and **copy the token**

**Keep this token safe!** You'll need it in Step 2.

---

### Step 2: Update `.env` File

Edit `D:\AstroSense\server\.env`:

```env
# [JWT AUTHENTICATION]: JWT Configuration
SECRET_KEY=astrosense-dev-secret-key-change-in-production-min-32-chars-!!!
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# [PER-USER STORAGE]: Storage Backend Configuration
# Options: "local", "huggingface", "zenodo"
STORAGE_BACKEND=zenodo

# Local filesystem storage (if STORAGE_BACKEND=local)
LOCAL_STORAGE_PATH=./uploads

# HuggingFace Spaces Configuration (auto-detected via GRADIO_TEMP_DIR)
# No configuration needed!

# Zenodo Configuration (PASTE YOUR TOKEN HERE!)
ZENODO_API_TOKEN=YOUR_TOKEN_HERE
ZENODO_SANDBOX_MODE=true
```

**Replace `YOUR_TOKEN_HERE`** with the token from Step 1

---

### Step 3: Restart Backend & Test

```powershell
cd D:\AstroSense\server

# Backend will auto-reload
# (Ctrl+C then restart if needed)
```

**Test in browser:**
1. Visit http://localhost:5173 (frontend already running)
2. Register new account
3. Upload a `.fits` file
4. ✅ Check response → should show `"backend": "zenodo"`
5. Click `"public_url"` link → file live on Zenodo! 🎉

---

## 🎯 What's Available NOW

| Feature | Local | HF Spaces | Zenodo |
|---------|-------|-----------|--------|
| Upload FITS | ✅ | ✅ | ✅ |
| per-user isolation | ✅ | ✅ | ✅ |
| Permanent URL | ❌ | ❌ | ✅ |
| Public archive | ❌ | ❌ | ✅ |
| List files | ✅ | ✅ | ❌ |
| Delete files | ✅ | ✅ | ❌ |
| **Setup effort** | **None** | **None** | **5 min** |

---

## 📖 Which Backend to Use?

- **LOCAL** → Testing, development, Windows local
- **HUGGINGFACE** → Deploy on HF Spaces (free hosting!)
- **ZENODO** → Production, permanent archive, citations

You can **switch anytime** - just change `.env` and restart!

---

## 🔐 Environment Variables Explained

```env
# Required: Choose your backend
STORAGE_BACKEND=zenodo

# Only needed if STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./uploads

# Only needed if STORAGE_BACKEND=zenodo
ZENODO_API_TOKEN=your_token_from_step_1

# true = sandbox.zenodo.org (testing)
# false = zenodo.org (production, permanent!)
ZENODO_SANDBOX_MODE=true
```

---

## ✅ Verification Checklist

- [ ] Token created on Zenodo with BOTH scopes
- [ ] ZENODO_API_TOKEN pasted in `.env`
- [ ] STORAGE_BACKEND set to `zenodo`
- [ ] Backend running with Ctrl+C → restart
- [ ] User registered successfully
- [ ] FITS file uploads successfully
- [ ] Response shows `"backend": "zenodo"`
- [ ] public_url link is clickable and shows file on Zenodo

---

## 🎓 File Locations by Backend

### Local Backend
```
./uploads/{user_id}/{timestamp}_{filename}
Example: ./uploads/abc123/20260324_154437_spectrum.fits
```

### HuggingFace Backend
```
{GRADIO_TEMP_DIR}/astrosense_uploads/{user_id}/{timestamp}_{filename}
Example: /tmp/xyz/astrosense_uploads/abc123/20260324_154437_spectrum.fits
```

### Zenodo Backend
```
https://sandbox.zenodo.org/record/{record_id}
Example: https://sandbox.zenodo.org/record/12345678
```

---

## 🚀 Next: Try All Three Backends

**Test Progression:**

1. **Local (default)**
   ```env
   STORAGE_BACKEND=local
   ```
   → Upload → Check `./uploads/` folder

2. **HuggingFace** (for sharing)
   ```env
   STORAGE_BACKEND=huggingface
   # Auto-detected automatically, no config needed!
   ```
   → Upload → Works on HF Spaces

3. **Zenodo** (for archiving)
   ```env
   STORAGE_BACKEND=zenodo
   ZENODO_API_TOKEN=...
   ```
   → Upload → File on Zenodo.org! 📚

---

## 💡 Pro Tips

- **Sandbox testing first:** Use `ZENODO_SANDBOX_MODE=true` before going production
- **Keep token secret:** Never share `ZENODO_API_TOKEN` on GitHub
- **Switch backends easily:** Just edit `.env` and restart
- **Files don't mix:** Each backend has separate storage
- **Zenodo is permanent:** Once published, you can't delete files (they stay archived)

---

## 🆘 Need Help?

**Zenodo token not working?**
- Check scopes: Must have BOTH `deposit:write` AND `deposit:actions`
- Try sandbox first: `ZENODO_SANDBOX_MODE=true`
- Token expires: Create a new one if old one doesn't work

**Files not uploading?**
- Check file extension: Must be `.fits`, `.fit`, or `.fts`
- Check file size: Max 500 MB
- Restart backend and try again

**Can't see files after upload?**
- Check console output: Should print `[STORAGE] backend: ZENODO`
- Zenodo intentionally doesn't list files (archive design)
- Use `public_url` from upload response to access

---

Ready? Let's go! 🚀

See [SETUP_MULTI_STORAGE.md](SETUP_MULTI_STORAGE.md) for detailed documentation.
