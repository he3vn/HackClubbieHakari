#Idk why im calling this ui js performative more like terminal these are going to be like stuff that helps it write the msgs in slack

import os
import re

COIN=os.environ.get("COIN","🪙")
#Colors for the bar on the messages might need to add hex codes.
GREEN="#2ecc71"
RED="#e74c3c"
GOLD="#f1c40f"
BLUE="#3498db"
GREY="#95a5a6"

_TAG_PATTERN = re.compile(r"⟦(\w+)⟧")
_name_cache = {}
app = None


def fmt(amount):
    return f"{COIN} {int(amount):,}"


def signed(amount):
    return f"{'+' if amount >= 0 else '-'}{fmt(abs(amount))}"


def ordinal(n):
    suffix = (
        "th" if 10 <= n % 100 <= 20
        else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    )
    return f"{n}{suffix}"


def tag(uid):
    return f"⟦{uid}⟧"


def lookup_name(uid, db, lock):
    if uid in _name_cache:
        return _name_cache[uid]
    try:
        info = app.client.users_info(user=uid)["user"]
        profile = info.get("profile", {})
        name = profile.get("display_name") or profile.get("real_name") or info.get("name")
        name = re.sub(r"[*_~`<>&|]", "", name or "").strip()
        if name:
            _name_cache[uid] = name
            return name
    except Exception:
        pass
    with lock:
        row = db.execute("SELECT name FROM users WHERE uid=?", (uid,)).fetchone()
    return row[0] if row and row[0] else "someone"


def render(obj, use_pings, db=None, lock=None):
    if isinstance(obj, str):
        def replace_tag(match):
            uid = match.group(1)
            if use_pings:
                return f"<@{uid}>"
            name = lookup_name(uid, db, lock)
            already_bold = obj.count("*", 0, match.start()) % 2 == 1
            return name if already_bold else f"*{name}*"
        return _TAG_PATTERN.sub(replace_tag, obj)
    if isinstance(obj, dict):
        return {k: render(v, use_pings, db, lock) for k, v in obj.items()}
    if isinstance(obj, list):
        return [render(v, use_pings, db, lock) for v in obj]
    return obj


def section(text, fields=None):
    block = {"type": "section", "text": {"type": "mrkdwn", "text": text}}
    if fields:
        block["fields"] = [{"type": "mrkdwn", "text": f} for f in fields]
    return block


def button(label, action_id, value="x", style=None):
    b = {
        "type": "button",
        "text": {"type": "plain_text", "text": label, "emoji": True},
        "action_id": action_id,
        "value": value,
    }
    if style:
        b["style"] = style
    return b


HELP_BUTTON = button("❓ Help", "show_help")


def embed(text, color=BLUE, fields=None, buttons=None, footer=None,
          response_type="ephemeral", nolog=False):
    blocks = [section(text, fields)]
    if footer:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": footer}],
        })
    if buttons:
        blocks.append({"type": "actions", "elements": buttons})
    result = {
        "text": text.replace("*", "")[:300],
        "attachments": [{"color": color, "blocks": blocks}],
    }
    if response_type:
        result["response_type"] = response_type
    if nolog:
        result["nolog"] = True
    return result


def _strip_text_key(msg):
    msg = dict(msg)
    if msg.get("attachments"):
        msg.pop("text", None)
    return msg


def swap(respond, view, db=None, lock=None):
    v = _strip_text_key(render(view, False, db, lock))
    respond(replace_original=True, **v)

def only_you(respond, text):
    respond(text=text, replace_original=False, response_type="ephemeral")
def respond_public(respond, text, use_pings=False, db=None, lock=None):
    respond(render(text, use_pings, db, lock), response_type="in_channel")
