#!/usr/bin/env python3

import argparse
import atexit
from dataclasses import dataclass
import os
import random
import signal
import sys
import termios
from time import sleep
import tkinter as tk
from tkinter import N, S, E, W

from gmusicapi import Mobileclient
from setproctitle import setproctitle
import ttk
import vlc

from gpmp import hotkeys
from gpmp.log import get_logger
from gpmp.util import enable_echo, pdb

log = get_logger("main")

oauth_file = os.path.join(os.path.dirname(__file__), "oauth.json")
#  oauth_file = Mobileclient.OAUTH_FILEPATH

class Application(tk.Frame):
   def __init__(self, master=None):
      super().__init__(master)
      self.master = master
      self.master.grid_rowconfigure(0, weight=1)
      self.master.grid_columnconfigure(0, weight=1)
      self.grid(row=0, column=0, sticky=N+S+W+E)
      self.create_widgets()

   def create_widgets(self):
      self.style = ttk.Style()
      self.style.theme_use("default")

      self.master.title("GPlayMusicPlayer (Unofficial)")
      self.grid_columnconfigure(0, weight=1)
      self.grid_columnconfigure(1, weight=0)
      self.grid_columnconfigure(2, weight=1)
      self.grid_rowconfigure(0, weight=1)

      sb = ttk.Scrollbar(self)
      #  sb.pack(side=tk.RIGHT, fill=tk.Y)
      sb.grid(row=0, column=1, sticky=tk.W+tk.N+tk.S+tk.E)

      playlist_list = tk.Listbox(self, yscrollcommand=sb.set)
      for x in range(20):
         playlist_list.insert(tk.END, str(x))
         if (x % 2) != 0:
            playlist_list.itemconfig(x, {'bg':'#eeeeee'})

      #  playlist_list.pack(side=tk.LEFT, fill=tk.BOTH)
      playlist_list.grid(row=0, column=0, sticky=N+S+W+E, pady=2)
      sb.config(command=playlist_list.yview)

      tree = ttk.Treeview(self)
      tree['columns'] = ("name", "nsongs")
      tree.column("name", width=100)
      tree.column("nsongs", width=30)
      tree.heading("#0", text="Line")
      tree.heading("name", text="Playlists")
      tree.heading("nsongs", text="#")

      tree.insert("", 0, text="Line1", values=("1A", "1b"))
      tree.insert("", "end", text="Line2", values=("2A", "2b"))
      #  tree.pack(side=tk.LEFT, fill=tk.BOTH)
      tree.grid(row=0, column=2, sticky=tk.W+tk.N+tk.S+tk.E, pady=2)

def buildUI():
   root = tk.Tk()
   app = Application(master=root)
   return app

class MediaPlayer:
   def __init__(self, url):
      self.player = vlc.MediaPlayer(url)

   def __del__(self):
      """NOTE: This MUST not be called from within an event callback from the
      player.
      """
      if self.player.is_playing():
         self.player.stop()

      self.player.release()

   def __getattr__(self, attr):
      return getattr(self.player, attr)

@dataclass
class PlayerEvent:
   event_str: str
   track_index: int

class TrackPlayer:
   def __init__(self, api, key_listener):
      self.api = api
      self.key_listener = key_listener
      self.setup_hotkeys()
      songs = api.get_all_songs()
      self.songs = {
            song['id']: {
                  'artist': song.get('artist'),
                  'title': song.get('title'),
               }
            for song in songs
         }
      # List of track ids
      self.tracks_to_play = []
      self.current_track_index = None

      self.player = None
      self.progress_bar = None
      self.pending_events = []

   def __del__(self):
      self.reset_progress_bar()

   def setup_hotkeys(self):
      self.key_listener.register_hotkey(
            "play_pause", (hotkeys.Key.ctrl, hotkeys.Key.up), self.toggle_play)
      self.key_listener.register_hotkey(
            "next", (hotkeys.Key.ctrl, hotkeys.Key.right), self.play_next_track)
      self.key_listener.register_hotkey(
            "prev", (hotkeys.Key.ctrl, hotkeys.Key.left),
            self.handle_previous_track_action)
      self.key_listener.register_hotkey(
            "skip-to-end",
            (hotkeys.Key.shift, hotkeys.Key.ctrl, hotkeys.Key.right),
            self.skip_to_end)

   def activate_hotkeys(self):
      # Hide keypressed from being echoed in the console
      #  atexit.register(enable_echo, True)
      #  enable_echo(False)
      pass

   def set_tracks_to_play(self, track_ids):
      self.tracks_to_play = track_ids

   def shuffle_tracks(self):
      random.shuffle(self.tracks_to_play)

   def handle_track_finished(self):
      self.play_next_track()

   def handle_player_event(self, event):
      log.debug("handle_player_event: {}".format(event))
      if event.type == vlc.EventType.MediaPlayerEndReached:
         self.pending_events.append(PlayerEvent(str(event.type),
                                                    self.current_track_index))

   def init_progress_bar(self, song_str):
      from progress.bar import IncrementalBar

      if self.progress_bar is not None:
         self.progress_bar.finish()
      self.progress_bar = IncrementalBar(song_str, max=100, suffix='%(percent)d%%')
      self.progress_bar.goto(0)

   def reset_progress_bar(self):
      if self.progress_bar is not None:
         self.progress_bar.finish()
         self.progress_bar = None

   def update_progress_bar(self):
      if self.player is not None and self.progress_bar is not None:
         prog = min(int(self.player.get_position() * 100), 100)
         self.progress_bar.goto(prog)

   def _get_player_for_url(self, url):
      self.reset_progress_bar()
      if not self.player:
         self.player = MediaPlayer(url)
      else:
         self.player.set_mrl(url)
      # https://www.olivieraubert.net/vlc/python-ctypes/doc/vlc.EventType-class.html
      event_blacklist = set([vlc.EventType.MediaPlayerTimeChanged,
                             vlc.EventType.MediaPlayerPositionChanged,
                             vlc.EventType.MediaPlayerLengthChanged,
                             vlc.EventType.MediaPlayerBuffering,
                             vlc.EventType.MediaPlayerAudioVolume,
                             vlc.EventType.MediaPlayerAudioDevice,
                             vlc.EventType.MediaPlayerESSelected,
                             vlc.EventType.MediaPlayerESAdded,
                             vlc.EventType.MediaPlayerESDeleted,
                             vlc.EventType.MediaPlayerScrambledChanged,
                             vlc.EventType.MediaPlayerPausableChanged,
                             vlc.EventType.MediaPlayerSeekableChanged,
                             ])
      for attr in dir(vlc.EventType):
         if attr.startswith("Media") or attr.startswith("Vlm"):
            event = getattr(vlc.EventType, attr)
            if event not in event_blacklist:
               self.player.event_manager().event_attach(event,
                                                        self.handle_player_event)

      return self.player

   def play_current_track(self):
      self.reset_progress_bar()

      song_id = self.tracks_to_play[self.current_track_index]
      song_info = self.songs.get(song_id)
      song_str = "Unknown - Unknown"
      if song_info:
         song_str = "{0} - {1}".format(song_info['title'], song_info['artist'])

      url = self.api.get_stream_url(song_id)
      code = self._get_player_for_url(url).play()
      if code != 0:
         log.error("play_current_track: player.play returned error: {}".format(code))
         return False

      log.info("play_current_track: Started player: OK")
      # Quick sleep, to avoid printing the bar over anything printed in the media thread
      sleep(1.0)
      self.init_progress_bar(song_str)
      return True

   def handle_previous_track_action(self):
      if self.player is not None and self.player.get_position() > 0.1:
         # Song is 10% done. Restart the track rather than going back.
         self.player.set_position(0.0)
         return

      if self.current_track_index is None or self.current_track_index <= 0:
         self.current_track_index = 0
      else:
         self.current_track_index -=1

      #  if self.player is not None and self.player.is_playing():
      self.play_current_track()

   def play_next_track(self):
      log.info("play_next_track: current_track_index {}".format(self.current_track_index))
      if self.current_track_index is None:
         self.current_track_index = 0
      else:
         self.current_track_index += 1

      if self.current_track_index >= len(self.tracks_to_play):
         log.info("play_next_track: Reached end of track list")
         return False

      return self.play_current_track()

   def skip_to_end(self):
      if self.player is not None:
         self.player.set_position(0.97)

   def toggle_play(self):
      if self.player is None:
         self.play_next_track()
      elif self.player.is_playing():
         self.player.pause()
      else:
         code = self.player.play()
         if code != 0:
            log.error("toggle_play: player.play returned error: {}".format(code))

   def do_thread_loop(self):
      if self.pending_events:
         log.debug("do_thread_loop: n pending_events: {}".format(
                   len(self.pending_events)))
      while self.pending_events:
         event = self.pending_events.pop(0)
         log.debug("do_thread_loop event {}".format(event))
         if event.track_index != self.current_track_index:
            log.debug("do_thread_loop ignoring event for other track")
            continue

         if event.event_str == str(vlc.EventType.MediaPlayerEndReached):
            log.debug("do_thread_loop: track finished")
            self.handle_track_finished()

   def loop(self):
      time_since_progress_update = 0.0
      while True:
         sleep(0.1)
         time_since_progress_update += 0.1
         self.do_thread_loop()
         if time_since_progress_update >= 1.0:
            self.update_progress_bar()
            time_since_progress_update = 0.0

def get_user_selected_playlist_tracks(api):
   playlists = api.get_all_user_playlist_contents()
   for i, playlist in enumerate(playlists):
      print("[{0}]: {1}".format(i, playlist['name']))

   index = int(input("\nSelect a playlist. "))
   if index >= len(playlists):
      print("No playlist at that index.")
      return None

   playlist = playlists[index]
   del playlists

   return [t['trackId'] for t in playlist['tracks']]

def run_cli_player(api, key_listener, play_all_songs=False):
   player = TrackPlayer(api, key_listener)

   if play_all_songs:
      trackIds = list(player.songs.keys())
   else:
      trackIds = get_user_selected_playlist_tracks(api)

   player.set_tracks_to_play(trackIds)
   player.shuffle_tracks()

   key_listener.start()
   player.toggle_play()

   # Hide keypressed from being echoed in the console
   if 'ECHO_KEYS' not in os.environ:
      atexit.register(enable_echo, True)
      enable_echo(False)

   try:
      player.loop()
   except KeyboardInterrupt:
      print("\nReceived Ctrl-C")
      player.reset_progress_bar()
      exited = True

   #  exited = False
   #  while not exited:
      #  try:
         #  signal.pause()
      #  except KeyboardInterrupt:
         #  print("\nReceived Ctrl-C")
         #  exited = True

def main():
   setproctitle("gplaymusicplayer")

   parser = argparse.ArgumentParser()
   parser.add_argument('--all-songs', action='store_true',
                       help="Play all songs in the library, rather than selecting a playlist")
   args = parser.parse_args()

   api = Mobileclient()
   if not os.path.exists(oauth_file):
      api.perform_oauth(oauth_file)

   device_id = Mobileclient.FROM_MAC_ADDRESS
   api.oauth_login(device_id, oauth_credentials=oauth_file)

   kl = hotkeys.HotkeyListener()

   run_cli_player(api, kl, play_all_songs=args.all_songs)

   #  app = buildUI()
   #  app.mainloop()

if __name__ == '__main__':
   main()
