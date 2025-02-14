"""
The attacker main program.

Strategy:
Inject EphIDs into the backend and say they are covid positive.
 - Able to make people think they are infected when they aren't.
 - Does this by reconstructing real EphIDs from clients.
 - Mitigation is to make it not a self-report, but authorised at the backend.
   i.e. a doctor will authorise the upload of the CBF

Listen and track nodes across locations when they broadcast the same hash.
For the same location, if the port is the same, then the node must be the same.
"""

import socket
import struct
import threading
import log

STRUCT_FORMAT_STRING = "<B32s32s"
STRUCT_SIZE = struct.calcsize(STRUCT_FORMAT_STRING)

# Locations to sniff at.
locations = [50050, 50100, 60060]

# [(node_id, [(location, port)], {hashes}))]
tracker: "list[tuple[str, set[tuple[str, int]], set[bytes]]]" = []
node_id = 0

def new_id():
    global node_id
    node_id += 1
    return f"Node {node_id}"

def find_node(hash: "bytes", addr: "tuple[str, int]"):
    for node in tracker:
        if addr in node[1]:
            # Found the port matching.
            node[2].add(hash)
            return node[0]
        if hash in node[2]:
            # Found the hash matching.
            node[1].add(addr)
            return node[0]
    # not found
    tracker.append((new_id(), {addr}, {hash}))
    return tracker[-1][0]

def thread(sock: socket.socket):
    with sock:
        while True:
            raw, addr = sock.recvfrom(STRUCT_SIZE)
            idx, _, hash = struct.unpack(STRUCT_FORMAT_STRING, raw)
            log.log("Received (", (str(idx), "MAGENTA"), ", ", (hash[:4].hex(), "BLUE"), ")", " from ", (str(addr), "CYAN"), sep="")
            id = find_node(hash, addr)
            log.log("Associated", (hash[:4].hex(), "BLUE"), "with", (id, "RED"))

def main():
    for location in locations:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", location))
        threading.Thread(target=thread, args=(sock,), daemon=True).start()

    while True:
        pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.log("Stopping")
