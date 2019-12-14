#!/usr/bin/env python3
"""Main driver for gplaymusicplayer. Defaults to GUI"""

import argparse
import signal

from gmusicapi import Mobileclient
from setproctitle import setproctitle
from system_hotkey import SystemHotkey

from gpmp.auth import authenticate_client
from gpmp.log import get_logger
from gpmp.player import Library, TrackPlayer
from gpmp.util import pdb # pylint: disable-msg=unused-import

log = get_logger()

def main():
   setproctitle("gplaymusicplayer")

   parser = argparse.ArgumentParser()
   parser.add_argument('--all-songs', action='store_true',
                       help="Play all songs in the library, rather than selecting a "
                            "playlist (CLI mode only)")
   parser.add_argument('--no-gui', action='store_true', default=False,
                       help="Run in CLI mode")
   parser.add_argument('--gui-only-test', action='store_true',
                       help="Don't load the player (for testing)")
   args = parser.parse_args()

   api = Mobileclient()
   hotkey_mgr = SystemHotkey()
   library = Library(api)
   player = TrackPlayer(api, hotkey_mgr, library)

   if not args.gui_only_test:
      authenticate_client(api)

   if not args.no_gui:
      # pylint: disable-msg=import-outside-toplevel
      from gpmp import gui
      app = gui.make_app()
      _controller = gui.QtController(app, player,
                                     init_player=not args.gui_only_test)

      def sighandler(signum, _frame):
         if signum == signal.SIGINT:
            print("sighandler: Ctrl-C")
            app.quit()

      signal.signal(signal.SIGINT, sighandler)
      app.exec_()
      signal.signal(signal.SIGINT, signal.SIG_DFL)
   else:
      from gpmp import cliui # pylint: disable-msg=import-outside-toplevel
      ui = cliui.CliUI(player, api, play_all_songs=args.all_songs)
      ui.exec_()

   player.stop_event_handler_thread()

if __name__ == '__main__':
   main()
