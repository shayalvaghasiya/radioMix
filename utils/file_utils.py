import os
from typing import List
from config.settings import settings

def is_audio_file(path: str) -> bool:
    _, ext = os.path.splitext(path)
    return ext.lower() in settings.supported_formats

def scan_folder(folder: str) -> List[str]:
    found = []
    for root, _, files in os.walk(folder):
        for f in files:
            path = os.path.join(root, f)
            if is_audio_file(path):
                found.append(path)
    return found