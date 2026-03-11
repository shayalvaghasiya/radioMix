import logging
import os
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, distinct
from typing import List
from database import models
from utils import metadata_reader, file_utils

logger = logging.getLogger(__name__)

def _to_wsl(path: str) -> str:
    """Converts a Windows path to a WSL path if needed."""
    if ':' in path and '\\' in path:
        drive, tail = path.split(':', 1)
        tail = tail.replace("\\", "/")
        return f"/mnt/{drive.lower()}{tail}"
    return path

def _to_win(path: str) -> str:
    """Converts a WSL path to a Windows path."""
    if path.startswith("/mnt/"):
        parts = path.split('/')
        if len(parts) > 2 and len(parts[2]) == 1:
            drive = parts[2].upper()
            rest = '\\'.join(parts[3:])
            return f"{drive}:\\{rest}"
    return path.replace('/', '\\')

def get_distinct(session: Session, field: str) -> List[str]:
    """Gets distinct non-null values for a given field in the songs table."""
    results = session.query(getattr(models.Song, field)).distinct().filter(
        getattr(models.Song, field).isnot(None)
    ).order_by(getattr(models.Song, field)).all()
    return [r[0] for r in results if r[0]]

def import_paths(session: Session, paths: List[str], prune_missing: bool = False) -> int:
    """
    Scans a list of paths (files or folders), adds all new songs, and commits once.
    """
    all_file_paths = set()
    for path in paths:
        # Paths from settings are likely Windows paths now. Convert to WSL for scanning.
        check_path = _to_wsl(path)
        if os.path.isdir(check_path):
            all_file_paths.update(file_utils.scan_folder(check_path))
        elif os.path.isfile(check_path) and file_utils.is_audio_file(check_path):
            all_file_paths.add(check_path)

    if not all_file_paths:
        logger.info("No new audio files found in the provided paths.")
        # Do not return immediately if pruning is requested, as we might need to remove songs
        if not prune_missing:
            return 0

    count = 0
    for file_path in all_file_paths:
        try:
            # file_path is WSL path here (/mnt/d/...). 
            # Convert to Windows path for DB storage to satisfy "Windows everywhere"
            db_path = _to_win(file_path)
            
            # Check if song with this path already exists
            if session.query(models.Song).filter_by(path=db_path).first():
                continue

            meta = metadata_reader.read_metadata(file_path)
            song = models.Song(
                path=db_path,
                title=meta.get('title'),
                artist=meta.get('artist'),
                album=meta.get('album'),
                genre=meta.get('genre'),
                duration=meta.get('duration')
            )
            session.add(song)
            count += 1
        except Exception as e:
            logger.error(f"Failed to stage song {file_path} for import: {e}")
    
    deleted_count = 0
    if prune_missing:
        all_songs = session.query(models.Song).all()
        for song in all_songs:
            # song.path is Windows format. Convert to WSL to check against scanned paths.
            wsl_path = _to_wsl(song.path)
            if wsl_path not in all_file_paths:
                session.delete(song)
                deleted_count += 1

    if count > 0 or deleted_count > 0:
        session.commit()
        logger.info(f"Import complete. Added {count} new songs. Removed {deleted_count} stale songs.")
    else:
        logger.info("Import complete. All found songs were already in the library.")
        
    return count

def search_songs(session: Session, query: str = None, artist: str = None, genre: str = None) -> List[models.Song]:
    """Searches for songs with filters."""
    q = session.query(models.Song)
    if artist and artist != "All":
        q = q.filter(models.Song.artist == artist)
    if genre and genre != "All":
        q = q.filter(models.Song.genre == genre)
    
    if query:
        search_term = f"%{query}%"
        q = q.filter(or_(
            models.Song.title.ilike(search_term),
            models.Song.artist.ilike(search_term),
            models.Song.album.ilike(search_term)
        ))
    
    return q.order_by(models.Song.artist, models.Song.title).all()

def update_song(session: Session, song_id: int, data: dict):
    """Updates song metadata."""
    song = session.query(models.Song).get(song_id)
    if song:
        for key, value in data.items():
            if hasattr(song, key):
                setattr(song, key, value)
        session.commit()
        return True
    return False

def get_library_stats(session: Session) -> dict:
    """Calculates library statistics."""
    total_songs = session.query(func.count(models.Song.id)).scalar()
    total_artists = session.query(func.count(distinct(models.Song.artist))).scalar()
    total_genres = session.query(func.count(distinct(models.Song.genre))).scalar()
    
    return {
        "total_songs": total_songs or 0,
        "total_artists": total_artists or 0,
        "total_genres": total_genres or 0,
    }

def scan_for_missing_files(session: Session) -> int:
    """Checks all songs in the library and removes entries where the file no longer exists."""
    songs = session.query(models.Song).all()
    missing_count = 0
    
    for song in songs:
        wsl_path = _to_wsl(song.path)
        if not os.path.exists(wsl_path):
            logger.warning(f"File not found (path={wsl_path}), removing from library: {song.path}")
            session.delete(song)
            missing_count += 1
            
    if missing_count > 0:
        session.commit()
        
    return missing_count


def clear_all_songs(session: Session) -> int:
    """Deletes all songs and playlists from the database."""
    try:
        song_count = session.query(models.Song).count()
        
        # Order of deletion matters if there were foreign key constraints enforced
        session.query(models.PlaylistItem).delete(synchronize_session=False)
        session.query(models.Playlist).delete(synchronize_session=False)
        session.query(models.Song).delete(synchronize_session=False)
        
        session.commit()
        logger.info(f"Cleared entire library, deleting {song_count} songs.")
        return song_count
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to clear library: {e}", exc_info=True)
        raise

def delete_song(session: Session, song_id: int):
    """Deletes a song from the library."""
    song = session.query(models.Song).get(song_id)
    if song:
        session.delete(song)
        session.commit()
        return True
    return False