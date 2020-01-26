#!/usr/bin/env python3
"""Main driver for gplaymusicplayer. Defaults to GUI"""

import argparse
import os
import signal

from setproctitle import setproctitle
from system_hotkey import SystemHotkey

from gpmp.api import Client
from gpmp.log import get_logger
from gpmp.player import Library, TrackPlayer
from gpmp.util import pdb # pylint: disable-msg=unused-import

log = get_logger()

def main():
   if "RANDSEED" in os.environ:
      # pylint: disable-msg=import-outside-toplevel
      import random
      random.seed(int(os.environ["RANDSEED"]))

   setproctitle("gplaymusicplayer")

   parser = argparse.ArgumentParser()
   parser.add_argument('--all-songs', action='store_true',
                       help="Play all songs in the library, rather than selecting a "
                            "playlist (CLI mode only)")
   parser.add_argument('--no-gui', action='store_true', default=False,
                       help="Run in CLI mode")
   parser.add_argument('--gui-only-test', action='store_true',
                       help="Don't load the player (for testing)")
   parser.add_argument('--error-sim-rate', type=float, default=1.0,
                       help="Debug flag - rate (0.0 - 1.0) at which simulated errors occur")
   parser.add_argument('--error-sim-attr-re', type=str, default=None,
                       help="Debug flag - regex pattern to match against api calls which "
                            "may simulate errors")
   parser.add_argument('--error-sim-enable', action='store_true',
                       help="Debug flag - enable API error simulations")
   parser.add_argument('--error-sim-timeout', type=int, default=0,
                       help="Debug flag - timeout in seconds for API error simulations")
   args = parser.parse_args()

   api = Client()
   # Set up error simulation settings
   api.set_simulated_error_rate(args.error_sim_rate)
   if args.error_sim_attr_re:
      api.set_simulated_error_function_re(args.error_sim_attr_re)
   api.simulated_timeout_delay = args.error_sim_timeout
   if args.error_sim_enable:
      if args.error_sim_timeout > 0:
         api.simulate_timeouts = True
      else:
         api.simulate_immediate_error = True

   hotkey_mgr = SystemHotkey()
   library = Library(api)
   player = TrackPlayer(api, hotkey_mgr, library)

   if not args.gui_only_test:
      api.authenticate()

   if not args.no_gui:
      # pylint: disable-msg=import-outside-toplevel
      from gpmp import gui
      app = gui.make_app()
      _controller = gui.QtController(app, api, player,
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
