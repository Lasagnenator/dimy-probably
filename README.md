# dimy-probably
Modified DIMY protocol implemented based on "DIMY: Enabling Privacy-preserving Contact Tracing" by Nadeem Ahmed et al. Done as a university project. Everything except `Ed25519.py` and `sss.py` is my own code. See those file headers for more information.

# How to Run

## Set up environment
* Install Python 3
* Install required packages with `pip3 install -r requirements.txt`

## Running the server
`python3 DimyServer.py port` where `port` is the port to run on. The server binds to the address `0.0.0.0` and is intended to be run on the same machine as the client nodes.

## Running the client
`python3 Dimy.py ip port cmd` where `ip`/`port` is the ip address and port of the backend server and `cmd` is the path to the command file to use for this client.

## Running the attacker
`python3 Attacker.py` and modify the `locations` variable inside the code to tetst different scenarios. These locations should be the same as the ones that the command files use in the MOVE command. This is a sample attacker to demonstrate a potential vulnerability being exploited in the system.

# Summary
This project fully implements the simplified implementation (notably no blockchain is used) of the DIMY protocol as specified in the assignment. Features include ephemeral identifiers used to create shared secrets securely between nodes. This specific implementation utilises port based location splitting and command files to make simulations easy to run. UDP was used rather than the BLE specified in the original paper.

# Potential Improvements
A possible improvement that could be made is the implementation of simultaneous advertisement
because in the current implementation, it is very easy for slightly offset share broadcasts to never
encounter each other. Simultaneous advertisement can be done by having a pair of EphIDs with
their generation cycle offset by half the time it takes to fully broadcast all shares.

An extension to the application would be to have dynamically sized bloom filters. This means that in
periods of many encounters, the bloom filters will maintain a low false positive rate and in periods of
low encounters, memory usage is kept to a minimum. Such filters would be realised by having a list
of bloom filters and after adding some elements, a new bloom filter will be added to the list.
Membership tests remain at a low false positive rate and memory usage scales linearly with
encounters. This would allow us to find the optimal solution for the circumstances at hand to the
design tradeoff discussed above.

# Attack
It is not feasible to create any EncID if the private key of a node is not known. The point of ECC is
that the private key is not known given only the public key, which is what is advertised from the
shares. An attacker advertising a copy of a public key from another node will not be useful as the
two nodes will not share a secret number and thus will not have the same EncID. With a sufficiently
large quantum computer, private key recovery is possible. This would allow someone to generate
the same EncIDs as a user if they listen to the public keys. These could be added to a query bloom
filter to check if the user has tested positive to covid, since there would be a match for all their
EncIds. Fortunately, for now this attack remains theoretical as a sufficiently large quantum computer
does not exist. Furthermore, even if the attacker can get the private key of a client, the keys are
regenerated every 15 seconds so it would only be an issue in a post-quantum environment with very
accessible quantum computers.

If the attacker can read the CBFs being uploaded by clients, they cannot gather the shared secret
numbers because the EncID is hashed to get indices for the set bits. Even if it were possible to
gather the shared secret, it would be impossible to find the private keys of clients.
The attack implemented in our code is to trace client nodes based on the hashes they advertise and
the port / address they broadcast from. For example, if a share is broadcast with the same hash
from a different address tuple, then it is still from the same client node. If a share is broadcast from
the same address tuple then it’s the same node again. Using this, it should be possible to trace
which nodes broadcast what. The simple way to prevent this attack from working is to create a new
socket / assign to a new port each broadcast.

An attack that is definitely possible in regard to the communication with the backend server is that
the attacker can upload arbitrary CBFs with no restrictions as the server has no way of knowing if
the CBF is genuine. Thus an attacker could upload a filled bloom filter and make every single QBF
upload match as positive. Doing so would make everyone get a message saying the tested positive.
A potential solution to this problem is to only authorise medical professionals to upload CBFs. For
example a hospital could download the CBF from a positive client and upload it themselves with
some secure authorisation/authentication method to the backend server.

# Demo
https://youtu.be/dWP3Yw9qzmk
