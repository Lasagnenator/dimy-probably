"""
The backend main program.
"""

import socket
from bloom import BloomFilter
import log

class Backend(object):
    def __init__(self, port: "int"):
        """
        Create the backend server at the given ip and port.
        Generate a bloom filter and socket.
        """
        self.bf = BloomFilter()
        self.port = port

    def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("", self.port))
        sock.listen(10)
        log.log("Server started on port", (str(self.port), "GREEN"))
        while True:
            # Listen and receive a BF from a client.
            conn, addr = sock.accept()
            # See if a CBF or QBF is being sent.
            type = conn.recv(3).decode()
            # Receive the BF
            filter = int.from_bytes(self.recv(conn, BloomFilter.FILTER_SIZE), "little")
            client_bf = BloomFilter(filter=filter)

            if (type == "CBF"):
                # Add the CBF to the existing BF of contacts.
                self.bf |= client_bf
                conn.send(b"Server: Contact Bloom Filter received.")
                log.log("Contact Bloom Filter received from", (str(addr), "BLUE"))
            else:
                log.log("Doing match analysis on Query Bloom Filter from", (str(addr), "BLUE"))
                # Check
                if (self.bf & client_bf).count() >= BloomFilter.HASH_ROUNDS:
                    conn.send(b"Server: You have been in contact with a positive case.")
                    log.log("Node at ", (str(addr), "BLUE"), " has been in contact with a ", ("positive", "RED"), " case.", sep="")
                else:
                    conn.send(b"Server: No contact with a positive case was detected.")
                    log.log("Node at ", (str(addr), "BLUE"), " has ", ("no detection", "GREEN"), ".", sep="")

            conn.close()

    def recv(self, sock: "socket.socket", length: "int"):
        """Get a specific length from the connection"""
        data = [b""]
        so_far = 0
        while so_far < length:
            data.append(sock.recv(length - so_far))
            so_far += len(data[-1])
        return b"".join(data)

