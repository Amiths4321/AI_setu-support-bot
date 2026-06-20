"""
nlu.py
------
A lightweight, fully offline intent classifier and entity extractor.

No external NLP/LLM API is used deliberately — this keeps the demo
runnable with zero API keys and zero cost, and (just as importantly for a
bank pitch) it means every classification decision is a traceable keyword
match, not an opaque model call. The same explainability principle from
the fraud-detection demo applies here: support staff can see exactly why
the bot routed a message the way it did.

Swapping this module for a real LLM-based NLU later is a drop-in
replacement — `detect_intent()` is the only function the rest of the app
depends on.
"""

import re

# Each pattern carries an explicit, hand-set weight rather than relying on
# raw matched-text length. This is deliberate: a generic word like
# "transaction" showing up inside a complaint sentence shouldn't be able
# to outscore the word "complaint" itself just because it's longer. Manual
# weights also mean a non-technical support-ops person can rebalance
# these later without touching the matching logic.
def _re(pattern):
    return re.compile(pattern, re.IGNORECASE)


INTENT_PATTERNS = {
    "GREETING": [
        (_re(r"\bhi\b"), 10), (_re(r"\bhello\b"), 10), (_re(r"\bhey\b"), 10),
        (_re(r"good (morning|afternoon|evening)"), 15),
    ],
    "HELP": [
        (_re(r"\bhelp\b"), 10), (_re(r"what can you do"), 20),
        (_re(r"\bmenu\b"), 10), (_re(r"\boptions\b"), 10),
    ],
    "BALANCE": [
        (_re(r"balance"), 25), (_re(r"how much money"), 20),
    ],
    "MINI_STATEMENT": [
        (_re(r"statement"), 25), (_re(r"transaction history"), 25),
        (_re(r"last\s+\d*\s*transactions?"), 25),
        (_re(r"transactions?"), 8),  # generic mention — weak signal on its own
    ],
    "BLOCK_CARD": [
        (_re(r"(lost|stolen|freeze).{0,20}card"), 35),
        (_re(r"card.{0,20}(lost|stolen)"), 35),
        # standalone word "block" only (word-boundary excludes "blocked",
        # which describes a *state*, not a request — see UNBLOCK_CARD)
        (_re(r"\bblock\b.{0,20}card"), 30), (_re(r"card.{0,20}\bblock\b"), 30),
    ],
    "UNBLOCK_CARD": [
        (_re(r"(unblock|activate|reactivate).{0,30}card"), 35),
        (_re(r"card.{0,30}(unblock|activate|reactivate)"), 35),
        (_re(r"\b(unblock|activate|reactivate)\b"), 25),  # strong even without "card" nearby
        (_re(r"\bblocked\b"), 15),  # "my card is blocked" usually precedes an unblock request
    ],
    "CHEQUE_BOOK": [
        (_re(r"cheque\s*book"), 40),
    ],
    "BRANCH_LOCATOR": [
        (_re(r"branch"), 20), (_re(r"\batm\b"), 15),
    ],
    "COMPLAINT": [
        (_re(r"complaint"), 35), (_re(r"\bissue\b"), 15), (_re(r"\bproblem\b"), 15),
        (_re(r"not working"), 25), (_re(r"raise a ticket"), 30), (_re(r"\bfailed\b"), 10),
    ],
    "GOODBYE": [
        (_re(r"\bbye\b"), 15), (_re(r"goodbye"), 20), (_re(r"thank(s| you)"), 15),
        (_re(r"that('s| is) all"), 20), (_re(r"no more questions"), 25),
    ],
}

# Intents that require us to look the customer up — handled specially by
# the dialogue manager, but flagged here so it knows to expect entities.
ACCOUNT_REQUIRED_INTENTS = {"BALANCE", "MINI_STATEMENT", "BLOCK_CARD", "UNBLOCK_CARD", "CHEQUE_BOOK"}

ACCOUNT_NO_RE = re.compile(r"\bDNS\d{6,12}\b", re.IGNORECASE)
PHONE_LAST4_RE = re.compile(r"\b\d{4}\b")

KNOWN_CITIES = ["dombivli", "thane", "kalyan", "ujjain", "mumbai", "pune", "indore"]


def classify_intent(text: str):
    """Returns (intent_label, score). Falls back to ('FAQ_OR_UNKNOWN', 0)
    if nothing matches strongly — the dialogue manager then tries the FAQ
    knowledge base before giving up entirely."""
    best_intent, best_score = "FAQ_OR_UNKNOWN", 0

    for intent, patterns in INTENT_PATTERNS.items():
        score = 0
        for pattern, weight in patterns:
            if pattern.search(text):
                score += weight
        if score > best_score:
            best_intent, best_score = intent, score

    return best_intent, best_score


def extract_entities(text: str):
    """Pulls out an account number, a 4-digit phone/verification code, and
    a known city name if present in the message. Any of these may be
    None if not found — the dialogue manager asks for what's missing."""
    entities = {"account_no": None, "phone_last4": None, "city": None}

    acc_match = ACCOUNT_NO_RE.search(text)
    if acc_match:
        entities["account_no"] = acc_match.group(0).upper()

    # Only treat a 4-digit number as a phone/verification code if it's not
    # part of the account number we already matched, to avoid double-using
    # the same digits for two different fields.
    remaining_text = text if not acc_match else text.replace(acc_match.group(0), "")
    phone_match = PHONE_LAST4_RE.search(remaining_text)
    if phone_match:
        entities["phone_last4"] = phone_match.group(0)

    text_lower = text.lower()
    for city in KNOWN_CITIES:
        if city in text_lower:
            entities["city"] = city.title()
            break

    return entities


def detect_intent(text: str):
    """Single entry point the rest of the app calls. Combines intent
    classification and entity extraction into one result."""
    intent, score = classify_intent(text)
    entities = extract_entities(text)
    return {
        "intent": intent,
        "confidence_signal": score,  # raw matched-character score, for debugging/logging
        "entities": entities,
    }
