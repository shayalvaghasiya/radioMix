import os
import pytest
from database.models import Song
from services import export_service

@pytest.fixture
def sample_playlist():
    return [
        Song(title="Title 1", artist="Artist 1", duration=120, path="/path/song1.mp3"),
        Song(title="Title 2", artist="Artist 2", duration=180, path="/path/song2.mp3"),
    ]

def test_export_m3u(sample_playlist, tmp_path):
    output_file = tmp_path / "playlist.m3u"
    export_service.to_m3u(sample_playlist, str(output_file))
    
    assert output_file.exists()
    content = output_file.read_text(encoding='utf-8')
    
    lines = content.strip().split('\n')
    assert lines[0] == "#EXTM3U"
    assert "#EXTINF:120,Artist 1 - Title 1" in lines[1]
    assert "/path/song1.mp3" in lines[2]

def test_export_csv(sample_playlist, tmp_path):
    output_file = tmp_path / "playlist.csv"
    export_service.to_csv(sample_playlist, str(output_file))
    
    assert output_file.exists()
    content = output_file.read_text(encoding='utf-8')
    
    lines = content.strip().split('\n')
    # Header
    assert "position,title,artist,genre,duration,path" in lines[0]
    # Data
    assert "1,Title 1,Artist 1,,120,/path/song1.mp3" in lines[1]

def test_export_custom(sample_playlist, tmp_path):
    output_file = tmp_path / "playlist.txt"
    template = "[Artist] - [Title] ([Duration])"
    export_service.to_custom_text(sample_playlist, str(output_file), template)
    
    assert output_file.exists()
    content = output_file.read_text(encoding='utf-8')
    
    lines = content.strip().split('\n')
    # Duration 120s -> 02:00
    assert lines[0] == "Artist 1 - Title 1 (02:00)"
    # Duration 180s -> 03:00
    assert lines[1] == "Artist 2 - Title 2 (03:00)"

def test_export_custom_missing_fields(tmp_path):
    song = Song(title="Only Title", path="/p.mp3") # No artist
    output_file = tmp_path / "missing.txt"
    export_service.to_custom_text([song], str(output_file), "[Artist] - [Title]")
    
    content = output_file.read_text(encoding='utf-8').strip()
    # Should handle None gracefully (e.g. empty string or None string representation)
    assert content == "None - Only Title"