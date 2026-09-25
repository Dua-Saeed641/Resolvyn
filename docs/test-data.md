# Test data, and how to test end to end

Everything below is **simulated demo data** (`backend/data/seed_data.py`, `backend/data/sops/`). The enterprise APIs are
mocks; the knowledge is real in the sense that the AI genuinely retrieves from it. Replace or extend it with your own
(see [Bring your own data](#bring-your-own-data)).

## Who can call (customers)

| Customer ID | Name | Plan | Email | Phone ends | Notes |
|---|---|---|---|---|---|
| `CUS-20481` | Lovekesh Anand | Premium | lovekesh.anand@example.com | 4821 | The hero case: **duplicate payment** on the earbuds, a **delayed** laptop stand, and headphones for the **first-time bug** |
| `CUS-20517` | Dua Saeed | Standard | dua.saeed@example.com | 3390 | Account is **LOCKED** (5 failed logins), a yoga mat still **processing** (cancellable), a delivered kettle |

Their real addresses are set in `backend/.env` (`CUSTOMER_EMAILS=CUS-20481:...,CUS-20517:...`, git-ignored, applied on every start) and can also be changed in **Team console → Customers**. After every call or chat the customer is emailed a summary; the **Emails** page shows every message sent.

## Orders, payments, shipments

| Order | Customer | Item | Amount | Status | Payments | Shipment |
|---|---|---|---|---|---|---|
| `ORD-83921` | Lovekesh | Wireless Earbuds Pro | ₹2,499 | Confirmed | **2 successful charges** (`TXN-90112`, `TXN-90113`, 38 s apart, same card) | `SHP-5521` BlueDart, in transit, ETA 27 Sep |
| `ORD-84010` | Dua | Smart Kettle 1.7L | ₹3,199 | Delivered | 1 (UPI) | `SHP-5390` delivered |
| `ORD-84102` | Lovekesh | Aluminium Laptop Stand | ₹1,899 | Shipped | 1 (card ****4821) | `SHP-5477` Ecom Express, **delayed** (sorting backlog), ETA 28 Sep |
| `ORD-84155` | Dua | Yoga Mat Pro | ₹1,299 | **Processing** | 1 (UPI) | none yet |
| `ORD-84230` | Lovekesh | Studio Headphones | ₹4,999 | Delivered | 1 (card) | `SHP-5488` delivered |

The AI only discusses an order with the account that owns it (say another customer's order ID and it refuses).

## Knowledge already in the brain

Seed documents (`backend/data/sops/`, ingested exactly like an upload), divided per department agent:

| Document | Type | Department |
|---|---|---|
| Billing Refund Policy (duplicate charges, **₹1,000 approval limit**, timelines) | SOP | Billing |
| Payment Processing Guide (deducted-but-not-confirmed, failures, GST, plans) | Business logic | Billing |
| Account Recovery Policy (lock after 5 failures, identity check, reset link) | SOP | Account |
| Shipping and Returns Policy (timelines, delays, cancel, 7-day returns) | SOP | Order |
| Support Business Logic (escalation rules, Premium handling, hours) | Business logic | Order |
| Technical Troubleshooting Guide (Bluetooth pairing, app crash, charging, kettle, warranty) | SOP | Technical |
| Product Catalog (5 products, prices, warranties) | Product DB | Other (shared) |

Plus 8 **solved past tickets** (`PH-0783`, `PH-0911`, `PH-0930`, `PH-0955`, `PH-0978`, `PH-1002`, `PH-1015`, `PH-1031`) that seed the
episodic memory and the knowledge graph. Every ticket you resolve adds to them.

**Deliberately not in the brain** (so you can see a first-time bug): the error code **P-77** on the Studio Headphones.

## Things to say (each exercises a different path)

| Say | Path you should see |
|---|---|
| "I was charged twice for the same order." → order ID `ORD-83921` → "yes refund the duplicate" | Billing agent, tools, **human approval gate** (₹2,499 > ₹1,000), verified refund |
| "My account is locked and I can't log in." → "last four digits are 3390" → "yes unlock it" | Account agent, identity check, unlock, verified |
| "Where is my order ORD-84102?" | Order agent: delayed shipment, new ETA |
| "Can I cancel order ORD-84155?" → yes | Order agent: cancel, verified (only while *Processing*) |
| "My Studio Headphones show a purple light and error P-77." | **First-time bug**: banner on the manager screen, you type the fix, the AI relays it live |
| "I want to speak to a manager." | Real-time escalation: assignee, context doc, Jira (simulated) |
| Say something to someone else mid-call ("Mom, turn the TV down") | The agent stays silent |
| "How much is the Portable Speaker Mini?" / "How do I claim warranty?" | Instant answer from the documents (no tools) |
| Ask something the documents never mention | First-time bug |

Reset everything between runs from the team console: **Overview → Reset demo**.

## Bring your own data

Three ways, all feed the same memory (vector index + knowledge graph); each section is routed to the right department agent.

1. **Team console → Knowledge → Ingest.** Drop PDF / DOCX / MD / TXT / CSV / JSON, or paste text. Choose the type (SOP, business logic, product DB)
   and department, or leave *Auto*. The **Retrieval tester** shows what the AI would find for any caller sentence, and *Rulebook by department* shows
   who owns what.
2. **A whole folder at once:**
   ```powershell
   cd backend
   .venv\Scripts\python scripts\ingest_folder.py D:\my-company-docs                 # writes to the database (stop the API first)
   .venv\Scripts\python scripts\ingest_folder.py D:\my-company-docs --api http://localhost:8000   # or upload through the running API
   ```
   Sub-folders steer classification: `sop/`, `business_logic/`, `product_db/` set the type; `billing/`, `technical/`, `account/`, `order/` set the department.
3. **Teach it while it runs.** On any ticket: **TEACH** (a rule for a department) or **CORRECT**; answer a first-time-bug banner. All of it lands in the Solvable Rulebook.

Tips for good results: use clear headings (they become topics), keep one procedure per section, name files descriptively (the file name becomes the title),
and use the words your customers use. CSV rows are kept whole, one fact per row. Check **Memory** to see the knowledge graph it builds.

### Business data (orders, payments, shipments, customers)
What the agents say about an order comes from a real database (tables `business_orders`, `business_payments`, `business_shipments`, `business_accounts`,
plus customers), seeded with the demo records above. See and extend it in **Team console → Business data**: upload a CSV or JSON, the kind is detected from
the columns, existing IDs are updated, and the agents use it immediately.

| File | Needs at least these columns |
|---|---|
| Orders | `order_id,item` (also `customer_id,amount,placed,status,shipment_id`) |
| Payments | `transaction_id,order_id` (also `amount,status,method,timestamp`) |
| Shipments | `shipment_id,carrier` (also `status,location,eta,delayed,delay_reason`) |
| Customers | `customer_id,name` (also `email,phone_last4,plan`) |

Lookups are forgiving, like a caller: `ORD-83921`, `83921`, `O R D 8 3 9 2 1` or just the last digits all find the order (the **Order lookup tester** on that page shows what
the desk would find). If nothing matches, Riya says so plainly and asks for the ID again, or the registered email / last four digits of the phone; she never guesses,
never invents a delivery date, and never says "already reported" unless the memory really holds that report.
API: `GET /api/business/data`, `GET /api/business/orders/lookup?ref=`, `POST /api/business/import`. Connecting your live systems means replacing
`backend/app/tools/mock_apis.py` with real API calls.

## Test it from your phone

### A. Phone browser (fastest, no telephony account)
```powershell
.\start.ps1 -Tunnel        # needs ngrok installed and authenticated once: ngrok config add-authtoken <token>
```
It prints a public `https://….ngrok-free.dev` address. Open it on your phone (tap *Visit Site* on ngrok's first-time notice), choose who you are calling
as, tap **Call Riya**, allow the microphone. The team console is the same address plus `/ops` (open it on your laptop to watch the ticket, approve, and answer bugs).
HTTPS is what lets the phone use its microphone.

### B. A real phone call to a number (Twilio, paid account only)
A Twilio *trial* account hangs up after its announcement without opening the audio stream, so this needs an upgraded account. Use option A for demos.

1. Run `.\start.ps1 -Tunnel` (it sets `PUBLIC_BASE_URL` for you).
2. In Twilio, buy or use a voice-capable number → **Voice → A call comes in → Webhook, HTTP POST** →
   `https://<your-ngrok-address>/api/telephony/twilio/voice` (printed by the script, also in *Settings → Phone*).
3. Call the number. On a trial account you can only call from numbers you have verified, and calls to a US number from India are international calls.
4. To have your own number recognised as a demo customer, set in `backend/.env`:
   `PHONE_ALIASES=+91XXXXXXXXXX:CUS-20481` (comma-separate several). Otherwise Riya asks who you are.

No Twilio yet? `backend\scripts\sim_phone_call.py --base https://<your-ngrok-address>` simulates exactly what Twilio sends.

## Run it yourself

```powershell
.\start.ps1                # local only            .\start.ps1 -Tunnel   # + public URL for a phone
.\stop.ps1                 # stop everything and free the GPU/RAM
.\start.ps1 -Fresh         # wipe the database first (seed data and built-in SOPs are re-created)
```
Team console `http://localhost:3000/ops` · customer side `http://localhost:3000` · API docs `http://localhost:8000/docs`.
Add `-Dev` for the frontend dev server. Logs: `backend_run.log`, `engine/logs/`. Tests: `cd backend; .venv\Scripts\python -m pytest -q`.
