"""
DEPRECATED: Firebase Configuration

This file is no longer used. The project now uses HuggingFace Spaces session storage
for temporary per-user file storage instead of Firebase Cloud Storage.

For historical reference, this module previously handled Firebase Admin SDK initialization.

[PER-USER STORAGE]: Files are now stored in /tmp/astrosense_uploads/{user_id}/
[ASTRONOMY PROCESSING PLACEHOLDER]: Processing pipeline accesses files from session storage
"""

# This file is kept for backwards compatibility but all functionality has moved to storage.py
# No Firebase imports or initialization is performed here.
