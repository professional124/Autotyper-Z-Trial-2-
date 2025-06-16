import logging
from logging.handlers import RotatingFileHandler
import os

# === Configuration ===
LOG_DIR = "logs"
LOG_FILE = "bot.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3  # keep last 3 logs

# === Ensure logs directory exists ===
os.makedirs(LOG_DIR, exist_ok=True)

# === Create logger ===
logger = logging.getLogger("AutoTyperZ")
logger.setLevel(logging.DEBUG)  # Set to INFO or WARNING for less verbosity

# === Formatter with timestamps and log level ===
formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# === Console handler with color support ===
class ColorConsoleHandler(logging.StreamHandler):
    COLORS = {
        "DEBUG": "\033[94m",     # Blue
        "INFO": "\033[92m",      # Green
        "WARNING": "\033[93m",   # Yellow
        "ERROR": "\033[91m",     # Red
        "CRITICAL": "\033[95m",  # Magenta
    }
    RESET = "\033[0m"

    def emit(self, record):
        try:
            color = self.COLORS.get(record.levelname, self.RESET)
            record.msg = f"{color}{record.msg}{self.RESET}"
            super().emit(record)
        except Exception:
            self.handleError(record)

console_handler = ColorConsoleHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# === File handler with rotating logs ===
file_handler = RotatingFileHandler(
    filename=os.path.join(LOG_DIR, LOG_FILE),
    maxBytes=MAX_LOG_SIZE,
    backupCount=BACKUP_COUNT,
    encoding="utf-8"
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# === Disable propagation to root logger ===
logger.propagate = False

# === Helper function to use logger globally ===
def get_logger():
    return logger
