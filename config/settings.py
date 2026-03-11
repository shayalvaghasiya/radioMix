import json
from pydantic import BaseModel, Field
from typing import List

class AppSettings(BaseModel):
    database_url: str = "sqlite:///library.db"
    music_library_paths: List[str] = Field(default_factory=list)
    supported_formats: List[str] = Field(default_factory=lambda: ['.mp3', '.wav', '.flac', '.ogg', '.m4a'])
    playlist_export_path: str = "playlists"
    recent_playlist_days: int = 15
    rotation_pattern: List[str] = Field(default_factory=lambda: ["A", "B", "A", "C", "A", "B"])
    log_file: str = "logs/app.log"
    log_level: str = "INFO"
    scheduler_enabled: bool = False
    scheduler_time: str = "08:00"
    scheduler_playlist_count: int = 20
    scheduler_export_format: str = "m3u"
    custom_export_format: str = "[Artist] - [Title]"
    scheduler_frequency: str = "daily"  # 'daily' or 'weekly'
    scheduler_day_of_week: int = 0  # 0=Monday, 6=Sunday

    def save(self, path: str = "config.json"):
        """Saves the current settings to a JSON file."""
        with open(path, 'w') as f:
            # Use model_dump() which is the Pydantic v2 equivalent of dict()
            json.dump(self.model_dump(), f, indent=2)

def load_settings(path: str = "config.json") -> AppSettings:
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return AppSettings(**data)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is invalid, create one with defaults
        default_settings = AppSettings()
        default_settings.save(path)
        return default_settings

settings = load_settings()