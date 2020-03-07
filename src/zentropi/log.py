import logging as _logging
import logging.handlers as _log_handlers
from os import makedirs as _make_directories
from pathlib import Path as _Path

from .symbol import APP_NAME
from .symbol import MB

_root_logger = _logging.getLogger(APP_NAME)
_root_logger_configured = False
logger = _root_logger


def logging_configure(file_path,
                      log_level=_logging.WARNING,
                      file_size=10 * MB,
                      keep_logs=10):
    global _root_logger_configured
    assert _root_logger_configured is False, 'root_logger is already configured!'

    file_formatter = _logging.Formatter(
        '%(asctime)s %(processName)-10s %(name)s %(levelname)-8s %(message)s')
    console_formatter = _logging.Formatter(
        '%(name)-15s %(levelname)-8s %(message)s')

    log_file_path = _Path(file_path)
    _make_directories(log_file_path.parent, exist_ok=True)
    fh = _log_handlers.RotatingFileHandler(log_file_path, 'a', file_size, keep_logs)
    fh.setFormatter(file_formatter)
    fh.setLevel(_logging.DEBUG)

    ch = _logging.StreamHandler()
    ch.setFormatter(console_formatter)
    ch.setLevel(log_level)

    _root_logger.addHandler(fh)
    _root_logger.addHandler(ch)
    _root_logger.setLevel(_logging.DEBUG)

    _root_logger_configured = True


def logging_init(name):
    global logger
    logger = _logging.getLogger(name)
