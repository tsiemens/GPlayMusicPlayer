#!/usr/bin/env python3

import argparse
import atexit
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

import hotkeys

import pdb

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

def enable_echo(enable):
    fd = sys.stdin.fileno()
    new = termios.tcgetattr(fd)
    if enable:
        new[3] |= termios.ECHO
    else:
        new[3] &= ~termios.ECHO

    termios.tcsetattr(fd, termios.TCSANOW, new)

class TrackPlayer():
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

   def __del__(self):
      self.cleanup_player()

   def setup_hotkeys(self):
      self.key_listener.register_hotkey(
            "play_pause", (hotkeys.Key.ctrl, hotkeys.Key.up), self.toggle_play)
      self.key_listener.register_hotkey(
            "next", (hotkeys.Key.ctrl, hotkeys.Key.right), self.play_next_track)
      self.key_listener.register_hotkey(
            "prev", (hotkeys.Key.ctrl, hotkeys.Key.left),
            self.handle_previous_track_action)

   def activate_hotkeys(self):
      # Hide keypressed from being echoed in the console
      #  atexit.register(enable_echo, True)
      #  enable_echo(False)
      pass

   def set_tracks_to_play(self, track_ids):
      self.tracks_to_play = track_ids

   def shuffle_tracks(self):
      random.shuffle(self.tracks_to_play)

   def handle_track_finished(self, event):
      self.play_next_track()

   def init_progress_bar(self, song_str):
      from progress.bar import IncrementalBar

      if self.progress_bar is not None:
         self.progress_bar.finish()
      self.progress_bar = IncrementalBar(song_str, max=100, suffix='%(percent)d%%')
      self.progress_bar.goto(0)

   def cleanup_player(self):
      if self.player is not None:
         if self.player.is_playing():
            self.player.stop()
         self.player.release()
         self.player = None

      if self.progress_bar is not None:
         self.progress_bar.finish()
         self.progress_bar = None

   def update_progress_bar(self):
      if self.player is not None and self.progress_bar is not None:
         prog = min(int(self.player.get_position() * 100), 100)
         self.progress_bar.goto(prog)

   def _get_new_player(self, url):
      self.cleanup_player()
      self.player = vlc.MediaPlayer(url)
      self.player.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached,
                                               self.handle_track_finished)

      return self.player

   def play_current_track(self):
      self.cleanup_player()

      song_id = self.tracks_to_play[self.current_track_index]
      song_info = self.songs.get(song_id)
      song_str = "Unknown - Unknown"
      if song_info:
         song_str = "{0} - {1}".format(song_info['title'], song_info['artist'])

      url = self.api.get_stream_url(song_id)
      self._get_new_player(url).play()
      # Quick sleep, to avoid printing the bar over anything printed in the media thread
      sleep(1.0)
      self.init_progress_bar(song_str)

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
      if self.current_track_index is None:
         self.current_track_index = 0
      else:
         self.current_track_index += 1
      if self.current_track_index >= len(self.tracks_to_play):
         return False

      self.play_current_track()

   def toggle_play(self):
      if self.player is None:
         self.play_next_track()
      elif self.player.is_playing():
         self.player.pause()
      else:
         self.player.play()

def quick_player_test(api, key_listener):
   player = TrackPlayer(api, key_listener)
   player.set_tracks_to_play(list(player.songs.keys()))
   player.shuffle_tracks()

   key_listener.start()
   player.toggle_play()

   # Hide keypressed from being echoed in the console
   if 'ECHO_KEYS' not in os.environ:
      atexit.register(enable_echo, True)
      enable_echo(False)

   try:
      while True:
         sleep(1)
         player.update_progress_bar()
   except KeyboardInterrupt:
      print("\nReceived Ctrl-C")
      exited = True

def player_test(api, key_listener):
   #  playlists = api.get_all_playlists()
   playlists = api.get_all_user_playlist_contents()
   for i, playlist in enumerate(playlists):
      print("[{0}]: {1}".format(i, playlist['name']))

   index = int(input("\nSelect a playlist. "))
   if index >= len(playlists):
      print("No playlist at that index.")
      return

   playlist = playlists[index]
   del playlists

   player = TrackPlayer(api, key_listener)
   trackIds = [t['trackId'] for t in playlist['tracks']]
   del playlist
   player.set_tracks_to_play(trackIds)
   player.shuffle_tracks()

   key_listener.start()
   player.toggle_play()

   # Hide keypressed from being echoed in the console
   if 'ECHO_KEYS' not in os.environ:
      atexit.register(enable_echo, True)
      enable_echo(False)

   try:
      while True:
         sleep(1)
         player.update_progress_bar()
   except KeyboardInterrupt:
      print("\nReceived Ctrl-C")
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
   parser.add_argument('--quick-test', action='store_true',
                       help="Load a set of songs quickly for testing")
   args = parser.parse_args()

   api = Mobileclient()
   if not os.path.exists(oauth_file):
      api.perform_oauth(oauth_file)

   device_id = Mobileclient.FROM_MAC_ADDRESS
   api.oauth_login(device_id, oauth_credentials=oauth_file)

   kl = hotkeys.HotkeyListener()

   kl.register_hotkey("foo", (hotkeys.Key.ctrl, 'y'),
                      lambda: print("did foo!"))

   if args.quick_test:
      quick_player_test(api, kl)
   else:
      player_test(api, kl)

   #  key_test()
   #  pdb.set_trace()

   #  app = buildUI()
   #  app.mainloop()

if __name__ == '__main__':
   main()
