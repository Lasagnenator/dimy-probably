"""
The following code has been adapted from https://ed25519.cr.yp.to/python/ed25519.py
The main purpose here is to decompress points.
"""

__all__ = ["compress_key", "decompress_key"]

from Crypto.PublicKey import ECC

b = 256
q = 2**255 - 19
l = 2**252 + 27742317777372353535851937790883648493

def inv(x: int) -> int:
    return pow(x, q - 2, q)

d = -121665 * inv(121666)
I = pow(2, (q - 1) // 4, q)

def xrecover(y: int) -> int:
    xx = (y * y - 1) * inv(d * y * y + 1)
    x = pow(xx, (q + 3) // 8, q)
    if (x*x - xx) % q != 0:
        x = (x * I) % q
    if x % 2 != 0:
        x = q - x
    return x

def compress(x: int, y: int) -> int:
    return y << 1 | (x & 1)

def compress_key(point: ECC.EccPoint) -> bytes:
    """Compress a point"""
    return compress(int(point.x), int(point.y)).to_bytes(32, "little")

def decompress_key(key_byte: bytes) -> ECC.EccPoint:
    """Decompress a point"""
    key = int.from_bytes(key_byte, "little")
    x_odd = key & 1
    y = key >> 1
    x = xrecover(y)
    if x & 1 != x_odd:
        x = q - x
    return ECC.EccPoint(x, y, "Ed25519")
