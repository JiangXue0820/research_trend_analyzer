"""
Logging configuration for Research Trend Analyzer Agent.
Adapted for langchain framework compatibility.
"""

import logging
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    COLORS = {
        'DEBUG': '\033[94m',    # Blue
        'INFO': '\033[92m',     # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'CRITICAL': '\033[95m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        log_message = super().format(record)
        if record.levelname in self.COLORS:
            return f"{self.COLORS[record.levelname]}{log_message}{self.COLORS['RESET']}"
        return log_message

def configure_logging(
    console: bool = True,
    console_level: int = logging.INFO,
    colored_console: bool = True,
    log_file: Optional[str] = None,
    file_level: int = logging.DEBUG
) -> None:
    """
    Configure logging for the application.
    
    Args:
        console: Whether to enable console logging
        console_level: Log level for console output
        colored_console: Whether to use colored console output
        log_file: Path to log file (optional)
        file_level: Log level for file output
    """
    # Clear existing handlers
    logging.getLogger().handlers.clear()
    
    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        
        if colored_console:
            formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(file_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Name of the logger
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)

# Default logging configuration
def setup_default_logging():
    """Set up default logging configuration from environment variables."""
    log_file = os.getenv('LOG_FILE', 'logs/app.log')
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    configure_logging(
        console=True,
        console_level=getattr(logging, log_level, logging.INFO),
        colored_console=True,
        log_file=log_file,
        file_level=logging.DEBUG
    )

# Initialize default logging when module is imported
setup_default_logging()