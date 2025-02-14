"""
Time management that allows for speeding up time (for testing).
"""

import time as time_real

# Speed up or slow down time for this program.
# Higher values indicate faster time.
# i.e. TIME_SCALE = 2.0 means any operation that would sleep for
# 2 seconds now only sleeps for 1.
TIME_SCALE = 1.0

if TIME_SCALE != 1.0:
    print(f"\033[93mAlert: Time scale is {TIME_SCALE}x\033[0m")

def time() -> float:
    """Current time in seconds."""
    return time_real.time() * TIME_SCALE

def sleep(secs: float):
    """Delay execution for the number of seconds."""
    time_real.sleep(secs / TIME_SCALE)

def till_next(interval: float) -> "float":
    """Calculate the delta till the next multiple of interval."""
    return interval - (rel() % interval)

def rel() -> float:
    """Return time since start."""
    return time() - TIME_START

# Need a common start time for operations.
TIME_START = time()
