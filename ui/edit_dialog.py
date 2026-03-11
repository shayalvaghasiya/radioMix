from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox
)
from database.models import Rotation

class EditSongDialog(QDialog):
    def __init__(self, song_obj, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Song")
        self.song_id = song_obj.id
        # Pre-fill data
        self.data = {
            'title': song_obj.title,
            'artist': song_obj.artist,
            'album': song_obj.album,
            'genre': song_obj.genre,
            'rotation': song_obj.rotation
        }
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.title_edit = QLineEdit(self.data.get('title') or '')
        self.artist_edit = QLineEdit(self.data.get('artist') or '')
        self.album_edit = QLineEdit(self.data.get('album') or '')
        self.genre_edit = QLineEdit(self.data.get('genre') or '')
        
        self.rotation_cb = QComboBox()
        self.rotation_cb.addItems([r.value for r in Rotation])
        if self.data.get('rotation'):
            self.rotation_cb.setCurrentText(self.data['rotation'].value)

        form.addRow("Title:", self.title_edit)
        form.addRow("Artist:", self.artist_edit)
        form.addRow("Album:", self.album_edit)
        form.addRow("Genre:", self.genre_edit)
        form.addRow("Rotation:", self.rotation_cb)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return {
            'title': self.title_edit.text(),
            'artist': self.artist_edit.text(),
            'album': self.album_edit.text(),
            'genre': self.genre_edit.text(),
            'rotation': Rotation(self.rotation_cb.currentText())
        }