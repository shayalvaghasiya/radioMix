import random
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from database import models, models as db_models
from config.settings import settings

def query_songs(session: Session, genre: Optional[str] = None, artist: Optional[str] = None) -> List[models.Song]:
    """Queries songs based on filters."""
    query = session.query(models.Song)
    filters = []
    if genre:
        filters.append(models.Song.genre == genre)
    if artist:
        filters.append(models.Song.artist == artist)
    
    if filters:
        query = query.filter(and_(*filters))
        
    return query.all()

def get_recently_played_ids(session: Session) -> List[int]:
    """Gets IDs of songs played within the configured number of days."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=settings.recent_playlist_days)
    
    recent_items = session.query(models.PlaylistItem.song_id)\
        .join(models.Playlist)\
        .filter(models.Playlist.created_at >= cutoff)\
        .distinct().all()
        
    return [item[0] for item in recent_items]

def save_playlist(session: Session, songs: List[models.Song]) -> int:
    """Saves a new playlist and updates song metadata."""
    playlist = models.Playlist()
    session.add(playlist)
    
    for pos, song in enumerate(songs):
        item = models.PlaylistItem(playlist=playlist, song_id=song.id, position=pos)
        session.add(item)
        
        # Update song play count and last played time
        song.play_count = (song.play_count or 0) + 1
        song.last_played_at = datetime.datetime.utcnow()

    session.commit()
    return playlist.id

def _is_valid_order(playlist: List[models.Song]) -> bool:
    """Checks if a playlist has consecutive artists or genres."""
    for i in range(1, len(playlist)):
        if playlist[i].artist and playlist[i].artist == playlist[i-1].artist:
            return False
        if playlist[i].genre and playlist[i].genre == playlist[i-1].genre:
            return False
    return True

def _find_next_song(pools, search_order, last_song):
    """Helper to find a non-clashing song from pools based on search order."""
    for category in search_order:
        candidate_pool = pools.get(category, [])
        for i, candidate in enumerate(candidate_pool):
            if last_song is None or (
                (not candidate.artist or candidate.artist != last_song.artist) and
                (not candidate.genre or candidate.genre != last_song.genre)
            ):
                return candidate_pool.pop(i)
    # Fallback: if no non-clashing song is found, just grab the first available
    for category in search_order:
        if pools.get(category):
            return pools[category].pop(0)
    return None

def generate_smart_playlist(
    songs: List[models.Song], 
    count: int, 
    exclude_ids: List[int] = None
) -> List[models.Song]:
    """Generates a playlist respecting rotation categories and no consecutive artists/genres."""
    if exclude_ids is None:
        exclude_ids = []

    pool = [s for s in songs if s.id not in exclude_ids]
    if not pool:
        # If exclusions make the pool empty, fall back to the full list
        pool = list(songs) 

    # 1. Separate songs by rotation category
    pools = {
        db_models.Rotation.A: [],
        db_models.Rotation.B: [],
        db_models.Rotation.C: [],
    }
    for song in pool:
        pools[song.rotation].append(song)
    
    # Shuffle each category pool
    for p in pools.values():
        random.shuffle(p)

    # 2. Get rotation pattern from config
    try:
        rotation_pattern = [db_models.Rotation(r) for r in settings.rotation_pattern]
        if not rotation_pattern:
            raise ValueError
    except (ValueError, TypeError):
        # Fallback to a default pattern if config is bad
        rotation_pattern = [db_models.Rotation.A, db_models.Rotation.B, db_models.Rotation.C]

    # 3. Build playlist
    result = []
    last_song = None
    
    # Fallback search order for each category
    fallback_order = {
        db_models.Rotation.A: [db_models.Rotation.A, db_models.Rotation.B, db_models.Rotation.C],
        db_models.Rotation.B: [db_models.Rotation.B, db_models.Rotation.C, db_models.Rotation.A],
        db_models.Rotation.C: [db_models.Rotation.C, db_models.Rotation.B, db_models.Rotation.A],
    }

    for i in range(count):
        target_category = rotation_pattern[i % len(rotation_pattern)]
        search_order = fallback_order.get(target_category, list(db_models.Rotation))
        
        picked_song = _find_next_song(pools, search_order, last_song)
        
        if picked_song:
            result.append(picked_song)
            last_song = picked_song
        else:
            # No songs left in any pool
            break

    return result