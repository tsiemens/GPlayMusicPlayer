import logging
from logging.handlers import RotatingFileHandler
import os
import tempfile
import traceback

#  _format = '%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s'
_format = '%(asctime)s %(name)s:%(levelname)s %(funcName)s: %(message)s'
_log_format = logging.Formatter(_format)

log_file = os.path.join(tempfile.gettempdir(), "gplaymusicplayer.log")

_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5*1024*1024,
                               backupCount=1, encoding=None, delay=0)
_handler.setFormatter(_log_format)

level_abrev_to_level = {
      'E': logging.ERROR,
      'W': logging.WARNING,
      'I': logging.INFO,
      'D': logging.DEBUG,
   }
level_to_level_abrev = {
      l: a for a, l in level_abrev_to_level.items()
   }

_logging_levels = {}
def set_logger_levels():
   """Gets the logging levels specified in the LOGGING env var.
   Should be formatted as: <name>/(E|W|I|D),...
   """

   logging_levels_str = os.environ.get("LOGGING")
   if not logging_levels_str:
      return
   levels = logging_levels_str.split(',')
   for name_and_level in levels:
      if '/' in name_and_level:
         name, level = name_and_level.strip().split('/')
      else:
         name = name_and_level.strip()
         level = 'D'

      full_level = level_abrev_to_level.get(level, logging.WARNING)
      _logging_levels[name] = full_level

set_logger_levels()

_log_logger = logging.getLogger("log")
_log_logger.setLevel(logging.INFO)
_log_logger.addHandler(_handler)

def get_logger(name=None):
   if name is None:
      stack = traceback.extract_stack()
      # Get the filename without py extension of the caller
      name = os.path.split(stack[-2].filename)[1].split('.')[0]

   log = logging.getLogger(name)
   level = _logging_levels.get(name, logging.WARNING)
   _log_logger.info("{}/{}".format(name, level_to_level_abrev[level]))
   log.setLevel(_logging_levels.get(name, logging.WARNING))
   log.addHandler(_handler)
   return log
