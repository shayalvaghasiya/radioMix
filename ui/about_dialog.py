from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PySide6.QtCore import Qt

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Radio Mix")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout(self)

        title = QLabel("Radio Mix")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = title.font()
        font.setBold(True)
        font.setPointSize(14)
        title.setFont(font)
        layout.addWidget(title)

        label = QLabel("Playlist Automation Tool\nVersion 1.1")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)