import os
import datetime
import logging
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout,
    QFileDialog, QComboBox, QSpinBox, QTableWidget, QTableWidgetItem, QMessageBox,
    QProgressDialog, QTabWidget, QAbstractItemView, QGroupBox, QMenuBar
)
from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, Signal, QTimer
from PySide6.QtGui import QAction

from database.db import get_session
from services import library_service, playlist_service, export_service
from services.scheduler_service import SchedulerService
from .library_view import LibraryView
from .settings_dialog import SettingsDialog
from .about_dialog import AboutDialog
from config.settings import settings

logger = logging.getLogger(__name__)

# Worker for background tasks
class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)

class ImportWorker(QRunnable):
    def __init__(self, paths, prune=False):
        super().__init__()
        self.paths = paths
        self.prune = prune
        self.signals = WorkerSignals()

    def run(self):
        try:
            session = get_session()
            count = library_service.import_paths(session, self.paths, prune_missing=self.prune)
            session.close()
            self.signals.finished.emit(count)
        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            self.signals.error.emit(str(e))

class CleanWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()

    def run(self):
        try:
            session = get_session()
            count = library_service.scan_for_missing_files(session)
            session.close()
            self.signals.finished.emit(count)
        except Exception as e:
            logger.error(f"Clean failed: {e}", exc_info=True)
            self.signals.error.emit(str(e))

class ClearAllWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()

    def run(self):
        try:
            session = get_session()
            count = library_service.clear_all_songs(session)
            session.close()
            self.signals.finished.emit(count)
        except Exception as e:
            logger.error(f"Clear All failed: {e}", exc_info=True)
            self.signals.error.emit(str(e))

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Radio Mix - Playlist Generator')
        self.resize(800, 600)
        self.thread_pool = QThreadPool()
        self.current_playlist = []

        self._setup_menu()
        self._setup_tabs()
        
        self.scheduler = SchedulerService(settings)
        self.scheduler.generate_signal.connect(self.run_scheduled_generation)
        self.scheduler.start()

        # Delay heavy initialization until after UI is shown to improve startup speed
        QTimer.singleShot(50, self._startup_initialization)

    def _setup_menu(self):
        self.menu_bar = QMenuBar(self)
        file_menu = self.menu_bar.addMenu("&File")
        
        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = self.menu_bar.addMenu("&Help")
        about_action = QAction("&About...", self)
        about_action.triggered.connect(self.open_about)
        help_menu.addAction(about_action)

    def _setup_tabs(self):
        main_layout = QVBoxLayout(self)
        main_layout.setMenuBar(self.menu_bar)
        self.tabs = QTabWidget()
        
        self.generator_tab = QWidget()
        self._setup_generator_ui(self.generator_tab)
        
        self.library_tab = LibraryView()
        
        self.tabs.addTab(self.generator_tab, "Playlist Generator")
        self.tabs.addTab(self.library_tab, "Library Manager")
        self.library_tab.paths_dropped.connect(self.start_import)

        # Connect signals from LibraryView to MainWindow handlers
        self.library_tab.import_requested.connect(self.import_new_folder)
        self.library_tab.rescan_requested.connect(self.rescan_libraries)
        self.library_tab.clean_requested.connect(self.clean_library)
        self.library_tab.clear_all_requested.connect(self.clear_entire_library)
        
        main_layout.addWidget(self.tabs)

    def _setup_generator_ui(self, parent_widget):
        layout = QVBoxLayout(parent_widget)

        # Stats Panel
        stats_group = QGroupBox("Library Statistics")
        stats_layout = QHBoxLayout()
        self.stats_songs_label = QLabel("Total Songs: 0")
        self.stats_artists_label = QLabel("Total Artists: 0")
        self.stats_genres_label = QLabel("Total Genres: 0")
        stats_layout.addWidget(self.stats_songs_label)
        stats_layout.addWidget(self.stats_artists_label)
        stats_layout.addWidget(self.stats_genres_label)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        layout.addStretch(1) # Add some space

        # Generation controls
        gen_layout = QHBoxLayout()
        gen_layout.addWidget(QLabel('Genre:'))
        self.genre_cb = QComboBox()
        gen_layout.addWidget(self.genre_cb)

        gen_layout.addWidget(QLabel('Artist:'))
        self.artist_cb = QComboBox()
        gen_layout.addWidget(self.artist_cb)

        gen_layout.addWidget(QLabel('Songs count:'))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 1000)
        self.count_spin.setValue(20)
        gen_layout.addWidget(self.count_spin)

        self.generate_btn = QPushButton('Generate Playlist')
        self.generate_btn.clicked.connect(self.generate_playlist)
        gen_layout.addWidget(self.generate_btn)
        gen_layout.addStretch()
        layout.addLayout(gen_layout)

        # Playlist Preview
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['ID', '#', 'Title', 'Artist', 'Genre'])
        self.table.setColumnHidden(0, True) # Hide ID column
        self.table.setColumnWidth(1, 40)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Enable Drag and Drop for reordering
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.table.model().rowsMoved.connect(self.on_playlist_reordered)

        layout.addWidget(self.table)

        # Export Controls
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        self.export_m3u_btn = QPushButton('Export .m3u')
        self.export_m3u_btn.clicked.connect(self.export_m3u)
        export_layout.addWidget(self.export_m3u_btn)

        self.export_csv_btn = QPushButton('Export .csv')
        self.export_csv_btn.clicked.connect(self.export_csv)
        export_layout.addWidget(self.export_csv_btn)

        self.export_custom_btn = QPushButton('Export Custom')
        self.export_custom_btn.clicked.connect(self.export_custom)
        export_layout.addWidget(self.export_custom_btn)
        layout.addLayout(export_layout)

    def reload_filters(self):
        session = get_session()
        try:
            genres = library_service.get_distinct(session, 'genre')
            artists = library_service.get_distinct(session, 'artist')
        finally:
            session.close()

        for combo, items in [(self.genre_cb, genres), (self.artist_cb, artists)]:
            combo.blockSignals(True)
            current_text = combo.currentText()
            combo.clear()
            combo.addItem('All')
            combo.addItems(items)
            combo.setCurrentText(current_text)
            combo.blockSignals(False)

    def _startup_initialization(self):
        """Load stats and filters after window is shown to improve startup perception."""
        self.update_stats()
        self.reload_filters()
        if settings.music_library_paths:
            self.rescan_libraries()

    def open_settings(self):
        """Opens the settings dialog."""
        old_paths = set(settings.music_library_paths)
        dialog = SettingsDialog(settings, self)
        if dialog.exec():
            logger.info("Settings updated and saved.")
            
            # Auto-scan if library paths changed
            new_paths = set(settings.music_library_paths)
            if old_paths != new_paths:
                self.rescan_libraries()

    def open_about(self):
        """Opens the about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    def rescan_libraries(self):
        """Wrapper for starting an import from the configured library folders."""
        if not settings.music_library_paths:
            QMessageBox.warning(self, "No Library Folders", 
                                "Please configure your music library folders in File > Settings.")
            return
        self.start_import(settings.music_library_paths, prune=True)

    def import_new_folder(self, folder_path):
        """Handler for importing a single new folder without pruning."""
        if not folder_path:
            return
        # We start the import with prune=False because it's a one-off addition,
        # not a full sync of the configured libraries.
        self.start_import([folder_path], prune=False)

    def start_import(self, paths: list, prune=False):
        """Shows a progress dialog and starts a background worker to import from the given paths."""
        self.progress_dialog = QProgressDialog("Scanning and importing songs...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()

        worker = ImportWorker(paths, prune=prune)
        worker.signals.finished.connect(self.on_import_finished)
        worker.signals.error.connect(self.on_import_error)
        self.thread_pool.start(worker)

    def on_import_finished(self, count):
        self.progress_dialog.close()
        QMessageBox.information(self, 'Import Complete', f'Imported {count} new songs.')
        self.reload_filters()
        # Refresh the library tab as well
        self.library_tab.refresh_data()
        self.update_stats()

    def on_import_error(self, error_message):
        self.progress_dialog.close()
        QMessageBox.critical(self, 'Import Error', f'An error occurred during import: {error_message}')

    def clean_library(self):
        """Starts a background worker to clean missing files from the library."""
        reply = QMessageBox.question(
            self, "Confirm Clean",
            "This will remove entries for files that no longer exist on disk. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        self.progress_dialog = QProgressDialog("Cleaning library...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()

        worker = CleanWorker()
        worker.signals.finished.connect(self.on_clean_finished)
        worker.signals.error.connect(self.on_clean_error)
        self.thread_pool.start(worker)

    def on_clean_finished(self, count):
        self.progress_dialog.close()
        QMessageBox.information(self, 'Clean Complete', f'Removed {count} missing songs.')
        self.update_stats()
        self.library_tab.refresh_data()

    def on_clean_error(self, error_message):
        self.progress_dialog.close()
        QMessageBox.critical(self, 'Clean Error', f'An error occurred during cleaning: {error_message}')

    def clear_entire_library(self):
        """Handles the request to delete all songs from the database."""
        reply = QMessageBox.warning(
            self, "Confirm Clear Library",
            "This will permanently delete ALL songs, artists, genres, and playlists from the database.\n\n"
            "This action cannot be undone. Are you absolutely sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        self.progress_dialog = QProgressDialog("Clearing entire library...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()

        worker = ClearAllWorker()
        worker.signals.finished.connect(self.on_clear_all_finished)
        worker.signals.error.connect(self.on_clear_all_error)
        self.thread_pool.start(worker)

    def on_clear_all_finished(self, count):
        self.progress_dialog.close()
        QMessageBox.information(self, 'Library Cleared', f'Successfully deleted {count} songs from the library.')
        self.update_stats()
        self.library_tab.refresh_data()
        self.reload_filters()

    def on_clear_all_error(self, error_message):
        self.progress_dialog.close()
        QMessageBox.critical(self, 'Clear Error', f'An error occurred while clearing the library: {error_message}')

    def generate_playlist(self):
        genre = self.genre_cb.currentText() if self.genre_cb.currentText() != 'All' else None
        artist = self.artist_cb.currentText() if self.artist_cb.currentText() != 'All' else None
        count = self.count_spin.value()

        session = get_session()
        try:
            songs = playlist_service.query_songs(session, genre=genre, artist=artist)
            if not songs:
                QMessageBox.warning(self, 'No Songs', 'No songs found for the selected filters.')
                return

            exclude_ids = playlist_service.get_recently_played_ids(session)
            picked_songs = playlist_service.generate_smart_playlist(songs, count, exclude_ids)
            self.current_playlist = picked_songs
            
            playlist_service.save_playlist(session, picked_songs)
            self.show_playlist(picked_songs)
            logger.info(f"Generated playlist with {len(picked_songs)} songs.")
        except Exception as e:
            logger.error(f"Failed to generate playlist: {e}", exc_info=True)
            QMessageBox.critical(self, 'Error', f'Could not generate playlist: {e}')
        finally:
            session.close()

    def run_scheduled_generation(self):
        """Handles the automated generation and export of a playlist."""
        logger.info("Running scheduled playlist generation...")
        session = get_session()
        try:
            # 1. Query all songs (default for scheduler)
            songs = playlist_service.query_songs(session, genre=None, artist=None)
            if not songs:
                logger.warning("Scheduled generation aborted: No songs in library.")
                return

            # 2. Generate
            exclude_ids = playlist_service.get_recently_played_ids(session)
            count = settings.scheduler_playlist_count
            playlist = playlist_service.generate_smart_playlist(songs, count, exclude_ids)
            
            # 3. Save
            playlist_service.save_playlist(session, playlist)
            
            # 4. Export
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
            ext = settings.scheduler_export_format
            filename = f"scheduled_playlist_{timestamp}.{ext}"
            path = os.path.join(settings.playlist_export_path, filename)
            
            if ext == 'csv':
                export_service.to_csv(playlist, path)
            else:
                export_service.to_m3u(playlist, path)
            
            logger.info(f"Scheduled playlist successfully exported to {path}")
            
        except Exception as e:
            logger.error(f"Scheduled generation failed: {e}", exc_info=True)
        finally:
            session.close()

    def on_playlist_reordered(self, parent, start, end, destination, dest_row):
        """Handles the reordering of the playlist in the UI and updates the internal list."""
        # The model moves the row(s) from `start` to `end-1` to `dest_row`.
        # We just need to rebuild our internal list to match the new UI order.
        
        # Block signals to prevent potential recursion if we modify the table
        self.table.blockSignals(True)

        new_playlist_order = []
        # Create a quick lookup map for song objects from the current (pre-move) list
        song_map = {song.id: song for song in self.current_playlist}
        
        for row in range(self.table.rowCount()):
            song_id_item = self.table.item(row, 0)
            if song_id_item:
                song_id = int(song_id_item.text())
                if song_id in song_map:
                    new_playlist_order.append(song_map[song_id])
            
            # Also update the '#' column to reflect the new order
            self.table.item(row, 1).setText(str(row + 1))

        self.current_playlist = new_playlist_order
        logger.info("Playlist reordered by user.")
        
        # Re-enable signals
        self.table.blockSignals(False)

    def show_playlist(self, items):
        self.table.setRowCount(0)
        for i, song in enumerate(items, start=1):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(song.id)))
            self.table.setItem(r, 1, QTableWidgetItem(str(i)))
            self.table.setItem(r, 2, QTableWidgetItem(song.title or os.path.basename(song.path)))
            self.table.setItem(r, 3, QTableWidgetItem(song.artist or ''))
            self.table.setItem(r, 4, QTableWidgetItem(song.genre or ''))

    def update_stats(self):
        """Fetches and displays library statistics."""
        session = get_session()
        try:
            stats = library_service.get_library_stats(session)
            self.stats_songs_label.setText(f"Total Songs: {stats.get('total_songs', 0)}")
            self.stats_artists_label.setText(f"Total Artists: {stats.get('total_artists', 0)}")
            self.stats_genres_label.setText(f"Total Genres: {stats.get('total_genres', 0)}")
            logger.info("Updated library statistics.")
        except Exception as e:
            logger.error(f"Failed to update stats: {e}", exc_info=True)
        finally:
            session.close()

    def _to_win(self, path):
        """Helper to convert WSL path to Windows path for display."""
        if path.startswith("/mnt/"):
            parts = path.split('/')
            if len(parts) > 2 and len(parts[2]) == 1:
                drive = parts[2].upper()
                rest = '\\'.join(parts[3:])
                return f"{drive}:\\{rest}"
        return path.replace('/', '\\')

    def _get_save_path(self, name, ext, file_filter):
        default_path = os.path.join(settings.playlist_export_path, name)
        
        # Use Windows native dialog if on WSL
        if hasattr(os, 'uname') and 'microsoft' in os.uname().release.lower():
            try:
                # Convert Qt filter "Description (*.ext)" to Windows Forms "Description|*.ext"
                ps_filter = "All Files|*.*"
                if "(*" in file_filter:
                    desc, pat = file_filter.rsplit("(", 1)
                    pat = pat.rstrip(")")
                    ps_filter = f"{desc.strip()}|{pat}"

                cmd = f"""
                Add-Type -AssemblyName System.Windows.Forms
                $f = New-Object System.Windows.Forms.SaveFileDialog
                $f.Filter = "{ps_filter}"
                $f.FileName = "{name}"
                if ($f.ShowDialog() -eq 'OK') {{ Write-Output $f.FileName }}
                """
                res = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
                win_path = res.stdout.strip()
                if win_path:
                    # Convert back to WSL path so Python can write to it
                    if ':' in win_path:
                        drive, tail = win_path.split(':', 1)
                        wsl_tail = tail.replace('\\', '/')
                        return f"/mnt/{drive.lower()}{wsl_tail}"
                    return win_path
                return "" # Cancelled
            except Exception as e:
                logger.error(f"WSL Dialog failed: {e}")
                # Fallback to Qt dialog if PowerShell fails
                
        return QFileDialog.getSaveFileName(self, f'Save {ext.upper()}', default_path, file_filter)[0]

    def _export(self, exporter, default_name, ext, file_filter):
        if not self.current_playlist:
            QMessageBox.warning(self, 'No Playlist', 'Generate a playlist first.')
            return
        fname = self._get_save_path(default_name, ext, file_filter)
        if not fname:
            return
        try:
            exporter(self.current_playlist, fname)
            display_name = self._to_win(fname)
            QMessageBox.information(self, 'Export Complete', f'Playlist exported to:\n{display_name}')
            logger.info(f"Exported {ext.upper()} playlist to {fname}")
        except Exception as e:
            logger.error(f"{ext.upper()} export failed: {e}", exc_info=True)
            QMessageBox.critical(self, 'Export Error', f'Could not export {ext.upper()}: {e}')

    def export_m3u(self):
        """Exports M3U with proper headers and path correction (WSL -> Windows)."""
        if not self.current_playlist:
            QMessageBox.warning(self, 'No Playlist', 'Generate a playlist first.')
            return
            
        fname = self._get_save_path('playlist.m3u', 'm3u', 'M3U Files (*.m3u)')
        if not fname:
            return
            
        try:
            with open(fname, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for song in self.current_playlist:
                    # Fix path if on WSL but path is /mnt/d/...
                    path = song.path
                    # Force Windows backslashes for compatibility
                    path = path.replace('/', '\\')

                    artist = song.artist or "Unknown Artist"
                    title = song.title or "Unknown Title"
                    # Duration -1 because we might not have it in DB, letting player detect it
                    f.write(f"#EXTINF:-1,{artist} - {title}\n")
                    f.write(f"{path}\n")
            
            display_name = self._to_win(fname)
            QMessageBox.information(self, 'Export Complete', f'Playlist exported to:\n{display_name}')
            logger.info(f"Exported M3U playlist to {fname}")
        except Exception as e:
            logger.error(f"M3U export failed: {e}", exc_info=True)
            QMessageBox.critical(self, 'Export Error', f'Could not export M3U: {e}')

    def export_csv(self):
        self._export(export_service.to_csv, 'playlist.csv', 'csv', 'CSV Files (*.csv)')

    def export_custom(self):
        if not self.current_playlist:
            QMessageBox.warning(self, 'No Playlist', 'Generate a playlist first.')
            return

        fname, _ = self._get_save_path('playlist.txt', 'txt', 'Text Files (*.txt)')
        if not fname:
            return

        try:
            export_service.to_custom_text(self.current_playlist, fname, settings.custom_export_format)
            display_name = self._to_win(fname)
            QMessageBox.information(self, 'Export Complete', f'Playlist exported to:\n{display_name}')
            logger.info(f"Exported Custom playlist to {fname}")
        except Exception as e:
            logger.error(f"Custom export failed: {e}", exc_info=True)
            QMessageBox.critical(self, 'Export Error', f'Could not export custom format: {e}')