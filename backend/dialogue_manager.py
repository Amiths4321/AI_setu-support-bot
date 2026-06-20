"""
dialogue_manager.py
--------------------
Holds per-session conversation state and decides what the bot says next.

Design intent: sensitive actions (blocking a card, for instance) should
never happen off a single message. This manager enforces a real flow —
verify identity, then confirm the action — the same way a human agent
would, rather than letting one well-matched intent immediately trigger an
account change. That's a deliberate point for the bank pitch: the bot's
caution is a feature, not a missing capability.

Session state is kept in memory only (a dict keyed by session_id) — fine
for a demo; a real deployment would back this with Redis or similar so
state survives a server restart.
"""

import random
import string

import mock_data
from nlu import detect_intent, extract_entities, ACCOUNT_REQUIRED_INTENTS

MAIN_MENU_REPLIES = ["Check balance", "Block my card", "Find a branch", "Register a complaint"]
YES_NO_REPLIES = ["Yes", "No"]


class Session:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = "IDLE"
        self.pending_intent = None     # the account-required intent we're verifying identity for
        self.account_no = None
        self.phone_last4 = None
        self.verified_customer = None  # cached customer dict once verification succeeds
        self.complaint_text = None


SESSIONS = {}


def get_session(session_id: str) -> Session:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = Session(session_id)
    return SESSIONS[session_id]


def _reset_to_idle(session: Session):
    session.state = "IDLE"
    session.pending_intent = None
    session.account_no = None
    session.phone_last4 = None
    session.verified_customer = None
    session.complaint_text = None


def _reply(text, quick_replies=None, meta=None):
    return {"reply": text, "quick_replies": quick_replies or [], "meta": meta or {}}


def _gen_ticket_id():
    return "TKT" + "".join(random.choices(string.digits, k=6))


# ---------------------------------------------------------------------------
# Identity verification sub-flow — shared by every account-required intent
# ---------------------------------------------------------------------------

def _start_verification(session: Session, intent: str, entities: dict):
    session.pending_intent = intent
    session.account_no = entities.get("account_no")
    session.phone_last4 = None
    session.verified_customer = None

    if session.account_no and mock_data.get_customer(session.account_no) is None:
        session.account_no = None  # looked like an account number but isn't a real one

    if not session.account_no:
        session.state = "VERIFY_AWAIT_ACCOUNT"
        return _reply("Sure — to pull that up, can you share your account number? (e.g. DNS4512152591)")

    # If the phone digits were already given in the same message (e.g.
    # "check my balance, account DNS9366091555 phone 9012"), don't make
    # the customer repeat themselves — try verifying immediately.
    phone_candidate = entities.get("phone_last4")
    if phone_candidate:
        customer = mock_data.verify_customer(session.account_no, phone_candidate)
        if customer:
            session.verified_customer = customer
            return _route_verified_intent(session)
        # Digits present but didn't match — don't accuse the customer of
        # being wrong on unproven ambiguity (the 4 digits might not even
        # have been meant as a verification code); just ask normally.

    session.state = "VERIFY_AWAIT_PHONE"
    return _reply("Thanks. To verify it's you, what are the last 4 digits of your registered mobile number?")


def _continue_verification(session: Session, text: str):
    entities = extract_entities(text)

    if session.state == "VERIFY_AWAIT_ACCOUNT":
        account_no = entities.get("account_no") or text.strip()
        if mock_data.get_customer(account_no) is None:
            return _reply("I couldn't find that account number — could you double-check and re-enter it?")
        session.account_no = account_no.upper()
        session.state = "VERIFY_AWAIT_PHONE"
        return _reply("Thanks. And the last 4 digits of your registered mobile number?")

    if session.state == "VERIFY_AWAIT_PHONE":
        phone_last4 = entities.get("phone_last4") or "".join(ch for ch in text if ch.isdigit())[:4]
        customer = mock_data.verify_customer(session.account_no, phone_last4)
        if not customer:
            session.state = "VERIFY_AWAIT_ACCOUNT"
            session.account_no = None
            return _reply("Those details don't quite match our records. Let's try again — "
                          "what's your account number?")
        session.verified_customer = customer
        return _route_verified_intent(session)

    return None  # unreachable in practice


def _route_verified_intent(session: Session):
    intent = session.pending_intent
    cust = session.verified_customer
    name = cust["name"]

    if intent == "BALANCE":
        _reset_to_idle(session)
        return _reply(f"Thanks {name}, you're verified. Your available balance is ₹{cust['balance']:,.2f}.",
                      MAIN_MENU_REPLIES)

    if intent == "MINI_STATEMENT":
        txns = mock_data.get_transactions(session.account_no, limit=5)
        lines = [f"• {t['date']} — {t['description']} — {'+' if t['type']=='CREDIT' else '-'}₹{t['amount']:,.2f}"
                 for t in txns]
        _reset_to_idle(session)
        return _reply(f"Here are your last 5 transactions, {name}:\n" + "\n".join(lines), MAIN_MENU_REPLIES)

    if intent == "BLOCK_CARD":
        if cust["card_status"] == "BLOCKED":
            _reset_to_idle(session)
            return _reply(f"Your card ending {cust['card_last4']} is already blocked, {name}. "
                          "Nothing more to do there.", MAIN_MENU_REPLIES)
        session.state = "AWAIT_CONFIRM_BLOCK"
        return _reply(f"Thanks {name}, verified. Your card ending {cust['card_last4']} is currently "
                      f"{cust['card_status']}. Shall I go ahead and block it?", YES_NO_REPLIES)

    if intent == "UNBLOCK_CARD":
        if cust["card_status"] == "ACTIVE":
            _reset_to_idle(session)
            return _reply(f"Your card ending {cust['card_last4']} is already active, {name}.", MAIN_MENU_REPLIES)
        session.state = "AWAIT_CONFIRM_UNBLOCK"
        return _reply(f"Thanks {name}, verified. Your card ending {cust['card_last4']} is currently "
                      f"{cust['card_status']}. Shall I reactivate it?", YES_NO_REPLIES)

    if intent == "CHEQUE_BOOK":
        _reset_to_idle(session)
        return _reply(f"Done, {name} — a new cheque book has been requested for account {session.account_no}. "
                      "It'll be delivered to your registered address within 7 working days.", MAIN_MENU_REPLIES)

    _reset_to_idle(session)
    return _reply("Sorry, something went wrong continuing that request. Could you tell me again what you need?",
                  MAIN_MENU_REPLIES)


def _handle_confirmation(session: Session, text: str):
    answer = text.strip().lower()
    confirmed = answer in ("yes", "y", "confirm", "yeah", "yep", "go ahead")
    declined = answer in ("no", "n", "cancel", "nope")

    cust = session.verified_customer
    if session.state == "AWAIT_CONFIRM_BLOCK":
        if confirmed:
            mock_data.set_card_status(session.account_no, "BLOCKED")
            _reset_to_idle(session)
            return _reply(f"Done — your card ending {cust['card_last4']} has been blocked, and a replacement "
                          "has been logged. Anything else I can help with?", MAIN_MENU_REPLIES)
        if declined:
            _reset_to_idle(session)
            return _reply("No problem, I haven't blocked the card. Anything else I can help with?", MAIN_MENU_REPLIES)
        return _reply("Just to confirm — should I block the card? Please reply Yes or No.", YES_NO_REPLIES)

    if session.state == "AWAIT_CONFIRM_UNBLOCK":
        if confirmed:
            mock_data.set_card_status(session.account_no, "ACTIVE")
            _reset_to_idle(session)
            return _reply(f"Done — your card ending {cust['card_last4']} is now active again. "
                          "Anything else I can help with?", MAIN_MENU_REPLIES)
        if declined:
            _reset_to_idle(session)
            return _reply("No problem, the card stays as is. Anything else I can help with?", MAIN_MENU_REPLIES)
        return _reply("Just to confirm — should I reactivate the card? Please reply Yes or No.", YES_NO_REPLIES)

    return None  # unreachable in practice


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def handle_message(session_id: str, text: str) -> dict:
    session = get_session(session_id)
    text = (text or "").strip()
    if not text:
        return _reply("Sorry, I didn't catch that — could you type your question again?")

    # --- mid-flow states take priority over fresh intent detection ---
    if session.state in ("VERIFY_AWAIT_ACCOUNT", "VERIFY_AWAIT_PHONE"):
        result = _continue_verification(session, text)
        result["meta"] = {"state": session.state, "flow": "verification"}
        return result

    if session.state in ("AWAIT_CONFIRM_BLOCK", "AWAIT_CONFIRM_UNBLOCK"):
        result = _handle_confirmation(session, text)
        result["meta"] = {"state": session.state, "flow": "confirmation"}
        return result

    if session.state == "AWAIT_BRANCH_CITY":
        branches = mock_data.find_branches(text)
        session.state = "IDLE"
        if not branches:
            return _reply(f"I couldn't find a branch matching '{text}'. Try Dombivli, Thane, Kalyan, or Ujjain.",
                          MAIN_MENU_REPLIES)
        lines = [f"• {b['name']} — {b['address']} ({b['hours']})" for b in branches]
        return _reply("Here's what I found:\n" + "\n".join(lines), MAIN_MENU_REPLIES)

    if session.state == "AWAIT_COMPLAINT_DESC":
        ticket_id = _gen_ticket_id()
        _reset_to_idle(session)
        return _reply(f"Thanks — I've logged this as ticket {ticket_id}. Our support team will reach out "
                      "within 24 hours. Anything else I can help with?", MAIN_MENU_REPLIES)

    # --- fresh message: classify intent ---
    nlu_result = detect_intent(text)
    intent, entities = nlu_result["intent"], nlu_result["entities"]
    meta = {"intent": intent, "confidence": nlu_result["confidence_signal"], "entities": entities}

    if intent == "GREETING":
        result = _reply("Hi! I'm Setu, your DNS Bank assistant. I can help with balance checks, "
                        "card blocking, branch info, and more. What would you like to do?", MAIN_MENU_REPLIES)
    elif intent == "HELP":
        result = _reply("Here's what I can help with:\n"
                        "• Check your account balance\n• Show your last 5 transactions\n"
                        "• Block or unblock your debit card\n• Request a new cheque book\n"
                        "• Find a branch near you\n• Register a complaint", MAIN_MENU_REPLIES)
    elif intent in ACCOUNT_REQUIRED_INTENTS:
        result = _start_verification(session, intent, entities)
    elif intent == "BRANCH_LOCATOR":
        if entities.get("city"):
            branches = mock_data.find_branches(entities["city"])
            if branches:
                lines = [f"• {b['name']} — {b['address']} ({b['hours']})" for b in branches]
                result = _reply("Here's what I found:\n" + "\n".join(lines), MAIN_MENU_REPLIES)
            else:
                session.state = "AWAIT_BRANCH_CITY"
                result = _reply(f"I don't have a branch listed in {entities['city']} yet. "
                                "Which city are you looking in?")
        else:
            session.state = "AWAIT_BRANCH_CITY"
            result = _reply("Sure — which city are you looking in?")
    elif intent == "COMPLAINT":
        session.state = "AWAIT_COMPLAINT_DESC"
        result = _reply("Sorry to hear that. Could you briefly describe the issue you're facing?")
    elif intent == "GOODBYE":
        _reset_to_idle(session)
        result = _reply("Thanks for chatting with DNS Bank! Have a great day.")
    else:
        faq = mock_data.search_faq(text)
        if faq:
            result = _reply(faq["answer"], MAIN_MENU_REPLIES)
        else:
            result = _reply("I'm not fully sure I understood that. I can help with balance checks, "
                            "card blocking, branch info, cheque books, or complaints — "
                            "or I can connect you with a human agent.", MAIN_MENU_REPLIES + ["Talk to a human agent"])

    result["meta"] = meta
    return result
