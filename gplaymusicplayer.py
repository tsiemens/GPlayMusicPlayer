#!/usr/bin/env python3

import atexit
import os
import signal
import sys
import termios
from time import sleep
import tkinter as tk
from tkinter import N, S, E, W

from gmusicapi import Mobileclient
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

   #  songs = api.get_all_songs()
   song_id = None
   url = None
   #  for song in songs:
      #  if song['title'] == "Sandstorm":
         #  song_id = song['id']
   song_id = playlist['tracks'][0]['trackId']

   # Hide keypressed from being echoed in the console
   atexit.register(enable_echo, True)
   enable_echo(False)

   url = api.get_stream_url(song_id)
   player = vlc.MediaPlayer(url)
   player.play()
   playing = True

   def toggle_player():
      nonlocal playing
      if playing:
         player.pause()
         playing = False
      else:
         player.play()
         playing = True

   key_listener.register_hotkey("play_pause", (hotkeys.Key.ctrl, hotkeys.Key.up),
                                toggle_player)

   try:
      signal.pause()
   except KeyboardInterrupt:
      print("\nReceived Ctrl-C")
   player.release()

def enable_echo(enable):
    fd = sys.stdin.fileno()
    new = termios.tcgetattr(fd)
    if enable:
        new[3] |= termios.ECHO
    else:
        new[3] &= ~termios.ECHO

    termios.tcsetattr(fd, termios.TCSANOW, new)

def main():
   api = Mobileclient()
   if not os.path.exists(oauth_file):
      api.perform_oauth(oauth_file)

   device_id = Mobileclient.FROM_MAC_ADDRESS
   api.oauth_login(device_id, oauth_credentials=oauth_file)

   kl = hotkeys.HotkeyListener()
   kl.start()

   kl.register_hotkey("foo", (hotkeys.Key.ctrl, 'y'),
                      lambda: print("did foo!"))

   player_test(api, kl)

   #  import signal
   #  try:
      #  signal.pause()
   #  except KeyboardInterrupt:
      #  print("\nReceived Ctrl-C")

   #  key_test()
   #  pdb.set_trace()

   #  app = buildUI()
   #  app.mainloop()

if __name__ == '__main__':
   main()
