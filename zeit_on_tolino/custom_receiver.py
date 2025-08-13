import logging
import os
import time
from pathlib import Path
from typing import Tuple
import requests
from zeit_on_tolino.env_vars import EnvVars, MissingEnvironmentVariable


TOLINO_CLOUD_LOGIN_URL = os.environ[EnvVars.CUSTOM_URL]

log = logging.getLogger(__name__)

def upload_epub(file_path: Path, server_url=os.environ[EnvVars.CUSTOM_URL]):
    """Simple function to upload an EPUB file."""
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Prepare the upload
    upload_url = f"{server_url}"
    
    print(f"Uploading {file_path} to {server_url}...")
    
    # Upload the file
    with open(file_path, 'rb') as f:
        files = {'epub': f}
        response = requests.post(upload_url, files=files)
    
    # Check response
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Uploaded as: {result['filename']}")
        return result
    else:
        print(f"❌ Upload failed: {response.status_code} - {response.text}")
        return None