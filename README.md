# Radio Mix - Playlist Automation

A production-grade desktop application for Radio Song Playlist Automation, designed for managing music libraries and generating smart playlists with rotation rules.

## Features

*   **Song Library Management**: recursive folder scanning, duplicate detection, and metadata extraction (ID3 tags).
*   **Smart Playlist Generator**: Rules-based generation (A/B/C rotation), preventing consecutive artists or genres.
*   **Library Interface**: Search, filter, edit metadata, and audio preview (Play/Stop).
*   **Export Options**: Support for `.m3u`, `.csv`, and user-defined custom text formats.
*   **Scheduler**: Automate playlist generation and export on a daily or weekly basis.
*   **Drag-and-Drop**: Reorder songs in the playlist preview before exporting.
*   **Persistence**: SQLite database with SQLAlchemy ORM.

## Project Structure

```text
RadioMix/
├── config/             # Configuration settings and Pydantic models
├── database/           # Database models and session connection logic
├── services/           # Business logic (Library, Playlist, Export, Scheduler)
├── ui/                 # PySide6 Widgets and Dialogs (Main Window, Library View, Settings)
├── utils/              # Helper utilities (File scanning, Metadata reading, Logging)
├── tests/              # Unit tests (Pytest)
├── logs/               # Application log files
├── radio_mix.py        # Main application entry point
└── requirements.txt    # Project dependencies
```

## Installation

1.  **Prerequisites**: Ensure Python 3.11+ is installed.

2.  **Install Dependencies**:
    Open a terminal in the project directory and run:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Running the Application

To start the application:
```bash
python radio_mix.py
```

### Initial Setup
1.  Go to **File > Settings**.
2.  Under **Music Library Folders**, click "Add Folder" to select directories containing your music files.
3.  Set the **Playlist Export Path** to your desired output location.
4.  (Optional) Configure **Automatic Scheduler** settings.
5.  Click **Save**.

### Importing Music
*   On the main screen, click **Rescan Libraries** to scan the configured folders and populate the database.
*   Go to the **Library Manager** tab to browse, search, edit, or preview songs.

### Generating Playlists
1.  On the **Playlist Generator** tab, select optional filters (Genre/Artist).
2.  Set the desired **Songs count**.
3.  Click **Generate Playlist**.
4.  The result appears in the preview table. You can drag and drop rows to reorder songs manually.
5.  Click **Export .m3u**, **Export .csv**, or **Export Custom** to save the playlist.

## Development & Testing

To run the automated test suite:
```bash
pytest
```

To package the application as a standalone executable:
```bash
pyinstaller --name RadioPlaylistApp --onefile --noconsole radio_mix.py
```