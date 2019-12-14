"""Utilities for multi-threading"""

import threading

# pylint: disable-msg=too-few-public-methods
class Atomic:
   def __init__(self, value=None):
      self._value = value
      self._lock = threading.Lock()

   @property
   def value(self):
      with self._lock:
         return self._value

   @value.setter
   def value(self, val):
      with self._lock:
         self._value = val
         return self._value
