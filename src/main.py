#!/usr/bin/env python3

import argparse
import os

from gmusicapi import Mobileclient
from setproctitle import setproctitle
from system_hotkey import SystemHotkey

from gpmp.auth import authenticate_client
from gpmp.log import get_logger
from gpmp.player import TrackPlayer
from gpmp.util import pdb

log = get_logger("main")

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

def run_cli_player(api, hotkey_mgr, play_all_songs=False):
   player = TrackPlayer(api, hotkey_mgr)

   if play_all_songs:
      trackIds = list(player.songs.keys())
   else:
      trackIds = get_user_selected_playlist_tracks(api)

   player.set_tracks_to_play(trackIds)
   player.shuffle_tracks()

   player.toggle_play()
   player.start_event_handler_thread()

   return player

def main():
   setproctitle("gplaymusicplayer")

   parser = argparse.ArgumentParser()
   parser.add_argument('--all-songs', action='store_true',
                       help="Play all songs in the library, rather than selecting a playlist")
   parser.add_argument('--gui', action='store_true',
                       help="Run in GUI mode")
   parser.add_argument('--no-gui', action='store_true',
                       help="Run in CLI mode")
   parser.add_argument('--gui-only-test', action='store_true',
                       help="Don't load the player (for testing)")
   args = parser.parse_args()

   api = Mobileclient()
   hotkey_mgr = SystemHotkey()

   if args.gui or not args.no_gui:
      from gpmp import gui

      player = TrackPlayer(api, hotkey_mgr)

      #  if args.gui_only_test:
         #  player = None
      #  else:
         #  player = run_cli_player(api, hotkey_mgr, play_all_songs=args.all_songs)

      app = gui.make_app()
      controller = gui.QtController(app, api, hotkey_mgr, player,
                                    init_player=not args.gui_only_test)

      def sighandler(signum, frame):
         if signum == signal.SIGINT:
            print("sighandler: Ctrl-C")
            app.quit()

      import signal
      signal.signal(signal.SIGINT, sighandler)
      app.exec_()
      signal.signal(signal.SIGINT, signal.SIG_DFL)

      if player:
         player.stop_event_handler_thread()
   else:
      authenticate_client(api)
      from gpmp import cliui
      player = run_cli_player(api, hotkey_mgr, play_all_songs=args.all_songs)
      ui = cliui.CliUI(player)
      ui.exec_()

      player.stop_event_handler_thread()

if __name__ == '__main__':
   main()
