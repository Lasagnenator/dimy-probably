"""
Shamir Secret Sharing. Wrapper around pycryptodome that supports more than 16 byte secrets.
Uses code from a current open pull request for such a feature in the main library.
https://github.com/Legrandin/pycryptodome/pull/593
Discussions about the security of the implementation are available on the pull request page
or on stackoverflow (https://crypto.stackexchange.com/questions/98243/is-it-secure-to-do-shamir-key-split-on-a-key-in-blocks-and-recombine)
which conclude that this implementation is as secure as the pycryptodome implementation.
"""

import itertools
from Crypto.Protocol.SecretSharing import Shamir
from Crypto.PublicKey import ECC
from hashlib import blake2b
from hmac import compare_digest
from typing import Tuple
import Ed25519

Share = Tuple[int, bytes]
Packet = Tuple[Share, int, bytes]

SHAMIR_BLOCK_SIZE = 16

def split(k: "int", n: "int", secret: "bytes", ssss=False) -> "list[Share]":
    """
    Wrapper for Shamir.split()
    when len(key) > SHAMIR_BLOCK_SIZE (16)
    """
    if not isinstance(secret, bytes):
        raise TypeError("Secret must be bytes")
    if len(secret) % SHAMIR_BLOCK_SIZE != 0:
        raise ValueError(f"Secret size must be a multiple of {SHAMIR_BLOCK_SIZE}")

    blocks = len(secret) // SHAMIR_BLOCK_SIZE
    shares = [b'' for _ in range(n)]
    for i in range(blocks):
        block_shares = Shamir.split(k, n,
                secret[i*SHAMIR_BLOCK_SIZE:(i+1)*SHAMIR_BLOCK_SIZE], ssss)
        for j in range(n):
            shares[j] += block_shares[j][1]
    return [(i+1,shares[i]) for i in range(n)]

def combine(shares: "list[Share]", ssss=False):
    """
    Wrapper for Shamir.combine()
    when len(key) > SHAMIR_BLOCK_SIZE (16)
    """
    share_len = len(shares[0][1])
    for share in shares:
        if len(share[1]) % SHAMIR_BLOCK_SIZE:
            raise ValueError(f"Share #{share[0]} is not a multiple of {SHAMIR_BLOCK_SIZE}")
        if len(share[1]) != share_len:
            raise ValueError("Share sizes are inconsistent")
    blocks = share_len // SHAMIR_BLOCK_SIZE
    result = b''
    for i in range(blocks):
        block_shares = [
                (int(idx), share[i*SHAMIR_BLOCK_SIZE:(i+1)*SHAMIR_BLOCK_SIZE]) 
            for idx, share in shares]
        result += Shamir.combine(block_shares, ssss)
    return result

def generate(k: "int", n: "int") -> "list[Packet]":
    """Returns [(shares, secret, hash)]"""
    key = ECC.generate(curve="Ed25519")
    public = Ed25519.compress_key(key.pointQ)
    h = blake2b(public, digest_size=32).digest()

    return list(zip(split(k, n, public), itertools.repeat(key.d), itertools.repeat(h)))

def verify(shares: "list[Share]", hash: "bytes"):
    """
    Returns the reconstructed secret if it matches with the given hash.
    False otherwise.
    """
    shared = combine(shares)
    shared_hash = blake2b(shared, digest_size=32).digest()
    if compare_digest(hash, shared_hash):
        return shared
    return False

def calc_shared(public: "bytes", secret: "int") -> "int":
    # Calculate the shared as the x component of the point.
    return int((Ed25519.decompress_key(public) * secret).x)
