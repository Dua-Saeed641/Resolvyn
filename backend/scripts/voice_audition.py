"""Hear the candidate voices reading the same lines, then pick one.

  .venv\\Scripts\\python scripts\\voice_audition.py            # Gnani female voices -> scripts/audition/*.mp3
  .venv\\Scripts\\python scripts\\voice_audition.py Nalini Suhana

Put the winner in backend/.env as GNANI_VOICE=<name>. Also writes the edge-tts voice for comparison.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.voice import gnani  # noqa: E402
from app.voice.tts import tts  # noqa: E402

LINES = [
    "Hi Lovekesh! This is Riya from Nova Retail. How can I help you today?",
    "Oh no, twice? Ugh, sorry about that. Umm, what's the order ID? It starts with O R D.",
    "Okay, hang on, pulling that up... yeah, I can see it. Two charges, same amount, seconds apart. Want me to reverse the extra one?",
    "Acha, ek second, order ID bataiye, O R D se shuru hota hai.",
]
FEMALE = ["Nalini", "Kaveri", "Asmita", "Suhana", "Poorvi", "Shubhra"]


async def main() -> None:
    out = Path(__file__).parent / "audition"
    out.mkdir(exist_ok=True)
    s = get_settings()
    voices = sys.argv[1:] or FEMALE
    if gnani.configured():
        from gnani.tts import AudioConfig, GnaniTTSClient

        client = GnaniTTSClient(api_key=s.gnani_api_key)
        cfg = AudioConfig(sample_rate=24000, encoding="linear_pcm", container="mp3", bitrate="128k")
        for v in voices:
            audio = bytearray()
            for line in LINES:
                try:
                    audio += client.synthesize(line, voice=v, model=s.gnani_tts_model, language="en-IN", speed=1.0, audio_config=cfg)
                except Exception as e:  # noqa: BLE001
                    print(f"  {v}: {str(e)[:120]}")
                    break
                await asyncio.sleep(0.4)
            else:
                (out / f"gnani_{v}.mp3").write_bytes(bytes(audio))
                print(f"wrote {out / f'gnani_{v}.mp3'}")
    audio = bytearray()
    for line in LINES:
        audio += await tts._edge(line, "en")
    (out / "edge_NeerjaExpressive.mp3").write_bytes(bytes(audio))
    print(f"wrote {out / 'edge_NeerjaExpressive.mp3'}")


asyncio.run(main())
