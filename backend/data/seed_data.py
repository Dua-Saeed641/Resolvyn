"""Deterministic mock data for the prototype (project.md §47-48, §70).

Internally consistent on purpose: the same customer, order, and refund IDs
recur everywhere they're referenced, per project.md §70 "Data realism".
This is the only source of truth for demo data — do not generate random
values elsewhere in the backend.
"""

CUSTOMERS = [
    {
        "customer_id": "CUS-20481",
        "name": "Aarav Sharma",
        "plan": "Premium",
        "account_age_years": 2,
        "previous_tickets": 7,
        "recent_sentiment": "Frustrated",
        "open_issues": 1,
    },
]

TICKETS = [
    {
        "ticket_id": "PH-1042",
        "customer_id": "CUS-20481",
        "subject": "I was charged twice for the same order and need one payment refunded.",
        "status": "ACTIVE",
        "intent": "Duplicate Payment",
        "sentiment": "Frustrated",
        "urgency": "Medium",
        "priority": "HIGH",
        "assigned_agent": "Billing Agent",
        "confidence": 96,
        "order_id": "ORD-83921",
    },
    {
        "ticket_id": "PH-1043",
        "customer_id": "CUS-20481",
        "subject": "Unable to access account.",
        "status": "RESOLVED",
        "intent": "Account Access",
        "sentiment": "Neutral",
        "urgency": "Low",
        "priority": "MEDIUM",
        "assigned_agent": "Account Agent",
        "confidence": 98,
        "order_id": None,
    },
    {
        "ticket_id": "PH-1044",
        "customer_id": "CUS-20481",
        "subject": "Refund not received.",
        "status": "WAITING_FOR_HUMAN",
        "intent": "Refund Status",
        "sentiment": "Frustrated",
        "urgency": "Medium",
        "priority": "MEDIUM",
        "assigned_agent": "Billing Agent",
        "confidence": 81,
        "order_id": "ORD-83921",
    },
    {
        "ticket_id": "PH-1045",
        "customer_id": "CUS-20481",
        "subject": "Shipment delayed.",
        "status": "ANALYZING",
        "intent": "Shipping Delay",
        "sentiment": "Neutral",
        "urgency": "Low",
        "priority": "LOW",
        "assigned_agent": "Logistics Agent",
        "confidence": 88,
        "order_id": "ORD-83921",
    },
    {
        "ticket_id": "PH-1046",
        "customer_id": "CUS-20481",
        "subject": "Product not functioning.",
        "status": "WAITING_FOR_HUMAN",
        "intent": "Technical Issue",
        "sentiment": "Neutral",
        "urgency": "Medium",
        "priority": "MEDIUM",
        "assigned_agent": "Technical Agent",
        "confidence": 74,
        "order_id": None,
    },
]

AGENTS = [
    {"name": "Billing Agent", "status": "ACTIVE"},
    {"name": "Account Agent", "status": "IDLE"},
    {"name": "Technical Agent", "status": "ACTIVE"},
    {"name": "Order Agent", "status": "ACTIVE"},
    {"name": "Logistics Agent", "status": "IDLE"},
]

KNOWLEDGE_DOCUMENTS = [
    {"title": "Billing Refund Policy", "category": "Billing", "referenced_in_tickets": 18},
    {"title": "Payment Processing Guide", "category": "Billing", "referenced_in_tickets": 12},
    {"title": "Account Recovery Policy", "category": "Product Information", "referenced_in_tickets": 9},
    {"title": "Shipping Policy", "category": "Orders", "referenced_in_tickets": 6},
    {"title": "Technical Troubleshooting Guide", "category": "Troubleshooting", "referenced_in_tickets": 11},
]
