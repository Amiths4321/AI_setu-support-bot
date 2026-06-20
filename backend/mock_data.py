"""
mock_data.py
------------
Synthetic customer accounts, transaction history, branches, and an FAQ
knowledge base. This stands in for what would normally come from the core
banking system (CBS) and a CMS-managed FAQ page — all fake, for demo
purposes only.

In a real deployment, get_customer() and get_transactions() would call the
bank's core banking API (e.g. Oracle FLEXCUBE) instead of this dictionary.
"""

import random
from datetime import datetime, timedelta

CUSTOMERS = {
    "DNS4512152591": {
        "name": "Rohan Shah",
        "phone_last4": "4821",
        "balance": 52353.28,
        "card_status": "ACTIVE",
        "card_last4": "7745",
        "branch": "Dombivli Main",
    },
    "DNS9366091555": {
        "name": "Priya Joshi",
        "phone_last4": "9012",
        "balance": 118420.50,
        "card_status": "ACTIVE",
        "card_last4": "3390",
        "branch": "Thane",
    },
    "DNS2834882395": {
        "name": "Suresh Pawar",
        "phone_last4": "5567",
        "balance": 7600.00,
        "card_status": "BLOCKED",
        "card_last4": "8801",
        "branch": "Kalyan",
    },
}

BRANCHES = [
    {"name": "Dombivli Main", "city": "Dombivli", "address": "Madhukunj, P-52, MIDC, Kalyan Shil Road",
     "hours": "10:00 AM – 4:00 PM (Mon–Sat)"},
    {"name": "Thane", "city": "Thane", "address": "Gokhale Road, Naupada", "hours": "10:00 AM – 4:00 PM (Mon–Sat)"},
    {"name": "Kalyan", "city": "Kalyan", "address": "Station Road, Kalyan West", "hours": "10:00 AM – 4:00 PM (Mon–Sat)"},
    {"name": "Ujjain", "city": "Ujjain", "address": "Teen Batti Chowk, Freeganj", "hours": "10:00 AM – 4:00 PM (Mon–Sat)"},
]

FAQS = [
    {
        "id": "faq_hours",
        "keywords": ["timing", "hours", "open", "close", "working hours"],
        "question": "What are your branch working hours?",
        "answer": "Branches are open 10:00 AM to 4:00 PM, Monday to Saturday. We're closed on Sundays and bank holidays.",
    },
    {
        "id": "faq_docs",
        "keywords": ["documents", "open account", "kyc", "account opening", "proof"],
        "question": "What documents do I need to open an account?",
        "answer": "You'll need a valid photo ID (Aadhaar/PAN/Passport), proof of address, and a recent passport-size photo. "
                  "PAN is mandatory for deposits above ₹50,000.",
    },
    {
        "id": "faq_interest",
        "keywords": ["interest rate", "fd rate", "fixed deposit", "savings rate"],
        "question": "What are your current interest rates?",
        "answer": "Savings accounts currently earn 3.5% p.a. Fixed deposit rates range from 6.25% to 7.75% p.a. "
                  "depending on tenure. Senior citizens get an additional 0.5%.",
    },
    {
        "id": "faq_neft",
        "keywords": ["neft", "rtgs", "transfer time", "fund transfer time"],
        "question": "How long does a fund transfer take?",
        "answer": "NEFT transfers settle in batches throughout the day, usually within 30 minutes. "
                  "RTGS (for amounts above ₹2 lakh) is near-instant during banking hours.",
    },
    {
        "id": "faq_minbalance",
        "keywords": ["minimum balance", "min balance", "balance requirement"],
        "question": "Is there a minimum balance requirement?",
        "answer": "Savings accounts require a minimum average balance of ₹1,000 (urban) or ₹500 (rural branches). "
                  "A small fee applies if the balance falls below this.",
    },
]


def set_card_status(account_no: str, status: str):
    """Updates a customer's card status in place. In a real deployment this
    would call the core banking system's card management API instead."""
    cust = get_customer(account_no)
    if cust:
        cust["card_status"] = status
        return True
    return False


def get_customer(account_no: str):
    return CUSTOMERS.get(account_no.strip().upper())


def verify_customer(account_no: str, phone_last4: str):
    cust = get_customer(account_no)
    if cust and cust["phone_last4"] == phone_last4.strip():
        return cust
    return None


def get_transactions(account_no: str, limit: int = 5):
    """Generates a plausible-looking mini statement on the fly."""
    cust = get_customer(account_no)
    if not cust:
        return []
    categories = ["UPI Transfer", "ATM Withdrawal", "POS Purchase", "NEFT Credit", "Bill Payment"]
    now = datetime.utcnow()
    txns = []
    for i in range(limit):
        amt = round(random.uniform(200, 9000), 2)
        is_credit = random.random() < 0.3
        txns.append({
            "date": (now - timedelta(days=i, hours=random.randint(0, 20))).strftime("%d %b, %I:%M %p"),
            "description": random.choice(categories),
            "amount": amt,
            "type": "CREDIT" if is_credit else "DEBIT",
        })
    return txns


def find_branches(city: str):
    city = city.strip().lower()
    return [b for b in BRANCHES if city in b["city"].lower()]


def search_faq(text: str):
    """Scores FAQs by total matched-keyword length rather than match count,
    so a specific phrase like 'account opening' outweighs a generic single
    word like 'open' that happens to appear in multiple FAQs' keyword sets."""
    text = text.lower()
    best, best_score = None, 0
    for faq in FAQS:
        score = sum(len(kw) for kw in faq["keywords"] if kw in text)
        if score > best_score:
            best, best_score = faq, score
    return best if best_score > 0 else None
