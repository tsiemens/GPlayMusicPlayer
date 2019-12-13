#!/usr/bin/env python3

import argparse
import os

from gmusicapi import Mobileclient
from setproctitle import setproctitle
from system_hotkey import SystemHotkey

from gpmp.auth import authenticate_client
from gpmp.log import get_logger
from gpmp.player import Library, TrackPlayer
from gpmp.util import pdb

log = get_logger("main")

def main():
   setproctitle("gplaymusicplayer")

   parser = argparse.ArgumentParser()
   parser.add_argument('--all-songs', action='store_true',
                       help="Play all songs in the library, rather than selecting a playlist (CLI mode only)")
   parser.add_argument('--no-gui', action='store_true', default=False,
                       help="Run in CLI mode")
   parser.add_argument('--gui-only-test', action='store_true',
                       help="Don't load the player (for testing)")
   args = parser.parse_args()

   api = Mobileclient()
   hotkey_mgr = SystemHotkey()
   library = Library(api)
   player = TrackPlayer(api, hotkey_mgr, library)

   if not args.no_gui:
      from gpmp import gui
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
   else:
      authenticate_client(api)
      from gpmp import cliui
      ui = cliui.CliUI(player, api, play_all_songs=args.all_songs)
      ui.exec_()

   player.stop_event_handler_thread()

if __name__ == '__main__':
   main()
