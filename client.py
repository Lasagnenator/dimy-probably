"""
Main client object
"""

from collections import deque, defaultdict
import queue
import itertools
import random
import socket
import struct
from sched import scheduler
from bloom import BloomFilter
import log
import sss
import timekeeper as time

# Time between generating a new EphID in seconds.
EPHID_TIME = 15

# Split into n shares with k required to reconstruct EphID.
SHARE_K = 3
SHARE_N = 5

# Time between broadcasting shares in seconds.
SHARE_TIME = 3
# Probability of dropping the share at broadcast.
SHARE_DROP = 0.5
#SHARE_DROP = 0.0

# How long between cleaning up of failed share reconstructions.
SHARE_CLEAN_TIME = SHARE_N * SHARE_TIME * 2

# How long the DBF should listen for in seconds.
DBF_TIME = 90
# How long the DBF lasts for before being deleted in seconds.
# This should be a multiple of DBF_TIME.
DBF_LIFE = 540 # 9 minutes
# How long between each QBF generation.
QBF_TIME = 540 # 9 minutes

"""
Broadcast format: packed binary data of size 72
int 8: idx of share
byte 32: share bytes
byte 32: hash of EncID

Hash function used is blake2b. digest_size = 32, no key, no salt,
no personalization, fanout = 1, depth = 1, leaf_size = 0, node_offset = 0,
node_depth = 0, inner_size = 0, last_node = False. Chosen because it is fast,
secure and can produce a customised digest size.
"""
# Python Struct format string:
STRUCT_FORMAT_STRING = "<B32s32s"
STRUCT_SIZE = struct.calcsize(STRUCT_FORMAT_STRING)

# Scheduler for all client functions. Do SCHED.run() to start everything.
SCHED = scheduler(time.time, time.sleep)

class Client(object):
    def __init__(self, ip: "str", port: "int", command_path: "str"):
        """
        Create a client object with the given command file path.
        The backend server is specified with ip and port.
        """
        self.ip = ip
        self.port = port

        self.ephs: "queue.Queue[sss.Packet]" = queue.Queue()
        self.command_path = command_path

        self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_send.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Secret associated with the most recent share broadcast.
        self.last_secret = 0

        # Current location (port) of the client.
        self.location = 0

        # The listener socket for shares.
        self.sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # {hash: (time, [shares], secret)}
        self.shares = defaultdict(lambda:(time.rel(), []))
        self.own_shares = set()

        # Accurate command file timer.
        self.wait_time = 0.0

    def start(self):
        """Sets initial timers and kicks off the main event loop. Does not return."""
        self.command_loop()
        self.dbf = DBFContainer(self.ip, self.port)
        # Generate one EphID initially.
        self.eph_gen()
        SCHED.enter(time.till_next(SHARE_TIME), 1, self.eph_share)
        SCHED.enter(time.till_next(EPHID_TIME), 1, self.share_clean)
        SCHED.enter(0.1, 1, self.listen)
        SCHED.run()

    def eph_gen(self):
        """Generate a new EphID and create shares from it."""
        # Reschedule this function.
        SCHED.enter(time.till_next(EPHID_TIME), 1, self.eph_gen)

        # Generate shares and add them to the queue.
        shares = sss.generate(SHARE_K, SHARE_N)
        for s in shares:
            self.ephs.put(s)
        log.log("Generated:", (shares[0][-1][:4].hex(), "BLUE"), "with", (str(SHARE_N), "MAGENTA"), "shares")

        # Make node unable to diffie-hellman with itself.
        self.own_shares.add(shares[0][-1])
    
    def eph_share(self):
        """Broadcast unique shares."""
        # Reschedule this function.
        SCHED.enter(time.till_next(SHARE_TIME), 1, self.eph_share)

        # Get the next share and broadcast it.
        share = self.ephs.get()
        idx = share[0][0]
        hash = share[-1][:4].hex()
        if random.random() < SHARE_DROP:
            # Share drop chance succeeded.
            log.log("Dropped: (", (str(idx), "MAGENTA"), ", ", (hash, "BLUE"), ")", sep="")
            return
        log.log("Broadcast to ", (f"{self.location}", "GREEN"), ": (", (str(idx), "MAGENTA"), ", ", (hash, "BLUE"), ")", sep="")

        self.last_secret = share[1]
        packet = struct.pack(STRUCT_FORMAT_STRING, share[0][0], share[0][1], share[2])
        self.sock_send.sendto(packet, ("<broadcast>", self.location))

    def share_clean(self):
        """Clean up old shares from the share dict"""
        # Reschedule this function.
        SCHED.enter(time.till_next(EPHID_TIME), 1, self.share_clean)
        for k, v in self.shares.copy().items():
            if time.rel() - v[0] > SHARE_CLEAN_TIME:
                log.log("Discarded:", (k[:4].hex(), "BLUE"))
                del self.shares[k]

    def listen(self):
        """Listen for a broadcast and process it if possible"""
        # Try every 0.1s. Maximum throughput: 10 shares/s.
        SCHED.enter(0.1, 1, self.listen)
        try:
            raw, _ = self.sock_recv.recvfrom(STRUCT_SIZE)
        except (socket.timeout, BlockingIOError):
            # No share available.
            return
        idx, share, hash = struct.unpack(STRUCT_FORMAT_STRING, raw)

        # Filter out own shares.
        if hash in self.own_shares: return

        self.shares[hash][1].append((idx, share))

        log.log("Received: (", (str(idx), "MAGENTA"), ", ", (hash[:4].hex(), "BLUE"), ")", sep="")

        if len(self.shares[hash][1]) >= SHARE_K:
            # Can reconstruct.
            public = sss.verify(self.shares[hash][1], hash)
            # Check that shares match the hash given.
            if not public: return
            log.log("Reconstructed", (hash[:4].hex(), "BLUE"))

            EncID = sss.calc_shared(public, self.last_secret)
            self.dbf.add(EncID)
            log.log("Encoded EncID", (hex(EncID)[-16:], "YELLOW"), "into DBF")

            # Remove from the share table now because it's done.
            self.shares[hash][1].clear()

    def command_loop(self):
        """
        Follow the command file forever looping back to the start.
        Does no error checking for the file format.
        """
        with open(self.command_path) as f:
            cmds = list(map(str.split, f))

        gen = itertools.cycle(cmds)
        SCHED.enter(0.0, 1, self.command, (gen,))

    def command(self, gen: "itertools.cycle[list[str]]"):
        cmd = next(gen)
        if cmd[0] == "STOP":
            log.log("Stopping")
            raise ProgramStop("Program stop")

        elif cmd[0] == "MOVE":
            SCHED.enter(0.0, 1, self.command, (gen,))
            self.cmd_move(int(cmd[1]))
            log.log("Moved to", (str(self.location), "GREEN"))

        elif cmd[0] == "WAIT":
            self.wait_time += float(cmd[1])
            SCHED.enter(time.till_next(self.wait_time), 1, self.command, (gen,))
            log.log("Waiting", (cmd[1], "RED"), "seconds")

        elif cmd[0] == "POSITIVE":
            SCHED.enter(0.0, 1, self.command, (gen,))
            log.log("Diagnosed", ("positive", "RED"), "for", (cmd[1], "RED"), "seconds")
            self.cmd_positive(int(cmd[1]))

    def cmd_move(self, location: "int"):
        """Handle the MOVE command."""
        self.location = location

        # Make a new socket using this location.
        self.sock_recv.close()
        self.sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_recv.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock_recv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock_recv.setblocking(False)
        self.sock_recv.bind(("", self.location))

    def cmd_positive(self, period: "int"):
        """Handle the POSITIVE command."""
        # According to spec:
        # - Combine all available DBFs and upload as CBF.
        # - Stop generating QBFs.

        # Stop generating QBFs and instead generate CBFs for the specified time.
        self.dbf.is_cbf = True
        def undo():
            self.dbf.is_cbf = False
            log.log("No longer considered", ("positive", "GREEN"))
        SCHED.enter(time.till_next(self.wait_time + period), 1, undo)

        # Make the CBF and upload it.
        cbf = self.dbf.combine()
        self.dbf.contact_backend("CBF", cbf)

class DBFContainer(object):
    """
    Handles rolling DBFs and constructing QBFs.
    """
    def __init__(self, ip: "str", port: "int"):
        self.serv_addr = (ip, port)
        # + 1 because the order of making a QBF or cycling DBF is undefined.
        dbf_count = DBF_LIFE // DBF_TIME + 1
        self.dbfs: "deque[BloomFilter]" = deque([BloomFilter()], dbf_count)

        # Flag to swap between making QBFs and CBFs
        self.is_cbf = False

        SCHED.enter(time.till_next(QBF_TIME), 1, self.qbf_create)
        SCHED.enter(time.till_next(DBF_TIME), 2, self.dbf_cycle)

    def qbf_create(self):
        """Create QBFs from available DBFs"""
        # Reschedule this function.
        SCHED.enter(time.till_next(QBF_TIME), 1, self.qbf_create)

        combined = self.combine()
        
        if not self.is_cbf:
            # Upload QBF and check.
            log.log("Created QBF")
            self.contact_backend("QBF", combined)
        else:
            # Currently in CBF mode.
            log.log("Created CBF")
            self.contact_backend("CBF", combined)

    def combine(self):
        """Combine all available DBFs"""
        cbf = BloomFilter()
        for dbf in self.dbfs:
            cbf |= dbf
        return cbf

    def dbf_cycle(self):
        """Cycle DBFs"""
        # Reschedule this function.
        SCHED.enter(time.till_next(DBF_TIME), 2, self.dbf_cycle)
        # Create a new DBF. Also removes the oldest one if there are too many.
        self.dbfs.append(BloomFilter())
        log.log("Created new DBF")

    def add(self, EncID: "int"):
        """Adds EncID to the current DBF"""
        self.dbfs[-1].add(EncID)

    def contact_backend(self, type: "str", bf: "BloomFilter"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(self.serv_addr)
        sock.send(type.encode())
        sock.sendall(bf.filter.to_bytes(BloomFilter.FILTER_SIZE, "little"))
        resp = sock.recv(1024).decode()
        log.log((resp, "YELLOW", "UNDERLINE"))
        sock.close()

class ProgramStop(Exception):
    """Exception for program stop."""
