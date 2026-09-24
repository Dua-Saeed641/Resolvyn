"""Gnani (Vachana) speech: neural TTS and real-time STT with server-side VAD.

TTS  https://api.vachana.ai   REST, model timbre-v2.5 (female voices, English / Hindi / Hinglish, mp3 or 8 kHz mu-law)
STT  wss://api.vachana.ai/stt/v3/stream   PCM16 mono, 8 kHz (phone) or 16 kHz (browser), VAD + transcripts

The official SDK is synchronous for REST, so TTS runs in a worker thread. A 429 (rate limit) is retried
with a short back-off; anything else raises so the caller can fall back to another voice.
"""

import asyncio
import contextlib
import logging
from typing import Awaitable, Callable

from app.config import get_settings

logging.getLogger("gnani").setLevel(logging.WARNING)


class GnaniUnavailable(RuntimeError):
    pass


def configured() -> bool:
    return bool(get_settings().gnani_api_key)


# fmt -> AudioConfig kwargs
_FORMATS = {
    "mp3": dict(sample_rate=24000, encoding="linear_pcm", container="mp3", bitrate="64k"),
    "mulaw8k": dict(sample_rate=8000, encoding="pcm_mulaw", container="mulaw"),
    "wav16k": dict(sample_rate=16000, encoding="linear_pcm", container="wav"),
}
_LANG = {"en": "en-IN", "hi": "hi-IN"}


# The trial key allows a burst of ~3 requests that refills in ~2 s. Requests start at most every MIN_GAP
# seconds (globally), and a 429 waits for the bucket to refill instead of failing the sentence.
MIN_GAP = 0.75
_gap_lock: asyncio.Lock | None = None
_last_start = 0.0


def _synth_blocking(text: str, lang: str, fmt: str) -> bytes:
    from gnani.tts import APIError, AudioConfig, GnaniTTSClient

    s = get_settings()
    client = GnaniTTSClient(api_key=s.gnani_api_key)
    cfg = AudioConfig(**_FORMATS[fmt])
    last: Exception | None = None
    for attempt in range(4):
        try:
            audio = client.synthesize(
                text, voice=s.gnani_voice, model=s.gnani_tts_model, language=_LANG.get(lang, "en-IN"),
                speed=1.0, audio_config=cfg,
            )
            return bytes(audio)
        except APIError as e:
            last = e
            if e.status_code == 429 and attempt < 3:
                import time

                time.sleep(1.0)
                continue
            break
    raise GnaniUnavailable(str(last)[:200])


async def synth(text: str, lang: str = "en", fmt: str = "mp3") -> bytes:
    if not configured():
        raise GnaniUnavailable("GNANI_API_KEY is not set")
    global _gap_lock, _last_start
    if _gap_lock is None:
        _gap_lock = asyncio.Lock()
    loop = asyncio.get_running_loop()
    async with _gap_lock:  # only spaces the *start* of requests; they still run concurrently
        wait = _last_start + MIN_GAP - loop.time()
        if wait > 0:
            await asyncio.sleep(wait)
        _last_start = loop.time()
    try:
        return await asyncio.to_thread(_synth_blocking, text, lang, fmt)
    except GnaniUnavailable:
        raise
    except Exception as e:  # noqa: BLE001
        raise GnaniUnavailable(f"{type(e).__name__}: {e}"[:200]) from e


class Listener:
    """One live speech-to-text stream.

    Feed it raw PCM16 mono audio as it arrives (real-time cadence); it reports
    `on_speech_start` (VAD) and `on_transcript` (final text of an utterance).
    """

    FRAME = 1024  # bytes: 512 samples, the size the Gnani stream expects

    def __init__(
        self,
        language: str = "en",
        sample_rate: int = 16000,
        *,
        on_transcript: Callable[[str], Awaitable[None]],
        on_speech_start: Callable[[], Awaitable[None]] | None = None,
        on_error: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self.language = _LANG.get(language, "en-IN")
        self.sample_rate = sample_rate
        self.on_transcript = on_transcript
        self.on_speech_start = on_speech_start
        self.on_error = on_error
        self._client = None
        self._task: asyncio.Task | None = None
        self._buf = bytearray()
        self._closed = False
        self.transcripts = 0

    async def start(self) -> None:
        from gnani.stt import GnaniSTTStreamClient

        if not configured():
            raise GnaniUnavailable("GNANI_API_KEY is not set")
        self._client = GnaniSTTStreamClient(
            api_key=get_settings().gnani_api_key, language_code=self.language, sample_rate=self.sample_rate,
        )
        try:
            await self._client.connect()
        except Exception as e:  # noqa: BLE001
            raise GnaniUnavailable(f"STT connect failed: {e}"[:200]) from e
        self._task = asyncio.create_task(self._events())

    async def _events(self) -> None:
        from gnani.stt import StreamErrorEvent, StreamProcessingEvent, StreamTranscriptEvent

        try:
            async for ev in self._client:
                if isinstance(ev, StreamTranscriptEvent):
                    text = (ev.text or "").strip()
                    if text:
                        self.transcripts += 1
                        await self.on_transcript(text)
                elif isinstance(ev, StreamProcessingEvent):
                    if (ev.raw or {}).get("type") in ("speech_start", "vad_start") and self.on_speech_start:
                        await self.on_speech_start()
                elif isinstance(ev, StreamErrorEvent) and self.on_error:
                    await self.on_error(ev.message)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            if self.on_error:
                await self.on_error(f"{type(e).__name__}: {e}")

    async def feed(self, pcm: bytes) -> None:
        if self._closed or self._client is None:
            return
        self._buf.extend(pcm)
        while len(self._buf) >= self.FRAME:
            frame = bytes(self._buf[: self.FRAME])
            del self._buf[: self.FRAME]
            try:
                await self._client.send_audio(frame)
            except Exception:  # noqa: BLE001 - connection dropped: reconnect once, then drop frames
                if not await self._reconnect():
                    return

    async def _reconnect(self) -> bool:
        if self._closed:
            return False
        with contextlib.suppress(Exception):
            await self._client.close()
        if self._task:
            self._task.cancel()
        try:
            await self.start()
            return True
        except GnaniUnavailable as e:
            if self.on_error:
                await self.on_error(str(e))
            return False

    async def stop(self) -> None:
        self._closed = True
        if self._task:
            self._task.cancel()
        if self._client:
            with contextlib.suppress(Exception):
                await self._client.close()
