import os
from mutagen import File as MutagenFile
from typing import Dict, Optional

def read_metadata(path: str) -> Dict[str, Optional[str | int]]:
    """Reads metadata from an audio file, including duration."""
    data = {
        'title': os.path.splitext(os.path.basename(path))[0],
        'artist': None,
        'album': None,
        'genre': None,
        'duration': None
    }
    try:
        audio = MutagenFile(path, easy=True)
        if audio is None: # Fallback for files without easy tags
            audio_raw = MutagenFile(path)
            if audio_raw and audio_raw.info:
                data['duration'] = int(audio_raw.info.length)
            return data

        if audio.info:
            data['duration'] = int(audio.info.length)

        for key in ('title', 'artist', 'album', 'genre'):
            if key in audio and audio[key]:
                data[key] = str(audio[key][0])
    except Exception:
        # If metadata reading fails, we still have the filename as title
        pass

    return data