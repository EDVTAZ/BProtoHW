"""
The utils.py file contains the implementation for getch, a function that gets a single character from stdin (and unlike sys.stdin.read(1) it doesn't wait for an endline to flush the buffer).
"""

def nest(obj, path):
    """
    create <path> in <obj> nested dictionary
    """
    if path == None or len(path) == 0:
        return

    p = path[0]
    for k in p:
        if k not in obj:
            obj[k] = {}
        nest(obj[k], path[1:])
    
# ugh https://stackoverflow.com/questions/510357/python-read-a-single-character-from-the-user
class _Getch:
    """Gets a single character from standard input.  Does not echo to the
screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()


getch = _Getch()