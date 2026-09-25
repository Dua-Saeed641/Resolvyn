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
    mine = [t for t in tickets if t["customer_name"] == "Dua Saeed" and t["channel"] == "Call"]  # 3390 -> Dua
    assert mine, "caller should be identified from the last four digits of the number"
    assert mine[0]["assigned_agent"] in ("Account", None)
    assert telephony  # module imported and routed


def test_twilio_webhook_returns_a_stream_twiml(client):
    r = client.post("/api/telephony/twilio/voice", data={"From": "+919876574821"})
    assert r.status_code == 200 and "<Stream url=" in r.text and "/ws/telephony/twilio" in r.text
    status = client.get("/api/telephony/status").json()
    assert status["webhook_url"].endswith("/api/telephony/twilio/voice")


def test_call_me_asks_twilio_to_dial_the_users_phone(client, monkeypatch):
    from app.api import telephony
    from app.config import get_settings

    s = get_settings()
    for k, v in dict(twilio_account_sid="ACtest", twilio_auth_token="tok", twilio_phone_number="+15550001111",
                     public_base_url="https://demo.example.dev").items():
        monkeypatch.setattr(s, k, v)
    sent = {}

    class FakeResp:
        status_code = 201
        text = "{}"

        def json(self):
            return {"sid": "CA123"}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, auth=None, data=None):
            sent.update(url=url, auth=auth, data=data)
            return FakeResp()

    monkeypatch.setattr(telephony.httpx, "AsyncClient", FakeClient)
    r = client.post("/api/telephony/call-me", json={"to": "+91 98765 43210"})
    assert r.status_code == 200 and r.json() == {"calling": "+919876543210", "call_sid": "CA123"}
    assert sent["url"].endswith("/Accounts/ACtest/Calls.json") and sent["auth"] == ("ACtest", "tok")
    assert sent["data"]["From"] == "+15550001111" and sent["data"]["To"] == "+919876543210"
    assert "Method" not in sent["data"] and "Twiml" not in sent["data"]  # trial accounts reject these
    assert sent["data"]["Url"] == "https://demo.example.dev/api/telephony/twilio/voice"
    assert client.get("/api/telephony/status").json()["call_me_ready"] is True


def test_call_me_is_refused_without_twilio_credentials(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "twilio_account_sid", None)
    r = client.post("/api/telephony/call-me", json={"to": "+919876543210"})
    assert r.status_code == 400 and "TWILIO_ACCOUNT_SID" in r.json()["detail"]


def test_outbound_call_identifies_the_person_who_was_dialled(client):
    """For a "Call me" call Twilio's From is our number and To is the person; the stream must carry To."""
    r = client.post("/api/telephony/twilio/voice", data={"Direction": "outbound-api", "From": "+15550001111", "To": "+919876543210"})
    assert 'name="from" value="+919876543210"' in r.text
    r = client.post("/api/telephony/twilio/voice", data={"Direction": "inbound", "From": "+919876500001", "To": "+15550001111"})
    assert 'name="from" value="+919876500001"' in r.text
