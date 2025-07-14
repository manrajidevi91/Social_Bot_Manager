import os
import zipfile
import shutil

ALLOWED_EXTENSIONS = {'.py', '.txt', '.md', '.json', '.png', '.jpg', '.jpeg'}


def secure_extract(zip_path: str, dest: str) -> None:
    """Extract zip while preventing directory traversal."""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.infolist():
            name = member.filename
            if os.path.isabs(name) or '..' in name:
                raise ValueError('Illegal file path in zip')
            ext = os.path.splitext(name)[1].lower()
            if ext and ext not in ALLOWED_EXTENSIONS:
                raise ValueError(f'File type not allowed: {ext}')
        zf.extractall(dest)
