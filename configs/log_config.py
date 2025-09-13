import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# Optional: enable ANSI colors on Windows
try:
    import colorama
    colorama.just_fix_windows_console()  # or colorama.init()
except Exception:
    pass

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG:    "\x1b[38;20m",  # dim gray
        logging.INFO:     "\x1b[37;20m",  # white
        logging.WARNING:  "\x1b[33;20m",  # yellow
        logging.ERROR:    "\x1b[31;20m",  # red
        logging.CRITICAL: "\x1b[31;1m",   # bold red
    }
    RESET = "\x1b[0m"

    def __init__(self, fmt: str, datefmt: str | None = None, use_color: bool = True):
        super().__init__(fmt, datefmt)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        # Don't mutate record.levelname used by other handlers; add a new field
        if self.use_color:
            color = self.COLORS.get(record.levelno, "")
            record.levelname_color = f"{color}{record.levelname}{self.RESET}" if color else record.levelname
            record.message_color = f"{self.COLORS.get(record.levelno, '')}{record.getMessage()}{self.RESET}"
        else:
            record.levelname_color = record.levelname
            record.message_color = record.getMessage()
        # Let base class build the final string using our injected fields
        return super().format(record)

def configure_logging(
    log_dir: str = "logs",
    log_file: str = "app.log",
    max_bytes: int = 5 * 1024 * 1024,     # 5 MB
    backup_count: int = 5,
    console: bool = True,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    colored_console: bool = True,
) -> None:
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # capture everything; handlers filter

    # prevent duplicate handlers on re-config
    for h in list(root.handlers):
        root.removeHandler(h)

    # File handler (no colors)
    fh = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    fh.setLevel(file_level)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(fh)

    # Console handler with colors
    if console:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(console_level)
        use_color = colored_console and sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb"
        ch.setFormatter(ColorFormatter("%(levelname_color)s | %(message_color)s", use_color=use_color))
        root.addHandler(ch)

# --- Example ---
if __name__ == "__main__":
    configure_logging(console=True, console_level=logging.INFO, colored_console=True)
    log = logging.getLogger(__name__)
    log.debug("debug message")
    log.info("info message")
    log.warning("warning message")
    log.error("error message")
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("exception with traceback")
