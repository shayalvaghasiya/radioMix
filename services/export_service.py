import csv
import os
import re
from typing import List
from database.models import Song

def to_m3u(playlist: List[Song], path: str):
    """Exports a playlist to an M3U file."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for song in playlist:
            title = song.title or os.path.basename(song.path)
            artist = song.artist or 'Unknown Artist'
            duration = song.duration or -1
            f.write(f"#EXTINF:{duration},{artist} - {title}\n")
            # Force Windows backslashes
            f.write(song.path.replace('/', '\\') + '\n')

def to_csv(playlist: List[Song], path: str):
    """Exports a playlist to a CSV file."""
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['position', 'title', 'artist', 'genre', 'duration', 'path'])
        for i, song in enumerate(playlist, start=1):
            writer.writerow([
                i, song.title, song.artist, song.genre, song.duration, song.path.replace('/', '\\')
            ])

def to_custom_text(playlist: List[Song], path: str, template: str):
    """Exports a playlist to a custom text format based on a template."""
    with open(path, 'w', encoding='utf-8') as f:
        for song in playlist:
            line = template
            # Use a function for replacement to handle None values
            def repl(match):
                key = match.group(1).lower()
                val = getattr(song, key, None)
                if key == 'duration' and val is not None:
                    # Format duration as MM:SS
                    minutes, seconds = divmod(val, 60)
                    return f"{minutes:02d}:{seconds:02d}"
                return str(val) if val is not None else 'None'

            # Find all [Placeholder] occurrences and replace them
            line = re.sub(r'\[(Title|Artist|Album|Genre|Duration)\]', repl, line, flags=re.IGNORECASE)
            f.write(line + '\n')