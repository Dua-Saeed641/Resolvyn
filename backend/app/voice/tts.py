"""Text-to-speech with a provider chain and an in-memory cache.

    Gnani (timbre-v2.5, Indian-accent female voices, also 8 kHz mu-law for phones)
      → edge-tts (free Microsoft neural voices, browser playback only)
      → the browser's own voice (the endpoint answers 503 and the front end takes over)

The cache matters: acknowledgements ("Mm-hmm, okay") are synthesised once and then served instantly,
which is what lets the agent answer within a few hundred milliseconds of the caller finishing a sentence.
"""

import asyncio
import hashlib
from collections import OrderedDict

import edge_tts

from app.config import BACKEND_DIR, get_settings
from app.voice import gnani
from app.voice.speech import FILLER_BANK

_MAX_ENTRIES = 600
CACHE_DIR = BACKEND_DIR / "data" / "tts_cache"


class TTSUnavailable(RuntimeError):
    pass


class TTS:
    def __init__(self) -> None:
        self.s = get_settings()
        self._cache: OrderedDict[str, bytes] = OrderedDict()
        self._inflight: dict[str, asyncio.Future] = {}
        self.error: str | None = None
        self.last_provider: str | None = None
        self._gnani_down_until = 0.0
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ── provider selection ───────────────────────────────────────────────────
    def providers(self, fmt: str) -> list[str]:
        want = self.s.tts_provider
        order = ["gnani", "edge"] if want in ("auto", "gnani") else ["edge", "gnani"]
        if want == "gnani":
            order = ["gnani"]
        out = []
        for p in order:
            if p == "gnani" and not gnani.configured():
                continue
            if p == "edge" and fmt != "mp3":
                continue  # edge-tts cannot produce phone mu-law
            out.append(p)
        return out

    def voice_name(self, provider: str, lang: str) -> str:
        if provider == "gnani":
            return f"gnani:{self.s.gnani_voice}"
        return self.s.tts_voice_hi if lang == "hi" else self.s.tts_voice_en

    async def _edge(self, text: str, lang: str) -> bytes:
        voice = self.voice_name("edge", lang)
        audio = bytearray()
        comm = edge_tts.Communicate(text, voice, rate=self.s.tts_rate)
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
        if not audio:
            raise TTSUnavailable("edge-tts returned no audio")
        return bytes(audio)

    # ── synthesis ────────────────────────────────────────────────────────────
    async def synth(self, text: str, lang: str = "en", fmt: str = "mp3") -> bytes:
        providers = self.providers(fmt)
        if not providers:
            raise TTSUnavailable("no text-to-speech provider available for " + fmt)
        key = hashlib.sha1(f"{providers[0]}|{self.voice_name(providers[0], lang)}|{fmt}|{text}".encode()).hexdigest()
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        disk = CACHE_DIR / f"{key}.bin"
        if disk.exists():  # survives restarts: every phrase is synthesised once, ever
            self._cache[key] = disk.read_bytes()
            return self._cache[key]
        if key in self._inflight:
            return await self._inflight[key]

        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._inflight[key] = fut
        try:
            data, err = None, None
            loop = asyncio.get_running_loop()
            for p in providers:
                if p == "gnani" and loop.time() < self._gnani_down_until:
                    continue
                try:
                    data = await (gnani.synth(text, lang, fmt) if p == "gnani" else self._edge(text, lang))
                    self.last_provider = p
                    break
                except Exception as e:  # noqa: BLE001 - try the next provider
                    err = e
                    if p == "gnani":
                        # down or auth error: skip Gnani briefly instead of paying a timeout per sentence
                        self._gnani_down_until = loop.time() + 5
            if data is None:
                raise TTSUnavailable(str(err)[:200] if err else "no provider")
            self._cache[key] = data
            if len(text) <= 120:  # short stock phrases only; long one-off replies are not worth the disk
                try:
                    disk.write_bytes(data)
                except OSError:
                    pass
            if len(self._cache) > _MAX_ENTRIES:
                self._cache.popitem(last=False)
            self.error = None
            fut.set_result(data)
            return data
        except Exception as e:  # noqa: BLE001
            self.error = str(e)[:200]
            fut.set_exception(e)
            fut.exception()  # mark retrieved so asyncio does not warn when nobody awaits
            raise
        finally:
            self._inflight.pop(key, None)

    async def warm(self, fmts: tuple[str, ...] = ("mp3", "mulaw8k")) -> None:
        """Pre-synthesise the acknowledgement bank (browser mp3 and phone mu-law) so those play instantly.

        Runs in the background, one phrase at a time, and steps aside whenever a call is live.
        """
        from app.services.sessions import sessions

        for fmt in fmts:
            if not self.providers(fmt):
                continue
            for lang, bank in FILLER_BANK.items():
                for phrases in bank.values():
                    for p in phrases:
                        while sessions.active_calls() > 0:
                            await asyncio.sleep(3)
                        try:
                            await self.synth(p, lang, fmt)
                        except Exception:  # noqa: BLE001
                            return  # offline / rate limited: the first real request will retry

    def status(self) -> dict:
        return {
            "engine": self.last_provider or (self.providers("mp3") or ["browser"])[0],
            "providers": self.providers("mp3"),
            "voice": self.voice_name((self.providers("mp3") or ["edge"])[0], "en"),
            "voice_en": self.voice_name("edge", "en"),
            "voice_hi": self.voice_name("edge", "hi"),
            "cached": len(self._cache),
            "error": self.error,
        }


tts = TTS()
