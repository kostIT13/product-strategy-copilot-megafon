"""Lightweight format metadata checks. Decoding and playback belong to the host."""

from io import BytesIO
import struct
import wave
from zlib import crc32

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_dimensions(data):
    if len(data) < 33 or data[:16] != PNG_SIGNATURE + b"\x00\x00\x00\x0dIHDR":
        raise ValueError("PNG screenshot header is invalid")
    if crc32(data[12:29]) != int.from_bytes(data[29:33], "big"):
        raise ValueError("PNG screenshot header checksum is invalid")
    width, height = struct.unpack_from(">II", data, 16)
    if not (1 <= width <= 8192 and 1 <= height <= 8192):
        raise ValueError("PNG screenshot dimensions exceed the supported bounds")
    return width, height


def wav_duration(data):
    try:
        with wave.open(BytesIO(data), "rb") as stream:
            frames, rate = stream.getnframes(), stream.getframerate()
            expected = frames * stream.getnchannels() * stream.getsampwidth()
            if (
                not rate
                or expected <= 0
                or expected > len(data)
                or len(stream.readframes(frames)) != expected
            ):
                raise ValueError("WAV has no complete PCM frames")
    except (wave.Error, EOFError) as error:
        raise ValueError("WAV must be a readable PCM capture") from error
    return frames * 1000 // rate


def _boxes(data, start, end):
    for _ in range(1024):
        if start == end:
            return
        if end - start < 8:
            raise ValueError("Truncated MP4 box header")
        size, kind = struct.unpack_from(">I4s", data, start)
        header = 8
        if size == 1:
            header = 16
            if end - start < header:
                raise ValueError("Truncated MP4 extended box header")
            size = struct.unpack_from(">Q", data, start + 8)[0]
        elif size == 0:
            size = end - start
        if not header <= size <= end - start:
            raise ValueError("MP4 box exceeds its container")
        yield kind, start + header, start + size
        start += size
    if start != end:
        raise ValueError("Too many MP4 boxes")


def mp4_duration(data):
    top = list(_boxes(data, 0, len(data)))
    kinds = {kind for kind, _, _ in top}
    movies = [(start, end) for kind, start, end in top if kind == b"moov"]
    if len(movies) != 1 or not {b"ftyp", b"mdat"} <= kinds or b"moof" in kinds:
        raise ValueError(
            "Use a local non-fragmented MP4 with movie metadata and media data"
        )
    movie = list(_boxes(data, *movies[0]))
    headers = [(start, end) for kind, start, end in movie if kind == b"mvhd"]
    if len(headers) != 1 or any(kind == b"mvex" for kind, _, _ in movie):
        raise ValueError("MP4 needs one non-fragmented movie header")
    start, end = headers[0]
    version = data[start] if start < end else -1
    if version == 0 and end - start >= 100:
        rate, ticks = struct.unpack_from(">II", data, start + 12)
        unknown = 0xFFFFFFFF
    elif version == 1 and end - start >= 112:
        rate, ticks = struct.unpack_from(">IQ", data, start + 20)
        unknown = 0xFFFFFFFFFFFFFFFF
    else:
        raise ValueError("Unsupported MP4 movie header")
    if not rate or not 0 < ticks < unknown:
        raise ValueError("MP4 movie duration is unavailable")
    for kind, start, end in movie:
        if kind != b"trak":
            continue
        for child, media_start, media_end in _boxes(data, start, end):
            if child != b"mdia":
                continue
            for tag, lo, hi in _boxes(data, media_start, media_end):
                if (
                    tag == b"hdlr"
                    and hi - lo >= 24
                    and data[lo + 8 : lo + 12] == b"vide"
                ):
                    return ticks * 1000 // rate
    raise ValueError("MP4 does not contain a declared video track")
