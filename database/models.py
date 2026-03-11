from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Enum
)
from sqlalchemy.orm import relationship, declarative_base
import datetime
import enum

Base = declarative_base()

class Rotation(enum.Enum):
    A = "A" # High
    B = "B" # Medium
    C = "C" # Low

class Song(Base):
    __tablename__ = 'songs'
    id = Column(Integer, primary_key=True)
    path = Column(String, unique=True, nullable=False)
    title = Column(String)
    artist = Column(String, index=True)
    album = Column(String)
    genre = Column(String, index=True)
    duration = Column(Integer) # in seconds
    added_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_played_at = Column(DateTime)
    play_count = Column(Integer, default=0)
    rotation = Column(Enum(Rotation), default=Rotation.C)

class Playlist(Base):
    __tablename__ = 'playlists'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    items = relationship("PlaylistItem", back_populates="playlist", cascade="all, delete-orphan")

class PlaylistItem(Base):
    __tablename__ = 'playlist_items'
    id = Column(Integer, primary_key=True)
    playlist_id = Column(Integer, ForeignKey('playlists.id'), nullable=False)
    song_id = Column(Integer, ForeignKey('songs.id'), nullable=False)
    position = Column(Integer, nullable=False)

    playlist = relationship("Playlist", back_populates="items")
    song = relationship("Song")