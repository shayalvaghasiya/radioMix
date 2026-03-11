import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, Song
from services import library_service

# Setup in-memory database
@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@patch('utils.file_utils.scan_folder')
@patch('utils.metadata_reader.read_metadata')
@patch('os.path.isdir', return_value=True)
def test_import_songs(mock_isdir, mock_read_metadata, mock_scan_folder, session):
    # Mock file system scan
    mock_scan_folder.return_value = ['/music/song1.mp3', '/music/song2.mp3']
    
    # Mock metadata reading
    def metadata_side_effect(path):
        if path == '/music/song1.mp3':
            return {'title': 'Song 1', 'artist': 'Artist A', 'duration': 180}
        else:
            return {'title': 'Song 2', 'artist': 'Artist B', 'duration': 200}
    mock_read_metadata.side_effect = metadata_side_effect

    # Run import
    count = library_service.import_paths(session, ['/music'])
    
    assert count == 2
    
    # Verify database content
    songs = session.query(Song).all()
    assert len(songs) == 2
    assert songs[0].path == '/music/song1.mp3'
    assert songs[0].title == 'Song 1'
    assert songs[1].artist == 'Artist B'

def test_import_duplicates(session):
    # Add existing song
    existing = Song(path='/music/exist.mp3', title='Existing')
    session.add(existing)
    session.commit()

    with patch('utils.file_utils.scan_folder', return_value=['/music/exist.mp3']):
        count = library_service.import_paths(session, ['/music'])
        assert count == 0  # Should skip duplicate