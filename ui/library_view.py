import logging
import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, 
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QMenu, QMessageBox,
    QProgressDialog, QFileDialog
)
from PySide6.QtCore import Qt, QUrl, Signal, QThreadPool, QRunnable, QObject
from PySide6.QtGui import QDesktopServices
from database.db import get_session
from services import library_service
from .edit_dialog import EditSongDialog

logger = logging.getLogger(__name__)

class LoaderSignals(QObject):
    finished = Signal(list)
    error = Signal(str)

class LibraryLoader(QRunnable):
    def __init__(self, query, artist, genre):
        super().__init__()
        self.query = query
        self.artist = artist
        self.genre = genre
        self.signals = LoaderSignals()

    def run(self):
        session = get_session()
        data = []
        try:
            songs = library_service.search_songs(session, self.query, self.artist, self.genre)
            # Extract data to simple dicts to avoid session/thread issues
            for s in songs:
                # Paths in DB are now Windows format
                data.append({
                    'id': str(s.id),
                    'path': s.path,
                    'display_path': s.path,
                    'title': s.title or "",
                    'artist': s.artist or "",
                    'album': s.album or "",
                    'genre': s.genre or "",
                    'rotation': s.rotation.value if s.rotation else "-"
                })
            self.signals.finished.emit(data)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            session.close()

class LibraryView(QWidget):
    paths_dropped = Signal(list)
    import_requested = Signal(str)
    rescan_requested = Signal()
    clean_requested = Signal()
    clear_all_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.thread_pool = QThreadPool()
        self.progress = None

        self._init_ui()
        self.reload_library()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Filter Controls
        filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search title, artist, album...")
        self.search_input.returnPressed.connect(self.reload_library)
        filter_layout.addWidget(self.search_input)

        self.artist_cb = QComboBox()
        self.artist_cb.addItem("All")
        self.artist_cb.currentIndexChanged.connect(self.reload_library)
        filter_layout.addWidget(self.artist_cb)

        self.genre_cb = QComboBox()
        self.genre_cb.addItem("All")
        self.genre_cb.currentIndexChanged.connect(self.reload_library)
        filter_layout.addWidget(self.genre_cb)

        filter_layout.addStretch()

        self.open_btn = QPushButton("▶ Open File")
        self.open_btn.clicked.connect(self.open_selected_song)
        filter_layout.addWidget(self.open_btn)

        # Management buttons
        mgmt_layout = QHBoxLayout()
        self.import_btn = QPushButton("Import Folder...")
        self.import_btn.clicked.connect(self.import_folder)
        self.rescan_btn = QPushButton("Rescan All Configured Folders")
        self.rescan_btn.clicked.connect(self.rescan_requested.emit)
        self.clean_btn = QPushButton("Remove Missing Files")
        self.clean_btn.setToolTip("Scans for and removes songs from the database if the file is missing.")
        self.clean_btn.clicked.connect(self.clean_requested.emit)
        self.clear_all_btn = QPushButton("Clear Entire Library")
        self.clear_all_btn.setToolTip("Deletes all songs and playlists from the database. This cannot be undone.")
        self.clear_all_btn.clicked.connect(self.clear_all_requested.emit)
        mgmt_layout.addWidget(self.import_btn)
        mgmt_layout.addWidget(self.rescan_btn)
        mgmt_layout.addWidget(self.clean_btn)
        mgmt_layout.addWidget(self.clear_all_btn)

        layout.addLayout(filter_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Path", "Title", "Artist", "Album", "Genre", "Rot"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.doubleClicked.connect(self.edit_selected_song)
        
        # Hide ID and Path columns
        self.table.setColumnHidden(0, True)
        self.table.setColumnHidden(1, True)
        
        layout.addWidget(self.table)
        layout.addLayout(mgmt_layout)

    def refresh_data(self):
        # Reload filter combos
        session = get_session()
        try:
            artists = library_service.get_distinct(session, 'artist')
            genres = library_service.get_distinct(session, 'genre')
            
            self.artist_cb.blockSignals(True)
            self.genre_cb.blockSignals(True)
            
            curr_artist = self.artist_cb.currentText()
            curr_genre = self.genre_cb.currentText()
            
            self.artist_cb.clear()
            self.artist_cb.addItem("All")
            self.artist_cb.addItems(artists)
            
            self.genre_cb.clear()
            self.genre_cb.addItem("All")
            self.genre_cb.addItems(genres)

            self.artist_cb.setCurrentText(curr_artist)
            self.genre_cb.setCurrentText(curr_genre)
            
            self.artist_cb.blockSignals(False)
            self.genre_cb.blockSignals(False)
        finally:
            session.close()
        self.reload_library()

    def reload_library(self):
        self.setCursor(Qt.BusyCursor)

        query = self.search_input.text()
        artist = self.artist_cb.currentText()
        genre = self.genre_cb.currentText()

        loader = LibraryLoader(query, artist, genre)
        loader.signals.finished.connect(self.on_load_finished)
        loader.signals.error.connect(self.on_load_error)
        self.thread_pool.start(loader)

    def on_load_finished(self, songs_data):
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False) 
        for r, song in enumerate(songs_data):
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(song['id']))
            
            path_item = QTableWidgetItem(song['display_path'])
            path_item.setData(Qt.UserRole, song['path'])
            self.table.setItem(r, 1, path_item)
            
            self.table.setItem(r, 2, QTableWidgetItem(song['title']))
            self.table.setItem(r, 3, QTableWidgetItem(song['artist']))
            self.table.setItem(r, 4, QTableWidgetItem(song['album']))
            self.table.setItem(r, 5, QTableWidgetItem(song['genre']))
            self.table.setItem(r, 6, QTableWidgetItem(song['rotation']))
        self.table.setSortingEnabled(True)
        
        self.unsetCursor()

    def on_load_error(self, err):
        self.unsetCursor()
        QMessageBox.critical(self, "Error", f"Failed to load library: {err}")

    def open_context_menu(self, position):
        menu = QMenu()
        edit_action = menu.addAction("Edit Song")
        delete_action = menu.addAction("Delete Song")
        action = menu.exec(self.table.viewport().mapToGlobal(position))
        
        if action == edit_action:
            self.edit_selected_song()
        elif action == delete_action:
            self.delete_selected_song()

    def get_selected_id(self):
        row = self.table.currentRow()
        if row < 0: return None
        return int(self.table.item(row, 0).text())

    def get_selected_path(self):
        row = self.table.currentRow()
        if row < 0: return None
        return self.table.item(row, 1).data(Qt.UserRole)

    def edit_selected_song(self):
        sid = self.get_selected_id()
        if not sid: return
        
        session = get_session()
        song = session.query(library_service.models.Song).get(sid)
        dlg = EditSongDialog(song, self)
        if dlg.exec():
            new_data = dlg.get_data()
            library_service.update_song(session, sid, new_data)
            self.reload_library()
        session.close()

    def delete_selected_song(self):
        sid = self.get_selected_id()
        if sid and QMessageBox.question(self, "Confirm Delete", "Delete this song?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            session = get_session()
            library_service.delete_song(session, sid)
            session.close()
            self.reload_library()

    def import_folder(self):
        if self._is_wsl():
            folder = self._open_wsl_folder_dialog()
        else:
            folder = QFileDialog.getExistingDirectory(self, "Select Folder to Import")
        
        if folder:
            self.import_requested.emit(folder)

    def open_selected_song(self):
        path = self.get_selected_path()
        if not path:
            QMessageBox.warning(self, "No Song Selected", "Please select a song from the library to open.")
            return
        
        # Use 'start' command via cmd.exe for robust file opening on Windows, even from WSL.
        # This is more reliable than explorer.exe for launching the default application.
        try:
            # The empty "" is a placeholder for the window title, a quirk of the 'start' command.
            subprocess.run(['cmd.exe', '/c', 'start', '""', path], check=True)
        except Exception as e:
            logger.error(f"Failed to open file via 'start' command: {e}")
            QMessageBox.critical(self, "Error", f"Could not open the file '{path}'.\n\nEnsure you have a default application for this file type.")

    def _is_wsl(self):
        return hasattr(os, 'uname') and 'microsoft' in os.uname().release.lower()

    def _open_wsl_folder_dialog(self):
        """Opens a Windows native folder dialog via PowerShell."""
        try:
            cmd = """
            Add-Type -AssemblyName System.Windows.Forms
            $f = New-Object System.Windows.Forms.FolderBrowserDialog
            $result = $f.ShowDialog()
            if ($result -eq 'OK') { Write-Output $f.SelectedPath }
            """
            # Run PowerShell command
            res = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
            win_path = res.stdout.strip()
            return win_path or None
        except Exception as e:
            logger.error(f"Failed to open Windows dialog: {e}")
        return None

    def dragEnterEvent(self, event):
        # Accept the event if it contains file paths
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        # Get the list of local file paths from the drop event
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls]
        if paths:
            self.paths_dropped.emit(paths)