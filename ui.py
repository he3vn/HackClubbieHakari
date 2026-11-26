#Idk why im calling this ui js performative more like terminal these are going to be like stuff that helps it write the msgs in slack

import os
import re

COIN = os.environ.get("COIN", "🪙")
GREEN = "#2ecc71"
RED = "#e74c3c"
GOLD = "#f1c40f"
BLUE = "#3498db"
GREY = "#95a5a6"
app = None
UNIT = 10 ** 18


def fmt(amount):
    return f"{COIN} {int(amount):,}"


def signed(amount):
    return f"{'+' if amount >= 0 else '-'}{fmt(abs(amount))}"


def stars(total):
    how_many = int(total) // UNIT
    if how_many <= 0:
        return ""
    return f"level {min(how_many, 9)} · "


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


_TAG_PATTERN =re.compile(r"⟦(\w+)⟧")


def tag(uid):
    return f"⟦{uid}⟧"


def lookup_name(uid, db=None, lock=None):
    import database
    return database.name_of(uid)


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
        return {key: render(value, use_pings, db, lock) for key, value in obj.items()}
    if isinstance(obj, list):
        return [render(value, use_pings, db, lock) for value in obj]
    return obj


def section(text, fields=None):
    block = {"type": "section", "text": {"type": "mrkdwn", "text": text}}
    if fields:
        block["fields"] = [{"type": "mrkdwn", "text": one_field} for one_field in fields]
    return block


def button(label, action_id, value="x", style=None):
    new_button = {
        "type": "button",
        "text": {"type": "plain_text", "text": label, "emoji": True},
        "action_id": action_id,
        "value": value,
    }
    if style:
        new_button["style"] = style
    return new_button


HELP_BUTTON = button("Help", "show_help")


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
        resultxc= True
    return result


def wire(message):
    return dict(message)


def plain_text(view):
    for attachment in (view.get("attachments") or []):
        for block in attachment.get("blocks") or []:
            text = (block.get("text") or {}).get("text")
            if text:
                return re.sub(r"[*_`]", "", text)[:300]
    return ""


def reply_ok(result):
    if result is None:
        return False
    status = getattr(result, "status_code", 200)
    body = getattr(result, "body", "")
    if isinstance(body, bytes):
        body = body.decode("utf-8", "ignore")
    body = str(body).strip().lower()
    if status != 200:
        return False
    if body in ("", "ok"):
        return True
    if '"ok":true' in body.replace(" ", "") or '"ok": true' in body:
        return True
    return '"ok": true' in body.replace("'", '"')


def swap(respond, view, client=None, body=None):
    message = wire(render(view, False))
    message.pop("nolog", None)
    message.pop("response_type", None)
    if not message.get("text"):
        message["text"] = plain_text(message)
    try:
        result = respond(replace_original=True, **message)
    except Exception as error:
        print("button update failed:", repr(error))
        result = None
    if reply_ok(result):
        return True

    print("button update was rejected by slack, posting it as a new message")
    if client is not None and body is not None:
        try:
            client.chat_postEphemeral(
                channel=(body.get("channel") or {}).get("id"),
                user=body["user"]["id"],
                text=message.get("text", ""),
                attachments=message.get("attachments"))
            return True
        except Exception as error:
            print("fallback message failed:", repr(error))
    return False


def only_you(respond, text, client=None, body=None):
    if client is not None and body is not None:
        channel = (body.get("channel") or {}).get("id")
        user = body["user"]["id"]
        try:
            client.chat_postEphemeral(channel=channel, user=user, text=text)
            return
        except Exception as error:
            print("ephemeral reply failed:", repr(error))
    try:
        respond(text=text, replace_original=False)
    except Exception as error:
        print("reply failed:", repr(error))


def respond_public(respond, text, use_pings=False, db=None, lock=None):
    respond(render(text, use_pings, db, lock), response_type="in_channel")



GIF_JACKPOT = ("https://giphy.com/gifs/jjk-jackpot-hakari-dance-DbH6HUoJMrPdHCI6Ce",
               "https://media.giphy.com/media/DbH6HUoJMrPdHCI6Ce/giphy.gif")
GIF_REPLY = ("https://giphy.com/gifs/jujutsu-kaisen-jjk-tybwaizen-ocBtGFDsOjlcp6aItx",
             "https://media.giphy.com/media/ocBtGFDsOjlcp6aItx/giphy.gif")
GIF_LOSS = ("https://giphy.com/gifs/pirate-token-fort-yIeBW3pl4TnTTyqQsj",
            "https://media.giphy.com/media/yIeBW3pl4TnTTyqQsj/giphy.gif")
GIF_AMOUNT = 200_000  #a win or a loss has to be at least this big for a gif


def play_gif(client, channel, gif, caption=None, thread_ts=None):
    if client is None or not channel:
        return False
    page_link, media_link = gif
    blocks = []
    if caption:
        blocks.append(section(caption))
    blocks.append({"type": "video", "video_url": media_link, "alt_text": caption or "gif",
                   "title": {"type": "plain_text", "text": caption or "gif"},
                   "thumbnail_url": media_link})
    try:
        client.chat_postMessage(channel=channel, text=f"{caption}\n{page_link}" if caption else page_link,
                                blocks=blocks, thread_ts=thread_ts)
        return True
    except Exception as error:
        print("gif could not be posted:", repr(error))
        try:
            client.chat_postMessage(channel=channel, text=f"{caption}\n{page_link}" if caption else page_link,
                                    thread_ts=thread_ts)
            return True
        except Exception as error2:
            print("gif fallback failed:", repr(error2))
            return False


def celebrate(uid, profit):
    import commands
    try:
        profit = int(profit)
    except (TypeError, ValueError):
        return
    if abs(profit) < GIF_AMOUNT:
        return
    client = getattr(commands.cur, "client", None)
    channel = getattr(commands.cur, "channel", None)
    if profit > 0:
        play_gif(client, channel, GIF_JACKPOT,
                 render(f"{tag(uid)} just won {fmt(profit)}!", False))
    else:
        play_gif(client, channel, GIF_LOSS,
                 render(f"{tag(uid)} just lost {fmt(abs(profit))}.", False))
