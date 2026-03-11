# d:\PROJECTS\RadioMix\config\settings.py
import json
import os
from pydantic import BaseModel
from platformdirs import user_config_dir, user_data_dir, user_log_dir, user_music_dir

APP_NAME = "RadioMix"
APP_AUTHOR = "RadioMix"

class AppSettings(BaseModel):
    # Core application paths managed by platformdirs
    config_path: str = os.path.join(user_config_dir(APP_NAME, APP_AUTHOR), 'settings.json')
    database_url: str = f"sqlite:///{os.path.join(user_data_dir(APP_NAME, APP_AUTHOR), 'library.db')}"
    log_path: str = os.path.join(user_log_dir(APP_NAME, APP_AUTHOR), 'app.log')
    
    # User-configurable paths
    music_library_paths: list[str] = []
    playlist_export_path: str = user_music_dir() # Default to the user's Music folder

    # Playlist settings
    recent_playlist_days: int = 30

    # Scheduler settings
    scheduler_enabled: bool = False
    scheduler_frequency: str = "daily" # 'daily' or 'weekly'
    scheduler_day_of_week: int = 0 # 0=Monday, 6=Sunday
    scheduler_time: str = "10:00"
    scheduler_playlist_count: int = 50
    scheduler_export_format: str = "m3u"

    # Custom Export
    custom_export_format: str = "[Artist] - [Title]"

    def save(self):
        """Saves the current settings to the config file."""
        # Ensure the directory for the config file exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            # Use model_dump() for Pydantic v2+
            json.dump(self.model_dump(), f, indent=4)

def load_settings() -> AppSettings:
    """Loads settings from the user's config directory."""
    config_file_path = os.path.join(user_config_dir(APP_NAME, APP_AUTHOR), 'settings.json')
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, 'r') as f:
                config_data = json.load(f)
                # Ensure the loaded settings object knows its own path
                config_data['config_path'] = config_file_path
                return AppSettings(**config_data)
        except (json.JSONDecodeError, TypeError):
            # If file is corrupt or invalid, fall back to defaults
            pass
    # Return default settings if no file exists or it's invalid
    return AppSettings(config_path=config_file_path)

# Global settings instance
settings = load_settings()
