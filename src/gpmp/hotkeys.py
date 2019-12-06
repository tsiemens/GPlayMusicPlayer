import os
import string

from pynput import keyboard

from gpmp.log import get_logger

log = get_logger("hotkeys")

Key = keyboard.Key

def ensure_key(k):
   if isinstance(k, str):
      return keyboard.KeyCode.from_char(k)
   return k

_char_lower_map = {
   '~': '`',
   '!': '1',
   '@': '2',
   '#': '3',
   '$': '4',
   '%': '5',
   '^': '6',
   '&': '7',
   '*': '8',
   '(': '9',
   ')': '0',
   '_': '-',
   '+': '=',
   '{': '[',
   '}': ']',
   '|': '\\',
   ':': ';',
   '"': '\'',
   '<': ',',
   '>': '.',
   '?': '/',
}
_special_chars_lower = set(_char_lower_map.values())

class HotkeyListener():
   def __init__(self):
      self.pressed = set()
      self.hotkey_combos = {}

   def register_hotkey(self, name, keys, action):
      keys = set(ensure_key(k) for k in keys)
      self.hotkey_combos[name] = (set(keys), action)

   def sanitize_key(self, key):
      if hasattr(key, 'char') and key.char is not None:
         lower = key.char.lower()
         if (lower == key.char and lower not in string.ascii_lowercase
             and lower not in _special_chars_lower):
            lower = _char_lower_map.get(lower)

         if lower is None:
            log.info("key: {} returned None".format(key.char))
            return None
         return keyboard.KeyCode.from_char(lower)
      return key

   def on_press(self, key):
      key = self.sanitize_key(key)
      if key is None:
         return
      self.pressed.add(key)
      log.debug(self.pressed)
      for combo_name, combo in self.hotkey_combos.items():
         if combo[0] == self.pressed:
            log.info("hotkey {0} activated".format(combo_name))
            combo[1]()

   def on_release(self, key):
      key = self.sanitize_key(key)
      if key is None:
         return
      if key in self.pressed:
         self.pressed.remove(key)

      log.debug(self.pressed)

   def start(self):
      self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
         )
      self.listener.start()
