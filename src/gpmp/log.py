"""App logging setup and utilities"""

import logging
from logging.handlers import RotatingFileHandler
import os
import tempfile
import traceback

#  _FORMAT = '%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s'
_FORMAT = '%(asctime)s %(name)s:%(levelname)s %(funcName)s: %(message)s'
_LOG_FORMATTER = logging.Formatter(_FORMAT)

LOG_FILE = os.path.join(tempfile.gettempdir(), "gplaymusicplayer.log")

_HANDLER = RotatingFileHandler(LOG_FILE, mode='a', maxBytes=5*1024*1024,
                               backupCount=1, encoding=None, delay=0)
_HANDLER.setFormatter(_LOG_FORMATTER)

LEVEL_ABREV_TO_LEVEL = {
      'E': logging.ERROR,
      'W': logging.WARNING,
      'I': logging.INFO,
      'D': logging.DEBUG,
   }
LEVEL_TO_LEVEL_ABREV = {
      l: a for a, l in LEVEL_ABREV_TO_LEVEL.items()
   }

_all_loggers = {}

_log_logger = logging.getLogger("log") # pylint: disable-msg=invalid-name
_log_logger.setLevel(logging.INFO)
_log_logger.addHandler(_HANDLER)
_all_loggers["log"] = _log_logger

_logging_levels = {} # pylint: disable-msg=invalid-name

def update_logger_level(name, logger):
   level = _logging_levels.get(name, logging.WARNING)
   _log_logger.info("%s/%s", name, LEVEL_TO_LEVEL_ABREV[level])
   logger.setLevel(_logging_levels.get(name, logging.WARNING))

def set_logger_levels(logging_levels_str=None):
   """Gets the logging levels specified in the LOGGING env var.
   Should be formatted as: <name>/(E|W|I|D),...
   """

   if logging_levels_str is None:
      logging_levels_str = os.environ.get("LOGGING")

   _logging_levels.clear()

   if logging_levels_str:
      levels = logging_levels_str.split(',')
      for name_and_level in levels:
         if '/' in name_and_level:
            name, level = name_and_level.strip().split('/')
         else:
            name = name_and_level.strip()
            level = 'D'

         full_level = LEVEL_ABREV_TO_LEVEL.get(level, logging.WARNING)
         _logging_levels[name] = full_level

   for name, log in _all_loggers.items():
      update_logger_level(name, log)

set_logger_levels()

def get_logging_levels_string():
   return ','.join(
      logname + '/' + LEVEL_TO_LEVEL_ABREV[level]
      for logname, level in _logging_levels.items()
   )

def get_logger(name=None) -> logging.Logger:
   if name is None:
      stack = traceback.extract_stack()
      # Get the filename without py extension of the caller
      name = os.path.split(stack[-2].filename)[1].split('.')[0]

   log = logging.getLogger(name)
   _all_loggers[name] = log
   update_logger_level(name, log)
   log.addHandler(_HANDLER)
   return log
