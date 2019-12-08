import threading
from time import sleep

from progress.bar import IncrementalBar

from gpmp.player import TrackPlayer

class CliUI:
   def __init__(self, player: TrackPlayer):
      self.player = player
      self.progress_bar = None
      self.current_song_info = None

   def init_progress_bar(self, song_str):

      if self.progress_bar is not None:
         self.progress_bar.finish()
      self.progress_bar = IncrementalBar(song_str, max=100, suffix='%(percent)d%%')
      self.current_song_info = song_str
      self.progress_bar.goto(0)

   def clear_progress_bar(self):
      if self.progress_bar is not None:
         self.progress_bar.finish()
         self.progress_bar = None

   def update_progress_bar(self):
      if self.player is not None and self.progress_bar is not None:
         prog = min(int(self.player.get_position() * 100), 100)
         self.progress_bar.goto(prog)

   def update_ui(self):
      if self.player is None:
         self.clear_progress_bar()
         return

      player_current_song_info = self.player.current_song_info.value
      if player_current_song_info != self.current_song_info:
         # Sleep extra long before switching, since VLC usually prints out
         # some error.
         sleep(2.0)
         self.init_progress_bar(player_current_song_info)

      self.update_progress_bar()

   def run_loop(self):
      t = threading.currentThread()
      while getattr(t, "do_run", True):
         sleep(1.0)
         self.update_ui()

      log.info("CliUI loop exited")

   def exec_(self):
      """Runs the UI thread loop"""
      try:
         self.run_loop()
      except KeyboardInterrupt:
         print("\nReceived Ctrl-C")
         self.clear_progress_bar()
         exited = True

