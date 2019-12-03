import os

from pynput import keyboard

from gpmp.log import get_logger

log = get_logger("hotkeys")

_debug_traces = 'DEBUG_HOTKEYS' in os.environ

Key = keyboard.Key

def ensure_key(k):
   if isinstance(k, str):
      return keyboard.KeyCode.from_char(k)
   return k

class HotkeyListener():
   def __init__(self):
      self.pressed = set()
      self.hotkey_combos = {}

   def register_hotkey(self, name, keys, action):
      keys = set(ensure_key(k) for k in keys)
      self.hotkey_combos[name] = (set(keys), action)

   def on_press(self, key):
      self.pressed.add(key)
      if _debug_traces:
         print(self.pressed)
      log.debug(self.pressed)
      for combo_name, combo in self.hotkey_combos.items():
         if combo[0] == self.pressed:
            if _debug_traces:
               print("hotkey {0} activated".format(combo_name))
            log.info("hotkey {0} activated".format(combo_name))
            combo[1]()

   def on_release(self, key):
      if key in self.pressed:
         self.pressed.remove(key)

      if _debug_traces:
         print(self.pressed)
      log.debug(self.pressed)

   def start(self):
      self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
         )
      self.listener.start()
