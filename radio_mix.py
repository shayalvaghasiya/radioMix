import sys
import os
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.logger import setup_logging
from database import db
from config.settings import settings

def main():
    # This file is now the main entry point for the application.
    # The original monolithic UI and logic have been refactored into
    # the new modular project structure.
    
    # This will create the log directory and set up logging
    setup_logging()

    # Ensure the data directory for the database exists
    db_path = settings.database_url.replace("sqlite:///", "")
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path))
    db.init_db()

    # Ensure the default export directory exists
    if not os.path.exists(settings.playlist_export_path):
        os.makedirs(settings.playlist_export_path)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
