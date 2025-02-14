"""
Main client program.
Run `python3 Dimy.py -h` for a help menu on how to use.
Only works on systems that have socket.SO_REUSEADDR defined (most systems).
Some obscure systems may not work without SO_REUSEPORT set as well.
This program has been tested on Python 3.7 - 3.9.
"""

import argparse
import client

def main(ip, port, commands):
    c = client.Client(ip, port, commands)
    try:
        c.start()
    except client.ProgramStop:
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ip", type=str, help="Server IP to use")
    parser.add_argument("port", type=int, help="Server port to use")
    parser.add_argument("commands", type=str, help="Location of the command file to use.")
    args = parser.parse_args()
    main(args.ip, args.port, args.commands)

"""
UDP broadcast with ports handles locations for clients to hang around with each other.

Custom library for time tracker (to speed up testing). Client is single threaded.

Client does the following functions:
    - Command file usage.
    - Maintaining DBFs, QBFs, CBFs.
    - Checking QBFs on server, uploading CBFs,
    - Generating shares, broadcasting shares.
    - Listen for UDP broadcast shares, make EncID with another client.

Client has the following sockets:
    - Broadcast socket. Sends EphID shares to a port corresponding to the location the client is in.
    - Broadcast listen socket. Listens for broadcasts to reconstruct EphID.

Command file format: Line separated list of instructions. If the end of file is reached without
a STOP, the commands are looped from the beginning. First command needs to be a move to set the
initial location. All commands are uppercase. No guarantees on the order of operations that occur
at the same time (like moving and broadcasting a share).
WAIT X
    - Tells the client to wait at the current location for X seconds where X is a float. X should be
      at minimum 1 second to allow for accurate timings.

MOVE X
    - Move to location X where X is an integer > 1024 and < 65536. The node will listen for broadcasts
      at this location.

POSITIVE X
    - Tell the backend server this node has diagnosed positive and stops generating QBFs for X
      seconds where X is an integer. The program continues to generate and transmit EphIDs.
      Instead of QBFs, the program generates CBFs and uploads them every 9 minutes.
    - At the end of X seconds, the node will go back to doing QBFs.
    - Do not have a POSITIVE command before the previous one has gone back to doing QBFs.

STOP
    - Stops the program here.
"""
