"""Domain lexicon shared by Jev (judgment), ingestion and retrieval.

Cheap, deterministic signals: they give Jev an answer in microseconds so the
agent can start speaking immediately, and act as the fallback when no LLM is
running (docs/claude.md).
"""

# Intent -> (department, trigger phrases). Longer phrases score higher.
INTENTS: dict[str, tuple[str, list[str]]] = {
    "Duplicate Payment": ("Billing", [
        "charged twice", "double charged", "charged two times", "duplicate payment", "duplicate charge",
        "deducted twice", "paid twice", "two payments", "two transactions", "billed twice", "charged again",
        "do baar paise", "paise do baar", "दो बार पैसे", "दो बार पेमेंट", "दो बार कट",
    ]),
    "Refund Status": ("Billing", [
        "refund not received", "where is my refund", "refund status", "haven't received my refund",
        "refund hasn't", "still waiting for refund", "refund pending", "refund delayed",
        "refund nahi aaya", "रिफंड नहीं आया", "रिफंड कब",
    ]),
    "Refund Request": ("Billing", [
        "want a refund", "need a refund", "want my money back", "money back", "refund", "reimburse",
        "refund chahiye", "paise wapas", "रिफंड चाहिए", "रिफंड", "पैसे वापस",
    ]),
    "Payment Failure": ("Billing", [
        "payment failed", "transaction failed", "payment declined", "money deducted", "amount deducted",
        "deducted but", "payment not going through", "upi failed", "card declined",
    ]),
    "Billing Query": ("Billing", [
        "invoice", "gst", "billing", "subscription", "bill", "charge", "payment", "price", "plan",
    ]),
    "Account Access": ("Account", [
        "can't log in", "cannot log in", "cant login", "unable to login", "unable to log in", "locked out",
        "account locked", "account is locked", "forgot password", "reset password", "password reset",
        "otp not", "can't sign in", "cannot sign in", "login", "log in", "sign in", "password", "locked",
        "login nahi", "password bhool", "account lock", "लॉगिन", "पासवर्ड", "अकाउंट लॉक",
    ]),
    "Profile Update": ("Account", [
        "change my email", "update my email", "change phone", "update phone", "change address",
        "update profile", "change my name", "close my account", "delete my account",
    ]),
    "Shipping Delay": ("Order", [
        "not delivered", "hasn't arrived", "has not arrived", "delayed", "delay", "where is my order",
        "where's my order", "where my order", "where is my parcel", "where is my package", "status of my order",
        "order status", "track my order", "track it", "tracking", "when will my order", "when will it arrive",
        "courier", "shipment", "still not here", "late delivery", "delivery",
        "order nahi aaya", "order abhi tak nahi", "kab aayega", "ऑर्डर नहीं आया", "डिलीवरी", "कब आएगा",
    ]),
    "Order Issue": ("Order", [
        "wrong item", "wrong colour", "wrong color", "damaged", "broken when", "missing item", "cancel my order",
        "cancel order", "cancel it", "return", "replace", "replacement", "exchange", "order",
        "cancel karna", "galat item", "कैंसल", "ऑर्डर",
    ]),
    "Technical Issue": ("Technical", [
        "not working", "doesn't work", "does not work", "stopped working", "error", "crash", "crashing",
        "bug", "glitch", "firmware", "bluetooth", "pair", "pairing", "battery", "charging", "won't turn on",
        "wont turn on", "flashing", "blinking", "light", "app", "update", "freezing", "stuck", "code",
        "not connecting", "won't connect", "no sound", "screen",
        "kaam nahi kar raha", "chal nahi raha", "काम नहीं कर रहा", "चल नहीं रहा",
    ]),
    "General Query": ("Other", [
        "store hours", "opening hours", "contact", "address of", "feedback", "complaint", "partnership",
        "job", "career", "hello", "hi", "thanks",
    ]),
}

# Department vocabulary for classifying ingested SOP chunks (uses stems/lowercase words).
DEPARTMENT_KEYWORDS: dict[str, list[str]] = {
    "Billing": [
        "refund", "payment", "charge", "charged", "invoice", "transaction", "billing", "gst", "subscription",
        "reimburse", "duplicate", "gateway", "upi", "card", "amount", "price", "pricing", "credit",
    ],
    "Account": [
        "account", "login", "log in", "password", "otp", "identity", "verify", "verification", "locked",
        "unlock", "profile", "email", "phone", "sign in", "security", "kyc",
    ],
    "Order": [
        "order", "shipping", "shipment", "delivery", "delivered", "courier", "tracking", "return", "replacement",
        "exchange", "cancel", "cancellation", "dispatch", "carrier", "warehouse",
    ],
    "Technical": [
        "troubleshoot", "error", "firmware", "reset", "bluetooth", "pair", "battery", "app", "crash", "install",
        "reinstall", "device", "led", "light", "connect", "connectivity", "software", "update", "cache", "bug",
    ],
}

SENTIMENT_NEGATIVE = [
    "annoyed", "angry", "furious", "upset", "frustrated", "frustrating", "terrible", "worst", "ridiculous",
    "unacceptable", "fed up", "useless", "waste", "pathetic", "disappointed", "irritated", "not happy",
    "horrible", "third time", "again and again", "sick of",
]
SENTIMENT_ANGRY = ["furious", "angry", "unacceptable", "ridiculous", "pathetic", "worst", "fed up", "scam", "cheat", "fraud"]
SENTIMENT_POSITIVE = ["thanks", "thank you", "great", "awesome", "perfect", "appreciate", "wonderful", "amazing", "helpful"]

URGENCY_HIGH = [
    "urgent", "asap", "immediately", "right now", "emergency", "as soon as possible", "today itself", "critical",
    "stuck abroad", "can't wait",
]

HUMAN_REQUEST = [
    "speak to a human", "talk to a human", "speak to a person", "real person", "human agent", "speak to a manager",
    "talk to a manager", "speak to someone", "supervisor", "customer care executive", "escalate", "manager",
]

# Phrases that mean the caller is talking to somebody else (docs/architecture.md §2.1).
SIDE_TALK_CUES = [
    "hold on a sec", "hold on a second", "one second mom", "one sec mom", "not you", "wasn't talking to you",
    "was not talking to you", "i'm talking to", "talking to my", "sorry, not you", "hey mom", "hey dad",
    "mom,", "mummy", "papa,", "bhaiya", "didi,", "beta,", "can you turn", "turn the tv", "turn down the",
    "dinner is", "are you coming", "come here", "put that down", "stop it", "what do you want for",
    "who's at the door", "who is at the door", "shut the door", "close the door", "take the call", "ek minute",
    "arre yaar", "kya kar raha", "kya kar rahi", "chai", "khana", "tum ruko", "ruko zara",
]

# Words that anchor an utterance to the support call (so it is *not* side talk).
ON_TOPIC_CUES = [
    "order", "refund", "payment", "charged", "account", "login", "password", "ticket", "delivery", "shipment",
    "cancel", "return", "app", "error", "email", "otp", "invoice", "issue", "problem", "help", "support",
    "riya", "nova", "yes", "yeah", "okay", "ok", "no", "please", "thanks", "thank you", "sorry about that",
    "go ahead", "sure", "correct", "right",
]

FILLER_WORDS = {"uh", "um", "umm", "uhh", "hmm", "hmmm", "like", "so", "well", "actually", "basically"}
