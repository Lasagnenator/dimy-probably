# Bloom filter implementation

import hashlib
import math

class BloomFilter(object):
    FILTER_SIZE = 100000
    HASH_ROUNDS = 3

    def __init__(self, byte_size = FILTER_SIZE, hash_rounds = HASH_ROUNDS, filter = 0):
        """
        Create a bloom filter with the given size (in bytes), hash rounds and optional initial filter.
        
        Default is 100 KB (800000 bits), 3 hash rounds and a filter starting at 0.
        """
        if filter.bit_length() > byte_size * 8:
            raise ValueError("Initial filter must be at most byte_size.")
        self.byte_size = byte_size
        self.bit_size = byte_size * 8
        self.digest_size = math.ceil(self.bit_size.bit_length() / 8)
        self.hash_rounds = hash_rounds
        self.filter = filter

    def generate_hashes(self, key: "int"):
        """Generate the hashes for the key."""
        key = str(key).encode()

        for i in range(self.hash_rounds):
            digest = hashlib.blake2b(key, digest_size=self.digest_size,
                key=str(i).encode()).digest()
            idx = int.from_bytes(digest, "little") % self.bit_size
            yield idx

    def add(self, key: "int"):
        """Add a key into the bloom filter."""
        for index in self.generate_hashes(key):
            self.filter |= 1 << index

    def query(self, key: "int"):
        """Whether this bloom filter contains the given key."""
        return key in self
    
    def __contains__(self, key: "int"):
        """Whether this bloom filter contains the given key."""
        checker = 0
        for index in self.generate_hashes(key):
            checker |= 1 << index
        return (checker & self.filter) == checker

    def __or__(self, other: "BloomFilter"):
        if not self.same_param(other):
            raise NotImplementedError("Filters must have the same starting parameters.")
        new_filter = self.filter | other.filter
        return BloomFilter(self.byte_size, self.hash_rounds, new_filter)
    
    def __and__(self, other: "BloomFilter"):
        if not self.same_param(other):
            raise NotImplementedError("Filters must have the same starting parameters.")
        new_filter = self.filter & other.filter
        return BloomFilter(self.byte_size, self.hash_rounds, new_filter)

    def same_param(self, other: "BloomFilter"):
        """Check that this bloom filter and the other were made with the same starting parameters."""
        # Attributes to check.
        attrs = ["byte_size", "hash_rounds"]
        flag = True
        for attr in attrs:
            flag &= getattr(self, attr) == getattr(other, attr)
        return flag
    
    def count(self):
        """Count number of set bits in this filter. Only efficient for sparse filters."""
        c = 0
        filter = self.filter
        while filter:
            c += 1
            filter &= filter - 1
        return c
