import threading

class Atomic:
   def __init__(self, value=None):
      self._value = value
      self._lock = threading.Lock()

   @property
   def value(self):
      with self._lock:
         return self._value

   @value.setter
   def value(self, v):
      with self._lock:
         self._value = v
         return self._value
