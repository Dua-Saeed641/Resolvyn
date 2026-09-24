"""Tiny audio helpers for phone-grade audio (8 kHz G.711 mu-law), dependency-free.

`audioop` was removed in Python 3.13, so mu-law decoding uses a precomputed table.
"""


def _ulaw_to_pcm16(u: int) -> int:
    u = ~u & 0xFF
    sign = u & 0x80
    exponent = (u >> 4) & 0x07
    mantissa = u & 0x0F
    sample = ((mantissa << 3) + 0x84) << exponent
    sample -= 0x84
    return -sample if sign else sample


_TABLE = [_ulaw_to_pcm16(i) for i in range(256)]
_TABLE_BYTES = [v.to_bytes(2, "little", signed=True) for v in _TABLE]


def mulaw_to_pcm16(data: bytes) -> bytes:
    """8-bit mu-law -> 16-bit little-endian PCM (same sample rate)."""
    return b"".join(_TABLE_BYTES[b] for b in data)


def pcm16_to_mulaw(data: bytes) -> bytes:
    """16-bit little-endian PCM -> 8-bit mu-law (G.711)."""
    out = bytearray()
    for i in range(0, len(data) - 1, 2):
        s = int.from_bytes(data[i:i + 2], "little", signed=True)
        sign = 0x80 if s < 0 else 0
        s = min(abs(s), 32635) + 0x84
        exponent = 7
        mask = 0x4000
        while exponent > 0 and not (s & mask):
            exponent -= 1
            mask >>= 1
        mantissa = (s >> (exponent + 3)) & 0x0F
        out.append(~(sign | (exponent << 4) | mantissa) & 0xFF)
    return bytes(out)


def frames(data: bytes, size: int):
    """Yield fixed-size chunks (the last one is zero-padded)."""
    for i in range(0, len(data), size):
        chunk = data[i:i + size]
        yield chunk.ljust(size, b"\x00") if len(chunk) < size else chunk
