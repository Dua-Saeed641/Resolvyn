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

    # Batch of 42 added to reach 10 resolved tickets per department, moulded from
    # the curated seed dataset and routed through the real swarm router.
    {"ticket_id": "PH-0801", "customer_id": "CUS-20481", "intent": "Shipping Delay", "department": "Order",
     "subject": "Delivery problem (Microsoft Surface)",
     "resolution": "The Microsoft Surface shipment was held at a courier hub. Escalated to the carrier, shared the new ETA, and it was delivered two days later."},
    {"ticket_id": "PH-0802", "customer_id": "CUS-20517", "intent": "Order Issue", "department": "Order",
     "subject": "Cancellation request (PlayStation)",
     "resolution": "The wrong item was received. Arranged a return pickup for PlayStation and dispatched the correct replacement under the wrong-item policy."},
    {"ticket_id": "PH-0803", "customer_id": "CUS-20481", "intent": "Shipping Delay", "department": "Order",
     "subject": "Delivery problem (Google Nest)",
     "resolution": "Contacted the carrier directly about the Google Nest shipment; it had been mis-routed and was redirected to the correct hub."},
    {"ticket_id": "PH-0804", "customer_id": "CUS-20517", "intent": "Shipping Delay", "department": "Order",
     "subject": "Delivery problem (Autodesk AutoCAD)",
     "resolution": "The Autodesk AutoCAD shipment was held at a courier hub. Escalated to the carrier, shared the new ETA, and it was delivered two days later."},
    {"ticket_id": "PH-0805", "customer_id": "CUS-20481", "intent": "Shipping Delay", "department": "Order",
     "subject": "Delivery problem (Sony Xperia)",
     "resolution": "Delay was a courier sorting backlog. Provided the updated tracking link for Sony Xperia and confirmed delivery once it moved."},
    {"ticket_id": "PH-0806", "customer_id": "CUS-20517", "intent": "Shipping Delay", "department": "Order",
     "subject": "Delivery problem (Roomba Robot Vacuum)",
     "resolution": "Contacted the carrier directly about the Roomba Robot Vacuum shipment; it had been mis-routed and was redirected to the correct hub."},
    {"ticket_id": "PH-0807", "customer_id": "CUS-20481", "intent": "Shipping Delay", "department": "Order",
     "subject": "Delivery problem (Sony PlayStation)",
     "resolution": "The Sony PlayStation shipment was held at a courier hub. Escalated to the carrier, shared the new ETA, and it was delivered two days later."},
    {"ticket_id": "PH-0808", "customer_id": "CUS-20517", "intent": "Refund Request", "department": "Billing",
     "subject": "Refund request (MacBook Pro)",
     "resolution": "Refund eligibility confirmed under policy; the MacBook Pro refund was issued and the reference number shared with the customer."},
    {"ticket_id": "PH-0809", "customer_id": "CUS-20481", "intent": "Payment Failure", "department": "Billing",
     "subject": "Payment issue (Google Pixel)",
     "resolution": "Payment failure was a gateway timeout. Retried the transaction with the customer on the line; the second attempt on Google Pixel succeeded."},
    {"ticket_id": "PH-0810", "customer_id": "CUS-20517", "intent": "Payment Failure", "department": "Billing",
     "subject": "Payment issue (LG OLED)",
     "resolution": "Card was declined by the issuing bank, not Nova Retail. Advised the customer to retry with a different payment method; the LG OLED order confirmed on retry."},
    {"ticket_id": "PH-0811", "customer_id": "CUS-20481", "intent": "Refund Request", "department": "Billing",
     "subject": "Refund request (Dell XPS)",
     "resolution": "Refund eligibility confirmed under policy; the Dell XPS refund was issued and the reference number shared with the customer."},
    {"ticket_id": "PH-0812", "customer_id": "CUS-20517", "intent": "Refund Request", "department": "Billing",
     "subject": "Refund request (Apple AirPods)",
     "resolution": "Verified the return had been received at the warehouse, then processed the Apple AirPods refund to the original payment method."},
    {"ticket_id": "PH-0813", "customer_id": "CUS-20481", "intent": "Payment Failure", "department": "Billing",
     "subject": "Payment issue (Samsung Soundbar)",
     "resolution": "Card was declined by the issuing bank, not Nova Retail. Advised the customer to retry with a different payment method; the Samsung Soundbar order confirmed on retry."},
    {"ticket_id": "PH-0814", "customer_id": "CUS-20517", "intent": "Payment Failure", "department": "Billing",
     "subject": "Payment issue (Microsoft Surface)",
     "resolution": "The Microsoft Surface payment had failed at the gateway but the amount was held, not charged. Confirmed with the bank statement and reassured the customer no charge would post."},
    {"ticket_id": "PH-0815", "customer_id": "CUS-20481", "intent": "Refund Request", "department": "Billing",
     "subject": "Refund request (Nintendo Switch)",
     "resolution": "Verified the return had been received at the warehouse, then processed the Nintendo Switch refund to the original payment method."},
    {"ticket_id": "PH-0816", "customer_id": "CUS-20517", "intent": "Account Access", "department": "Account",
     "subject": "Account access (Xbox)",
     "resolution": "Verified the customer's identity via registered email, then unlocked the Xbox account and sent a fresh password reset link."},
    {"ticket_id": "PH-0817", "customer_id": "CUS-20481", "intent": "Account Access", "department": "Account",
     "subject": "Account access (PlayStation)",
     "resolution": "Confirmed identity with the last four digits of the registered phone number; account was unlocked and a new sign-in link issued."},
    {"ticket_id": "PH-0818", "customer_id": "CUS-20517", "intent": "Account Access", "department": "Account",
     "subject": "Account access (Amazon Kindle)",
     "resolution": "The lockout was from repeated failed logins. Verified identity, reset the password, and confirmed sign-in worked before closing."},
    {"ticket_id": "PH-0819", "customer_id": "CUS-20481", "intent": "Account Access", "department": "Account",
     "subject": "Account access (Sony PlayStation)",
     "resolution": "Verified the customer's identity via registered email, then unlocked the Sony PlayStation account and sent a fresh password reset link."},
    {"ticket_id": "PH-0820", "customer_id": "CUS-20517", "intent": "Account Access", "department": "Account",
     "subject": "Account access (GoPro Action Camera)",
     "resolution": "Confirmed identity with the last four digits of the registered phone number; account was unlocked and a new sign-in link issued."},
    {"ticket_id": "PH-0821", "customer_id": "CUS-20481", "intent": "Account Access", "department": "Account",
     "subject": "Account access (HP Pavilion)",
     "resolution": "The lockout was from repeated failed logins. Verified identity, reset the password, and confirmed sign-in worked before closing."},
    {"ticket_id": "PH-0822", "customer_id": "CUS-20517", "intent": "Account Access", "department": "Account",
     "subject": "Account access (Fitbit Charge)",
     "resolution": "Verified the customer's identity via registered email, then unlocked the Fitbit Charge account and sent a fresh password reset link."},
    {"ticket_id": "PH-0823", "customer_id": "CUS-20481", "intent": "Account Access", "department": "Account",
     "subject": "Account access (Adobe Photoshop)",
     "resolution": "Confirmed identity with the last four digits of the registered phone number; account was unlocked and a new sign-in link issued."},
    {"ticket_id": "PH-0824", "customer_id": "CUS-20517", "intent": "Account Access", "department": "Account",
     "subject": "Account access (LG Washing Machine)",
     "resolution": "The lockout was from repeated failed logins. Verified identity, reset the password, and confirmed sign-in worked before closing."},
    {"ticket_id": "PH-0825", "customer_id": "CUS-20481", "intent": "Technical Issue", "department": "Technical",
     "subject": "Network problem (Amazon Echo)",
     "resolution": "The Amazon Echo issue matched a known firmware conflict. Walked the customer through a factory reset and re-pairing; resolved."},
    {"ticket_id": "PH-0826", "customer_id": "CUS-20517", "intent": "Technical Issue", "department": "Technical",
     "subject": "Data loss (Amazon Kindle)",
     "resolution": "Diagnosed a cached-data conflict on Amazon Kindle. Cleared local storage and reinstalled; the customer confirmed it was fixed."},
    {"ticket_id": "PH-0827", "customer_id": "CUS-20481", "intent": "Technical Issue", "department": "Technical",
     "subject": "Product compatibility (LG Washing Machine)",
     "resolution": "The LG Washing Machine fault was a loose connection/peripheral compatibility issue. Guided the customer through reseating the connection; resolved."},
    {"ticket_id": "PH-0828", "customer_id": "CUS-20517", "intent": "Technical Issue", "department": "Technical",
     "subject": "Hardware issue (Canon EOS)",
     "resolution": "The Canon EOS issue matched a known firmware conflict. Walked the customer through a factory reset and re-pairing; resolved."},
    {"ticket_id": "PH-0829", "customer_id": "CUS-20481", "intent": "Technical Issue", "department": "Technical",
     "subject": "Display issue (Samsung Soundbar)",
     "resolution": "Diagnosed a cached-data conflict on Samsung Soundbar. Cleared local storage and reinstalled; the customer confirmed it was fixed."},
    {"ticket_id": "PH-0830", "customer_id": "CUS-20517", "intent": "Technical Issue", "department": "Technical",
     "subject": "Installation support (Fitbit Charge)",
     "resolution": "The Fitbit Charge fault was a loose connection/peripheral compatibility issue. Guided the customer through reseating the connection; resolved."},
    {"ticket_id": "PH-0831", "customer_id": "CUS-20481", "intent": "Technical Issue", "department": "Technical",
     "subject": "Installation support (Google Pixel)",
     "resolution": "The Google Pixel issue matched a known firmware conflict. Walked the customer through a factory reset and re-pairing; resolved."},
    {"ticket_id": "PH-0832", "customer_id": "CUS-20517", "intent": "Technical Issue", "department": "Technical",
     "subject": "Product compatibility (Dell XPS)",
     "resolution": "Diagnosed a cached-data conflict on Dell XPS. Cleared local storage and reinstalled; the customer confirmed it was fixed."},
    {"ticket_id": "PH-0833", "customer_id": "CUS-20481", "intent": "General Query", "department": "Other",
     "subject": "Product recommendation (Google Nest)",
     "resolution": "Answered the Google Nest question directly from the product catalog and confirmed it matched what the customer needed."},
    {"ticket_id": "PH-0834", "customer_id": "CUS-20517", "intent": "General Query", "department": "Other",
     "subject": "Product recommendation (iPhone)",
     "resolution": "The customer wanted a recommendation between two options; compared specs against their stated use case for iPhone and suggested the better fit."},
    {"ticket_id": "PH-0835", "customer_id": "CUS-20481", "intent": "General Query", "department": "Other",
     "subject": "Product recommendation (Dyson Vacuum Cleaner)",
     "resolution": "General pre-sales question about Dyson Vacuum Cleaner; answered from the product catalog, no order or account action needed."},
    {"ticket_id": "PH-0836", "customer_id": "CUS-20517", "intent": "General Query", "department": "Other",
     "subject": "Product recommendation (Autodesk AutoCAD)",
     "resolution": "Answered the Autodesk AutoCAD question directly from the product catalog and confirmed it matched what the customer needed."},
    {"ticket_id": "PH-0837", "customer_id": "CUS-20481", "intent": "General Query", "department": "Other",
     "subject": "Product recommendation (Asus ROG)",
     "resolution": "The customer wanted a recommendation between two options; compared specs against their stated use case for Asus ROG and suggested the better fit."},
    {"ticket_id": "PH-0838", "customer_id": "CUS-20517", "intent": "General Query", "department": "Other",
     "subject": "Product recommendation (LG OLED)",
     "resolution": "General pre-sales question about LG OLED; answered from the product catalog, no order or account action needed."},
    {"ticket_id": "PH-0839", "customer_id": "CUS-20481", "intent": "General Query", "department": "Other",
     "subject": "Product recommendation (Nikon D)",
     "resolution": "Answered the Nikon D question directly from the product catalog and confirmed it matched what the customer needed."},
    {"ticket_id": "PH-0840", "customer_id": "CUS-20517", "intent": "General Query", "department": "Other",
     "subject": "Product recommendation (Lenovo ThinkPad)",
     "resolution": "The customer wanted a recommendation between two options; compared specs against their stated use case for Lenovo ThinkPad and suggested the better fit."},
    {"ticket_id": "PH-0841", "customer_id": "CUS-20481", "intent": "General Query", "department": "Other",
     "subject": "Product recommendation (Sony Xperia)",
     "resolution": "General pre-sales question about Sony Xperia; answered from the product catalog, no order or account action needed."},
    {"ticket_id": "PH-0842", "customer_id": "CUS-20517", "intent": "General Query", "department": "Other",
     "subject": "Product recommendation (GoPro Action Camera)",
     "resolution": "Answered the GoPro Action Camera question directly from the product catalog and confirmed it matched what the customer needed."},
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
