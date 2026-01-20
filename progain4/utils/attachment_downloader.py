"""
Utility for downloading attachments from Firebase Storage
"""
import os
import tempfile
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

def download_attachment(url: str, filename: str) -> Optional[str]:
    """
    Download an attachment from a public URL to a temporary file.
    
    Args:
        url: Public URL of the file
        filename: Original filename (used for extension)
        
    Returns: 
        Path to downloaded temp file, or None if failed
    """
    try:
        # Get file extension
        _, ext = os.path.splitext(filename)
        
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        temp_path = temp_file.name
        temp_file.close()
        
        # Download file
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Save to temp file
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Downloaded attachment: {filename} → {temp_path}")
        return temp_path
        
    except Exception as e:
        logger. error(f"Error downloading attachment {filename}: {e}")
        return None