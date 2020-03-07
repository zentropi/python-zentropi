from pathlib import Path as _Path
from sys import intern as _intern

from . import __version__

APP_NAME = 'zentropi'
APP_VERSION = __version__

_app_absolute_path = _Path(__file__)

BASE_DIR = _intern(str(
    _app_absolute_path.resolve().parent))


BYTE = 1
KB = 1024 * BYTE
MB = 1024 * KB
GB = 1024 * MB
TB = 1024 * GB
PB = 1024 * TB
