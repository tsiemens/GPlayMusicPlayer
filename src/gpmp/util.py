"""General/misc utilities"""

import pdb as pdbmod
import signal
import sys
import termios

def enable_echo(enable):
   fd = sys.stdin.fileno()
   new = termios.tcgetattr(fd)
   if enable:
      new[3] |= termios.ECHO
   else:
      new[3] &= ~termios.ECHO

   termios.tcsetattr(fd, termios.TCSANOW, new)

def wait_for_interrupt():
   exited = False
   while not exited:
      try:
         signal.pause()
      except KeyboardInterrupt:
         print("\nReceived Ctrl-C")
         exited = True

def pdb():
   enable_echo(True)
   # pylint: disable-msg=no-member
   pdbmod.Pdb(skip=['gpmp.util']).set_trace()
