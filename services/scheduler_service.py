import datetime
from PySide6.QtCore import QObject, QTimer, Signal

class SchedulerService(QObject):
    """Service to trigger events at scheduled times."""
    generate_signal = Signal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_time)
        self._last_run_date = None

    def start(self):
        """Starts the scheduler timer (checks every 10 seconds)."""
        self.timer.start(10000)

    def stop(self):
        self.timer.stop()

    def _check_time(self):
        if not self.settings.scheduler_enabled:
            return

        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        
        if current_time == self.settings.scheduler_time:
            # Check if we should run today
            should_run = False
            if self.settings.scheduler_frequency == 'daily':
                should_run = True
            elif self.settings.scheduler_frequency == 'weekly':
                if now.weekday() == self.settings.scheduler_day_of_week:  # Monday is 0, Sunday is 6
                    should_run = True
            
            # Ensure it only runs once per day
            if should_run and self._last_run_date != now.date():
                self._last_run_date = now.date()
                self.generate_signal.emit()