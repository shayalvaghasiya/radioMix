import os
import subprocess
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QSpinBox,
    QListWidget, QHBoxLayout, QPushButton, QFileDialog, QAbstractItemView,
    QGroupBox, QCheckBox, QTimeEdit, QComboBox, QLabel, QMessageBox
)
from PySide6.QtCore import QTime
from config.settings import AppSettings
from services import library_service
from database.db import get_session

class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.settings = settings
        self.resize(500, 500)

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Library Paths
        self.library_paths_list = QListWidget()
        self.library_paths_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        library_buttons_layout = QHBoxLayout()
        add_folder_btn = QPushButton("Add Folder")
        add_folder_btn.clicked.connect(self.add_library_folder)
        remove_folder_btn = QPushButton("Remove Selected")
        remove_folder_btn.clicked.connect(self.remove_library_folder)
        library_buttons_layout.addWidget(add_folder_btn)
        library_buttons_layout.addWidget(remove_folder_btn)

        form.addRow("Music Library Folders:", self.library_paths_list)
        form.addRow("", library_buttons_layout)

        # Playlist Export Path
        self.export_path_edit = QLineEdit()
        export_path_layout = QHBoxLayout()
        export_path_layout.addWidget(self.export_path_edit)
        browse_export_btn = QPushButton("Browse...")
        browse_export_btn.clicked.connect(self.browse_export_path)
        export_path_layout.addWidget(browse_export_btn)
        form.addRow("Playlist Export Path:", export_path_layout)

        # Recent Playlist Days
        self.recent_days_spin = QSpinBox()
        self.recent_days_spin.setRange(1, 365)
        form.addRow("Exclude songs played in last (days):", self.recent_days_spin)

        layout.addLayout(form)

        # Custom Export
        custom_export_group = QGroupBox("Custom Export")
        custom_export_layout = QFormLayout()
        self.custom_format_edit = QLineEdit()
        self.custom_format_edit.setToolTip("Placeholders: [Title], [Artist], [Album], [Genre], [Duration]")
        custom_export_layout.addRow("Format Template:", self.custom_format_edit)
        custom_export_group.setLayout(custom_export_layout)
        layout.addWidget(custom_export_group)

        # Scheduler Settings
        scheduler_group = QGroupBox("Automatic Scheduler")
        sched_layout = QFormLayout()
        
        self.sched_enabled_cb = QCheckBox("Enable Scheduler")
        sched_layout.addRow(self.sched_enabled_cb)

        self.sched_freq_combo = QComboBox()
        self.sched_freq_combo.addItems(["Daily", "Weekly"])
        self.sched_freq_combo.currentTextChanged.connect(self.on_freq_changed)
        sched_layout.addRow("Frequency:", self.sched_freq_combo)

        self.sched_day_label = QLabel("Day of Week:")
        self.sched_day_combo = QComboBox()
        self.sched_day_combo.addItems(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        sched_layout.addRow(self.sched_day_label, self.sched_day_combo)
        
        self.sched_time_edit = QTimeEdit()
        self.sched_time_edit.setDisplayFormat("HH:mm")
        sched_layout.addRow("Schedule Time:", self.sched_time_edit)
        
        self.sched_count_spin = QSpinBox()
        self.sched_count_spin.setRange(1, 1000)
        sched_layout.addRow("Song Count:", self.sched_count_spin)
        
        self.sched_format_combo = QComboBox()
        self.sched_format_combo.addItems(["m3u", "csv"])
        sched_layout.addRow("Export Format:", self.sched_format_combo)
        
        scheduler_group.setLayout(sched_layout)
        layout.addWidget(scheduler_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_settings(self):
        self.library_paths_list.clear()
        # Ensure paths are displayed in Windows format
        win_paths = []
        for p in self.settings.music_library_paths:
            if p.startswith("/mnt/"):
                parts = p.split('/')
                if len(parts) > 2 and len(parts[2]) == 1:
                    drive = parts[2].upper()
                    rest = '\\'.join(parts[3:])
                    p = f"{drive}:\\{rest}"
            win_paths.append(p)
        self.library_paths_list.addItems(win_paths)
        self.export_path_edit.setText(self.settings.playlist_export_path)
        self.recent_days_spin.setValue(self.settings.recent_playlist_days)
        self.custom_format_edit.setText(self.settings.custom_export_format)

        self.sched_enabled_cb.setChecked(self.settings.scheduler_enabled)
        self.sched_time_edit.setTime(QTime.fromString(self.settings.scheduler_time, "HH:mm"))
        self.sched_count_spin.setValue(self.settings.scheduler_playlist_count)
        self.sched_format_combo.setCurrentText(self.settings.scheduler_export_format)
        self.sched_freq_combo.setCurrentText(self.settings.scheduler_frequency.capitalize())
        self.sched_day_combo.setCurrentIndex(self.settings.scheduler_day_of_week)
        self.on_freq_changed(self.sched_freq_combo.currentText())

    def on_freq_changed(self, text: str):
        is_weekly = text.lower() == "weekly"
        self.sched_day_label.setVisible(is_weekly)
        self.sched_day_combo.setVisible(is_weekly)

    def add_library_folder(self):
        if self._is_wsl():
            folder = self._open_wsl_folder_dialog()
        else:
            folder = QFileDialog.getExistingDirectory(self, "Select Music Library Folder")
            
        if folder:
            folder = os.path.normpath(folder)
            self.library_paths_list.addItem(folder)

    def remove_library_folder(self):
        for item in self.library_paths_list.selectedItems():
            self.library_paths_list.takeItem(self.library_paths_list.row(item))

    def browse_export_path(self):
        if self._is_wsl():
            folder = self._open_wsl_folder_dialog()
        else:
            folder = QFileDialog.getExistingDirectory(self, "Select Playlist Export Folder")
            
        if folder:
            self.export_path_edit.setText(folder)

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
            if win_path:
                # Return Windows path directly
                return win_path
        except Exception as e:
            print(f"Failed to open Windows dialog: {e}")
        return None

    def accept(self):
        self.settings.music_library_paths = [self.library_paths_list.item(i).text() for i in range(self.library_paths_list.count())]
        self.settings.playlist_export_path = self.export_path_edit.text()
        self.settings.recent_playlist_days = self.recent_days_spin.value()
        self.settings.custom_export_format = self.custom_format_edit.text()

        self.settings.scheduler_enabled = self.sched_enabled_cb.isChecked()
        self.settings.scheduler_time = self.sched_time_edit.time().toString("HH:mm")
        self.settings.scheduler_playlist_count = self.sched_count_spin.value()
        self.settings.scheduler_export_format = self.sched_format_combo.currentText()
        self.settings.scheduler_frequency = self.sched_freq_combo.currentText().lower()
        self.settings.scheduler_day_of_week = self.sched_day_combo.currentIndex()

        self.settings.save()
        super().accept()