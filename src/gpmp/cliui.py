"""Logic and layouts for CLI UI"""

import threading
from time import sleep

from gmusicapi import Mobileclient
from progress.bar import IncrementalBar

from gpmp.log import get_logger
from gpmp.player import TrackPlayer

log = get_logger()

class CliUI:
   def __init__(self, player: TrackPlayer, api: Mobileclient,
                play_all_songs=False):
      self.player = player
      self.api = api
      self.library = self.player.library
      self.play_all_songs = play_all_songs
      self.progress_bar = None
      self.current_song_info = None

   def get_user_selected_playlist_tracks(self):
      self.library.load_playlist_contents()
      playlists = self.library.playlist_meta
      for i, playlist in enumerate(playlists):
         print("[{0}]: {1}".format(i, playlist['name']))

      index = int(input("\nSelect a playlist. "))
      if index >= len(playlists):
         print("No playlist at that index.")
         return None

      playlist = playlists[index]
      return self.library.playlist_contents[playlist['id']]

   def run_player(self):
      self.player.initialize()
      if self.play_all_songs:
         track_ids = list(self.library.songs.keys())
      else:
         track_ids = self.get_user_selected_playlist_tracks()

      self.player.set_tracks_to_play(track_ids)
      self.player.shuffle_tracks()

      self.player.toggle_play()

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
      self.run_player()
      try:
         self.run_loop()
      except KeyboardInterrupt:
         print("\nReceived Ctrl-C")
         self.clear_progress_bar()
