# Demo runbook: talking to Riya from the browser, in front of judges

The demo is **browser-based**: you (and the judges, on their own phones) open the site, tap **Call Riya**, and talk. It is the full
experience: streaming speech recognition, the human voice, barge-in, the live ticket. Put the **team console** (`/ops`) on the
projector while you talk: the judges watch the ticket, the AI's live notes, the tools, the approval gate and the memory update in real time.

> A real phone number (Twilio) is optional and **not part of this demo**: a Twilio *trial* account hangs up right after its announcement
> when the call is bridged to a two-way audio stream, and it only accepts verified callers anyway. See [Optional: real phone number](#optional-real-phone-number).

---

## Before you go on (T-5 minutes)

```powershell
.\start.ps1 -Tunnel                                      # 30 s after this, the model is loaded
backend\.venv\Scripts\python backend\scripts\preflight.py --reset
```
It should say `0 failure(s)` (a Twilio warning is fine). Then:

- **Laptop / projector:** `http://localhost:3000/ops/overview` (team console)
- **Customer side, on your laptop:** `http://localhost:3000` (pitch and benchmarks), `http://localhost:3000/talk` (call, chat, email)
- **Customer side, on a phone** (yours or a judge's): the `https://….ngrok-free.dev` address printed by the script. Tap *Visit Site* on ngrok's first-time notice, pick who you are calling as, tap **Call Riya**, allow the microphone. HTTPS is what lets the phone use its microphone.

Do **one** dry run of the hero call so the voice cache is warm. Keep the server running a few minutes after starting: it pre-generates ~100 stock phrases (acknowledgements like "hmm, one sec") with Gnani, so they play instantly.
Use headphones or keep the laptop speakers low (echo). If a judge calls from a phone while you talk from the laptop, expect the shared Gnani quota (a burst of ~3 requests per couple of seconds on a trial key) to slow both down: take turns.

---

## The 6-minute script

| # | You do | Judges see |
|---|---|---|
| 1 | Say: *"This is a support line where the AI resolves issues, and humans stay in the loop."* Show `/ops/overview` empty. | Live console: KPIs, agents idle |
| 2 | **Call Riya.** *"Hi, I was charged twice for the same order."* → *"The order ID is ORD 83921."* → *"Yes, refund the duplicate."* | Ticket appears the moment the call connects; routes to Billing; tools run; **Approval required (₹2,499)** card on the projector |
| 3 | Click **Approve** on the projector (you are the manager). Keep talking. | Riya, unprompted: *"It's done and confirmed, reference RFD-28192."* Ticket → RESOLVED, one-line + detailed summary written by the AI |
| 4 | New call: *"My Studio Headphones show a purple light and error P-77."* | Red banner: **A FIRST TIME BUG HAS BEEN REPORTED, please enter your suggestion**. Type: *"Hold the power button 15 seconds for recovery mode."* Riya relays it live |
| 5 | Mid-call, say to someone else: *"Mom, turn the TV down."* | The agent stays silent; the line shows "talking to someone else" |
| 6 | **Knowledge → drop a PDF/DOCX SOP** (prepare one: a 1-page policy). Then ask a question only that document answers. | The AI answers from the brand-new document. *Memory* shows the knowledge graph it built |
| 7 | Say: *"I want to speak to a manager."* | Real-time escalation: assignee, context document, Jira issue (labelled simulation) |
| 8 | End the call, then open **Emails** on the console. | The customer's summary email: what they asked, the verified refund reference, status, ticket number |

What to point out: the AI **never claims a refund is done until the refund service verified it**; every human action is an audit row and a learning signal; the second caller with the P-77 problem is answered from memory with no human.

---

## If something goes wrong

| Problem | Do this |
|---|---|
| Riya is quiet | Gnani rate limit: wait ~10 s, speak again; the site falls back to another voice automatically |
| Site hears nothing | Allow the microphone in the browser; or type in the box under the call panel |
| Phone shows a warning page | It is ngrok's first-visit notice: tap *Visit Site* |
| Tunnel address changed / site unreachable | Re-run `.\start.ps1 -Tunnel` |
| Model slow | Cloud LLM: set `CLOUD_LLM_*` in `.env` (Groq is fast and free) and `LLM_PREFER=cloud` |
| Total network loss | `Overview → Run demo` plays the scripted hero call through the real pipeline, no microphone or internet needed |

Reset between rehearsals: *Overview → Reset demo* (or `preflight.py --reset`). Stop everything: `.\stop.ps1`.

---

## Optional: real phone number

The telephony bridge (`/ws/telephony/twilio`, Twilio Media Streams, 8 kHz mu-law) is built and passes its tests against a simulated Twilio stream
(`backend\scripts\sim_phone_call.py`). It has **not** worked through a real Twilio *trial* account: Twilio fetches the webhook, plays its trial
announcement, then ends the call without ever opening the stream. To use it, you need a **paid (upgraded) Twilio account** with a number whose
*A call comes in* webhook is `https://<your-ngrok-address>/api/telephony/twilio/voice` (HTTP POST), and these lines in `backend\.env`:

```
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
PHONE_ALIASES=+91XXXXXXXXXX:CUS-20481   # your phone -> demo customer Lovekesh
```
Then call the number (or use *Settings → Phone → Call me*). `preflight.py` checks the number's webhook. Free-trial rules:
[Twilio free-trial limitations](https://help.twilio.com/articles/360036052753-Twilio-Free-Trial-Limitations).
