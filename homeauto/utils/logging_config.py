"""
Logging configuration for Home Automation project
"""

import logging
import sys
from typing import Optional
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormatter(logging.Formatter):
    """Custom log formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[41m',   # Red background
        'RESET': '\033[0m',       # Reset
    }
    
    def format(self, record):
        """Format log record with colors"""
        if sys.stdout.isatty():  # Only use colors in terminal
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
                record.msg = f"{self.COLORS[levelname]}{record.msg}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logging(
    level: LogLevel = LogLevel.INFO,
    verbose: bool = False,
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    Set up logging configuration
    
    Args:
        level: Log level
        verbose: If True, enable debug logging
        log_file: Optional file to log to
        console: Whether to log to console
    
    Returns:
        Root logger
    """
    # Determine log level
    if verbose:
        log_level = logging.DEBUG
    else:
        log_level = getattr(logging, level.value)
    
    # Create root logger
    logger = logging.getLogger("homeauto")
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    colored_formatter = LogFormatter(
        '%(levelname)s: %(message)s'
    )
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        if sys.stdout.isatty() and not verbose:
            console_handler.setFormatter(colored_formatter)
        else:
            console_handler.setFormatter(simple_formatter)
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)
    
    # Add file handler if log_file specified
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)
    
    # Set level for common third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f"homeauto.{name}")


# Convenience functions for common logging operations
def log_device_communication(logger: logging.Logger, device_type: str, device_ip: str, 
                           operation: str, details: str = "", success: bool = True):
    """Log device communication details"""
    status = "SUCCESS" if success else "FAILED"
    logger.debug(f"[{device_type}@{device_ip}] {operation} - {status} {details}")


def log_network_scan(logger: logging.Logger, ip: str, ports: list, result: str):
    """Log network scan details"""
    ports_str = ",".join(str(p) for p in ports) if ports else "none"
    logger.debug(f"[SCAN] {ip}:{ports_str} - {result}")


def log_device_identification(logger: logging.Logger, ip: str, mac: str, 
                            device_type: str, confidence: float):
    """Log device identification details"""
    logger.debug(f"[IDENTIFY] {ip} ({mac}) -> {device_type} (confidence: {confidence:.2f})")
