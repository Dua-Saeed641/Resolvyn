"""Deterministic mock data for the prototype (project.md §47-48, §70).

Internally consistent on purpose: the same customer, order and payment IDs
recur everywhere they are referenced. This is the only source of truth for
demo data — do not generate random values elsewhere in the backend.

Everything here backs the *simulated* enterprise APIs (app/tools/mock_apis.py).
"""

DEPARTMENTS = ["Technical", "Billing", "Account", "Order", "Other"]

CUSTOMERS = [
    {"customer_id": "CUS-20481", "name": "Lovekesh Anand", "email": "lovekesh.anand@example.com",
     "phone_last4": "4821", "plan": "Premium", "account_age_years": 3,
     "recent_sentiment": "Frustrated", "open_issues": 0, "previous_tickets": 7},
    {"customer_id": "CUS-20517", "name": "Dua Saeed", "email": "dua.saeed@example.com",
     "phone_last4": "3390", "plan": "Standard", "account_age_years": 1,
     "recent_sentiment": "Neutral", "open_issues": 0, "previous_tickets": 3},
]

# Customers that earlier versions of the demo seeded; removed on start so the console shows only the two above.
LEGACY_CUSTOMER_IDS = ["CUS-20633", "CUS-20702", "CUS-20790"]

ORDERS = {
    "ORD-83921": {"order_id": "ORD-83921", "customer_id": "CUS-20481", "item": "Wireless Earbuds Pro",
                  "amount": 2499, "placed": "2026-09-20", "status": "Confirmed",
                  "shipment_id": "SHP-5521"},
    "ORD-84010": {"order_id": "ORD-84010", "customer_id": "CUS-20517", "item": "Smart Kettle 1.7L",
                  "amount": 3199, "placed": "2026-09-08", "status": "Delivered",
                  "shipment_id": "SHP-5390"},
    "ORD-84102": {"order_id": "ORD-84102", "customer_id": "CUS-20481", "item": "Aluminium Laptop Stand",
                  "amount": 1899, "placed": "2026-09-14", "status": "Shipped",
                  "shipment_id": "SHP-5477"},
    "ORD-84155": {"order_id": "ORD-84155", "customer_id": "CUS-20517", "item": "Yoga Mat Pro",
                  "amount": 1299, "placed": "2026-09-24", "status": "Processing",
                  "shipment_id": None},
    "ORD-84230": {"order_id": "ORD-84230", "customer_id": "CUS-20481", "item": "Studio Headphones",
                  "amount": 4999, "placed": "2026-09-16", "status": "Delivered",
                  "shipment_id": "SHP-5488"},
}

# Two successful charges 38 seconds apart on the same card -> the hero duplicate-payment case.
PAYMENTS = {
    "ORD-83921": [
        {"transaction_id": "TXN-90112", "amount": 2499, "status": "SUCCESS", "method": "Card ****4821",
         "timestamp": "2026-09-20 10:41:03"},
        {"transaction_id": "TXN-90113", "amount": 2499, "status": "SUCCESS", "method": "Card ****4821",
         "timestamp": "2026-09-20 10:41:41"},
    ],
    "ORD-84010": [{"transaction_id": "TXN-88790", "amount": 3199, "status": "SUCCESS",
                   "method": "UPI", "timestamp": "2026-09-08 19:12:10"}],
    "ORD-84102": [{"transaction_id": "TXN-89544", "amount": 1899, "status": "SUCCESS",
                   "method": "Card ****4821", "timestamp": "2026-09-14 09:03:55"}],
    "ORD-84155": [{"transaction_id": "TXN-90201", "amount": 1299, "status": "SUCCESS",
                   "method": "UPI", "timestamp": "2026-09-24 08:20:31"}],
    "ORD-84230": [{"transaction_id": "TXN-89701", "amount": 4999, "status": "SUCCESS",
                   "method": "Card ****4821", "timestamp": "2026-09-16 21:44:02"}],
}

SHIPMENTS = {
    "SHP-5521": {"shipment_id": "SHP-5521", "carrier": "BlueDart", "status": "In transit",
                 "location": "Pune hub", "eta": "2026-09-27", "delayed": False},
    "SHP-5390": {"shipment_id": "SHP-5390", "carrier": "Delhivery", "status": "Delivered",
                 "location": "Delivered", "eta": "2026-09-10", "delayed": False},
    "SHP-5477": {"shipment_id": "SHP-5477", "carrier": "Ecom Express", "status": "Delayed",
                 "location": "Nagpur hub", "eta": "2026-09-28", "delayed": True,
                 "delay_reason": "Carrier sorting backlog"},
    "SHP-5488": {"shipment_id": "SHP-5488", "carrier": "BlueDart", "status": "Delivered",
                 "location": "Delivered", "eta": "2026-09-19", "delayed": False},
}

ACCOUNTS = {
    "CUS-20481": {"status": "ACTIVE", "failed_logins": 0},
    "CUS-20517": {"status": "LOCKED", "failed_logins": 5, "locked_reason": "Too many failed logins"},
}

# Historical, already-resolved tickets. They seed the *episodic* memory: the
# knowledge graph and the "past query" memory (docs/architecture.md §2.6).
HISTORY = [
    {"ticket_id": "PH-0783", "customer_id": "CUS-20481", "intent": "Order Issue", "department": "Order",
     "subject": "Order shows confirmed but no tracking link.",
     "resolution": "Tracking link is generated once the courier scans the parcel, usually within 24 hours; "
                   "the agent re-sent the tracking link by SMS."},
    {"ticket_id": "PH-0911", "customer_id": "CUS-20481", "intent": "Payment Verification", "department": "Billing",
     "subject": "Payment deducted but order not confirmed.",
     "resolution": "Payment gateway timeout. Payment was auto-reversed within 3 to 5 working days; "
                   "order was re-placed and confirmed."},
    {"ticket_id": "PH-0930", "customer_id": "CUS-20517", "intent": "Account Access", "department": "Account",
     "subject": "Cannot log in after several attempts.",
     "resolution": "Account was auto-locked after 5 failed logins. Identity verified with email and phone "
                   "last four digits; unlock link sent."},
    {"ticket_id": "PH-0955", "customer_id": "CUS-20481", "intent": "Shipping Delay", "department": "Order",
     "subject": "Parcel stuck at hub for three days.",
     "resolution": "Carrier sorting backlog. New ETA shared and courier escalated; parcel delivered in two days."},
    {"ticket_id": "PH-0978", "customer_id": "CUS-20481", "intent": "Technical Issue", "department": "Technical",
     "subject": "Bluetooth headphones will not pair.",
     "resolution": "Factory reset by holding power and volume-down for ten seconds, then re-pair from "
                   "phone Bluetooth settings. Resolved."},
    {"ticket_id": "PH-1002", "customer_id": "CUS-20517", "intent": "Refund Status", "department": "Billing",
     "subject": "Refund not received after return.",
     "resolution": "Refund was completed by the bank on day four; shared the refund reference and reminded "
                   "that UPI refunds take up to five working days."},
    {"ticket_id": "PH-1015", "customer_id": "CUS-20481", "intent": "Technical Issue", "department": "Technical",
     "subject": "App crashes on launch after update.",
     "resolution": "Cached data conflict. Clear app storage, reinstall, and sign in again. Resolved."},
    {"ticket_id": "PH-1031", "customer_id": "CUS-20517", "intent": "Order Issue", "department": "Order",
     "subject": "Wrong colour delivered.",
     "resolution": "Return pickup scheduled and replacement dispatched under the wrong-item policy."},
]

AGENTS = [
    {"name": "Technical", "status": "IDLE"},
    {"name": "Billing", "status": "IDLE"},
    {"name": "Account", "status": "IDLE"},
    {"name": "Order", "status": "IDLE"},
    {"name": "Other", "status": "IDLE"},
]

# Demo scripts (project.md §46-48): a scripted *customer* that goes through the
# real pipeline — nothing about the AI side is faked.
DEMO_SCENARIOS = {
    "duplicate_payment": {
        "customer_id": "CUS-20481",
        "title": "Duplicate payment → human-approved refund",
        "turns": [
            "Hi, I was charged twice for the same order and I want one of the payments refunded.",
            "My name is Lovekesh Anand and the order ID is ORD-83921.",
            "Yes, please go ahead and refund the duplicate one.",
            "Okay great, thank you so much.",
        ],
    },
    "first_time_bug": {
        "customer_id": "CUS-20481",
        "title": "First-time bug → manager suggestion → AI continues",
        "turns": [
            "Hello, my Studio Headphones show a flashing purple light and error code P-77 right after the firmware update.",
            "I'm Lovekesh Anand. I already tried charging them overnight.",
            "Okay, I tried that and it worked, the light is white now. Thanks!",
        ],
    },
    "side_talk": {
        "customer_id": "CUS-20517",
        "title": "Caller talks to someone else mid-call",
        "turns": [
            "Hi, I want to know where my order ORD-84155 is.",
            "Mom, can you turn the TV down a little? I'm on the phone.",
            "Sorry about that. So can I still cancel it?",
            "Yes please cancel it.",
            "No, that's all. Thanks!",
        ],
    },
}
