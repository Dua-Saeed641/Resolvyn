"""Voice layer: phone audio codec, spoken-text humanizer, and the telephony bridge (fake speech providers)."""

import base64
import json
import time

from app.voice import speech
from app.voice.audio import mulaw_to_pcm16, pcm16_to_mulaw


def test_mulaw_roundtrip_is_close():
    pcm = b"".join(int(v).to_bytes(2, "little", signed=True) for v in (0, 100, -100, 1000, -1000, 8000, -8000, 30000, -30000))
    back = mulaw_to_pcm16(pcm16_to_mulaw(pcm))
    for i in range(0, len(pcm), 2):
        a = int.from_bytes(pcm[i:i + 2], "little", signed=True)
        b = int.from_bytes(back[i:i + 2], "little", signed=True)
        assert abs(a - b) <= max(40, abs(a) * 0.05)  # G.711 is lossy but close


def test_humanizer_removes_call_centre_phrasing():
    h = speech.humanize
    assert "frustration" not in h("I understand your frustration. Let me check that.")
    assert h("I will check that for you.") == "I'll check that for you."
    assert h("Certainly! I cannot do that.").startswith("Sure")
    assert "can't" in h("Certainly! I cannot do that.")
    assert h("Is there anything else I can help you with today?") == "Anything else I can sort out for you?"
    assert h("मैं आपकी मदद करूँगी") == "मैं आपकी मदद करूँगी"  # Hindi is left alone


def test_first_sentence_streams_out_immediately():
    st = speech.SentenceStreamer()
    out = st.feed("Oh no, twice? Ugh, sorry about that. Umm, what's the order ID?")
    assert out and out[0].startswith("Oh no")


def test_telephony_bridge_end_to_end_with_fake_speech(client, monkeypatch):
    """Twilio-style media stream in, mu-law audio out, ticket created for the caller identified by number."""
    from app.api import telephony
    from app.voice import gnani
    from app.voice.tts import tts

    class FakeListener:
        """Stands in for Gnani STT: after ~0.5 s of media frames it 'hears' the caller."""

        def __init__(self, language, sample_rate, *, on_transcript, on_speech_start=None, on_error=None):
            self.language = "en-IN"
            self.on_transcript = on_transcript
            self.frames = 0
            self.said = False

        async def start(self):
            return None

        async def feed(self, pcm):
            self.frames += len(pcm) // 320
            if self.frames > 25 and not self.said:
                self.said = True
                await self.on_transcript("Hi, my account is locked and I can't log in.")

        async def stop(self):
            return None

    async def fake_synth(text, lang="en", fmt="mp3"):
        return b"\xff" * 1600  # 200 ms of mu-law silence, standing in for speech

    monkeypatch.setattr(gnani, "Listener", FakeListener)
    monkeypatch.setattr(tts, "synth", fake_synth)

    with client.websocket_connect("/ws/telephony/twilio") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(json.dumps({"event": "start", "start": {"streamSid": "MZtest", "callSid": "CAtest", "customParameters": {"from": "+91 98765 33390"}}}))
        got_audio, deadline = False, time.time() + 20
        frame = base64.b64encode(b"\xff" * 160).decode()
        for _ in range(60):
            ws.send_text(json.dumps({"event": "media", "streamSid": "MZtest", "media": {"payload": frame}}))
        while time.time() < deadline and not got_audio:
            msg = json.loads(ws.receive_text())
            if msg.get("event") == "media":
                got_audio = base64.b64decode(msg["media"]["payload"]) == b"\xff" * 1600
        assert got_audio, "the agent's greeting should arrive as mu-law media frames"
        ws.send_text(json.dumps({"event": "stop"}))
    time.sleep(1.0)
    tickets = client.get("/api/tickets").json()
    mine = [t for t in tickets if t["customer_name"] == "Maya Patel" and t["channel"] == "Call"]  # 3390 -> Maya
    assert mine, "caller should be identified from the last four digits of the number"
    assert mine[0]["assigned_agent"] in ("Account", None)
    assert telephony  # module imported and routed


def test_twilio_webhook_returns_a_stream_twiml(client):
    r = client.post("/api/telephony/twilio/voice", data={"From": "+919876574821"})
    assert r.status_code == 200 and "<Stream url=" in r.text and "/ws/telephony/twilio" in r.text
    status = client.get("/api/telephony/status").json()
    assert status["webhook_url"].endswith("/api/telephony/twilio/voice")
