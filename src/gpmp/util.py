import pdb as pdbmod
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

def pdb():
   enable_echo(True)
   pdbmod.Pdb(skip=['gpmp.util']).set_trace()
