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

   def set_if_equal(self, val_to_match, new_val_if_eq):
      with self._lock:
         if self._value == val_to_match:
            self._value = new_val_if_eq
            return True
      return False
