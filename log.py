"""Simple logging functionality for Dimy"""

import timekeeper as time

"""
Color codes taken from Blender build scripts.
https://svn.blender.org/svnroot/bf-blender/trunk/blender/build_files/scons/tools/bcolors.py
"""
MAGENTA = '\033[95m'
BLUE = '\033[94m'
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
RESET = '\033[0m'
colors = {"MAGENTA": MAGENTA,
          "BLUE": BLUE,
          "CYAN": CYAN,
          "GREEN": GREEN,
          "YELLOW": YELLOW,
          "RED": RED,
          "BOLD": BOLD,
          "UNDERLINE": UNDERLINE,
          "RESET": RESET}

def log(*values: "str | tuple[str, ...]", sep=" "):
    """
    Works similarly to the print statement.
    Arguments can be a tuple in which case it is colored.
    """
    header = f"[{CYAN}{time.rel():07.2f}{RESET}] "
    joined = []
    for v in values:
        if isinstance(v, tuple):
            # text, *col
            color = "".join(colors[x] for x in v[1:])
            joined.append(color + v[0] + RESET)
        elif isinstance(v, str):
            # raw text
            joined.append(v)
    print(header + sep.join(joined))
