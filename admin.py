#This is my panel lol i can do wtv i want here ima add some good ass commands hopefully
#So every admin command is under /admin, like /admin add-money @user 1000

import time
import database as db_module
import ui
from commands import ADMINS, cmd, game_history, parse_amount, parse_user

ADMIN_HELP = (
    "*Admin commands*\n"
    "`add-money @user <amount>`: give coins to a player\n"
    "`create-item <name> <price> <description>`: put an item in the shop\n"
    "`delete-item <name>`: remove an item from the shop\n"
    "`audit @user`: see someone's last money moves\n"
    "`set-decks <1-8>`: how many decks blackjack uses\n"
    "`set-cooldown <usages> <duration>`: games allowed per time window (e.g. `4 5m`)\n"
    "`nuke @user`: wipe their cash and bank\n"
    "`nuke all confirm`: wipe EVERYONE's cash and bank\n"
    "`cap @user <amount>` / `cap all <amount>`: cut total coins down to the amount (cash first)\n"
    "`set @user <cash> [bank]` · `take @user <amount|all>` · `giveall <amount>` (cash to everyone)\n"
    "`undo`: restore the last nuke/cap/set/take\n"
    "`resetcd @user|all`: clear cooldowns\n"
    "`ban @user` / `unban @user`: block from the economy · `info @user`: balance\n"
    "`item-remove <name>`: delete an item (same as `delete-item`)")


def snapshot(user_ids):
    with db_module.lock:
        db_module.db.execute("DELETE FROM snap")
        for user_id in user_ids:
            cash, bank = db_module.get_user(user_id)
            db_module.db.execute("INSERT INTO snap VALUES (?,?,?)", (user_id, str(cash), str(bank)))
        db_module.db.commit()


def set_money(user_id, cash, bank):
    old_cash, old_bank = db_module.get_user(user_id)
    db_module.change_money(user_id, cash=db_module.keep_inside_limit(cash) - old_cash,
                           bank=db_module.keep_inside_limit(bank) - old_bank)


def all_user_ids():
    with db_module.lock:
        return [row[0] for row in db_module.db.execute("SELECT uid FROM users").fetchall()]


def cap_total(user_id, amount):
    cash, bank = db_module.get_user(user_id)
    if cash + bank <= amount:
        return False
    new_cash = min(cash, amount)
    set_money(user_id, new_cash, min(bank, amount - new_cash))
    return True


def add_money(args):
    if len(args) < 2 or not parse_user(args[0]):
        return "How do i use: `/admin add-money @user <amount>`"
    amount = parse_amount(args[1], db_module.MAX_COINS)
    if amount is None:
        return "How to use: `/admin add-money @user <amount>`"
    db_module.change_money(parse_user(args[0]), cash=amount)
    return f"Added {ui.fmt(amount)} to {ui.tag(parse_user(args[0]))}."


def create_item(args):
    if len(args) < 3 or not args[1].isdigit():
        return "How tf i use: `/admin create-item <name> <price> <description>`"
    name = args[0].lower()
    with db_module.lock:
        db_module.db.execute("INSERT OR REPLACE INTO items VALUES (?,?,?)",
                             (name, int(args[1]), " ".join(args[2:])))
        db_module.db.commit()
    return f"Item `{name}` created for {ui.fmt(int(args[1]))}."


def remove_item(name):
    with db_module.lock:
        deleted = db_module.db.execute("DELETE FROM items WHERE name=?", (name,)).rowcount
        removed = db_module.db.execute("DELETE FROM inv WHERE name=?", (name,)).rowcount
        db_module.db.commit()
    if deleted:
        return f"Item `{name}` deleted (removed from {removed} inventories)."
    return f"No item called `{name}`."


def delete_item(args):
    if not args:
        return "How to usee: `/admin delete-item <name>`"
    return remove_item(args[0].lower())


def set_blackjack_decks(args):
    if not args or not args[0].isdigit() or not 1 <= int(args[0]) <= 8:
        return "How use: `/admin set-decks <1-8>`"
    db_module.set_setting("bj_decks", int(args[0]))
    return f"Blackjack now uses {args[0]} deck(s)."


def parse_duration(text):
    import re
    match = re.fullmatch(r"(\d+)([smh]?)", (text or "").lower())
    if not match:
        return None
    return int(match.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600}[match.group(2)]


def set_game_cooldown(args):
    seconds = parse_duration(args[1]) if len(args) > 1 else None
    if len(args) < 2 or not args[0].isdigit() or int(args[0]) < 1 or not seconds:
        return ("How me use: `/admin set-cooldown <usages> <duration>`\n"
                "Example: `/admin set-cooldown 4 5m` (4 games per 5 minutes)")
    db_module.set_setting("cd_uses", int(args[0]))
    db_module.set_setting("cd_secs", seconds)
    return f"Players can now play {args[0]} games per {seconds}s."


def audit(args):
    if not args or not parse_user(args[0]):
        return "How use: `/admin audit @user`"
    target = parse_user(args[0])
    with db_module.lock:
        rows = db_module.db.execute(
            "SELECT ts, cash, bank, why FROM log WHERE uid=? ORDER BY ts DESC LIMIT 20", (target,)).fetchall()
    if not rows:
        return "No logged money moves for that user yet."
    lines = [f"`{time.strftime('%d %H:%M:%S', time.gmtime(when))}` cash {db_module.read_number(cash):+,} "
             f"bank {db_module.read_number(bank):+,} ({why})" for when, cash, bank, why in rows]
    return f"*Last moves (UTC)* for {ui.tag(target)}\n" + "\n".join(lines)


@cmd("admin", keep_case=True)
def admin_cmd(uid, args):
    if uid not in ADMINS:
        return (f"🔒 Admins only. Your Slack ID is `{uid}` — add it to the `ADMINS` set in commands.py "
                "or set `ADMIN_IDS=" + uid + "` in the environment.")
    if not args or args[0].lower() == "help":
        return ADMIN_HELP

    sub, rest = args[0].lower(), args[1:]
    target = parse_user(rest[0]) if rest else None

    if sub == "add-money":
        return add_money(rest)
    if sub == "create-item":
        return create_item(rest)
    if sub == "delete-item":
        return delete_item(rest)
    if sub == "set-decks":
        return set_blackjack_decks(rest)
    if sub == "set-cooldown":
        return set_game_cooldown(rest)
    if sub == "audit":
        return audit(rest)

    if sub == "nuke":
        if rest and rest[0] == "all":
            if rest[1:] != ["confirm"]:
                return ("This wipys EVERYONE's cash and bank. Run `/admin nuke all confirm` to do it "
                        "(`/admin undo` can restore it).")
            ids = all_user_ids()
            snapshot(ids)
            for user_id in ids:
                set_money(user_id, 0, 0)
            return f"NUKED ALL OF YALL ({len(ids)} players) to 0."
        if not target:
            return "How to use ts: `/admin nuke @user` or `/admin nuke all confirm`"
        snapshot([target])
        set_money(target, 0, 0)
        return f"BOOM ARAB ATTACK {ui.tag(target)} to 0."

    if sub == "cap":
        amount = parse_amount(rest[1], 0) if len(rest) > 1 else None
        if amount is None or not (target or rest[0] == "all"):
            return "How to use ts: `/admin cap @user <amount>` or `/admin cap all <amount>`"
        ids = all_user_ids() if rest[0] == "all" else [target]
        snapshot(ids)
        how_many = sum(cap_total(user_id, amount) for user_id in ids)
        return f"Capped {how_many} player(s) to {ui.fmt(amount)} total."

    if sub == "set":
        if not target or len(rest) < 2:
            return "WHY AM I MAKING THIS IM THE ONLY ADMIN: `/admin set @user <cash> [bank]`"
        new_cash = parse_amount(rest[1], db_module.MAX_COINS)
        new_bank = parse_amount(rest[2], db_module.MAX_COINS) if len(rest) > 2 else db_module.get_user(target)[1]
        if new_cash is None or new_bank is None:
            return "How use it: `/admin set @user <cash> [bank]`"
        snapshot([target])
        set_money(target, new_cash, new_bank)
        return f"{ui.tag(target)} now has {ui.fmt(db_module.get_user(target)[0])} cash " \
               f"and {ui.fmt(db_module.get_user(target)[1])} bank."

    if sub == "take":
        if not target or len(rest) < 2:
            return "HOW USE IT: `/admin take @user <amount|all>`"
        cash, bank = db_module.get_user(target)
        amount = parse_amount(rest[1], cash + bank)
        if not amount or amount < 1:
            return "How use: `/admin take @user <amount|all>`"
        amount = min(amount, cash + bank)
        snapshot([target])
        from_cash = min(cash, amount)
        db_module.change_money(target, cash=-from_cash, bank=-(amount - from_cash))
        return f"Took {ui.fmt(amount)} from {ui.tag(target)}."

    if sub == "giveall":
        amount = parse_amount(rest[0], db_module.MAX_COINS) if rest else None
        if not amount:
            return "HOW DO I USE IT: `/admin giveall <amount>`"
        ids = all_user_ids()
        for user_id in ids:
            db_module.change_money(user_id, cash=amount)
        return f"Gave {ui.fmt(amount)} to {len(ids)} players."

    if sub == "undo":
        with db_module.lock:
            rows = db_module.db.execute("SELECT uid, cash, bank FROM snap").fetchall()
            db_module.db.execute("DELETE FROM snap")
            db_module.db.commit()
        if not rows:
            return "Nothing to undo."
        for user_id, cash, bank in rows:
            set_money(user_id, db_module.read_number(cash), db_module.read_number(bank))
        return f"Restored {len(rows)} player(s) to how they were before the last change."

    if sub == "resetcd":
        with db_module.lock:
            if target:
                db_module.db.execute("DELETE FROM cooldowns WHERE uid=?", (target,))
                game_history.pop(target, None)
            elif rest and rest[0] == "all":
                db_module.db.execute("DELETE FROM cooldowns")
                game_history.clear()
            else:
                return "How usde: `/admin resetcd @user` or `/admin resetcd all`"
            db_module.db.commit()
        return "Cooldowns cleared."

    if sub in ("ban", "unban"):
        if not target:
            return f"HOW TO USE: `/admin {sub} @user`"
        db_module.set_setting(f"ban:{target}", 1 if sub == "ban" else 0)
        return f"{ui.tag(target)} is {'blocked from' if sub == 'ban' else 'allowed back into'} the economy."

    if sub == "info":
        if not target:
            return "HOW USE: `/admin info @user`"
        cash, bank = db_module.get_user(target)
        blocked = " · 🔒 blocked" if db_module.setting(f"ban:{target}", 0) else ""
        return f"{ui.tag(target)}: cash {ui.fmt(cash)} · bank {ui.fmt(bank)}{blocked}"

    if sub in ("item-remove", "remove-item"):
        return remove_item(rest[0]) if rest else "LAST PLS JS USE THIS: `/admin item-remove <name>`"

    return ADMIN_HELP
