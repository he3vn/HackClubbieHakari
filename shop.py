#Yh this is the shop or should i say catalog kinda seems cringe anyways yh  u can buy stuff in here

import database as db_module
import ui
from commands import cmd, parse_amount

#Making commands for each different commands ofc duh heading off to do research :/

#So when in slack someone types /buy cofee 2 it like runs a command so ima write some cmds?
@cmd("catalog")
def catalog(uid, args):
    with db_module.lock:
        if args:
            row = db_module.db.execute(
                "SELECT name,price,description FROM items WHERE name=?", (args[0],)
            ).fetchone()
            return f"*{row[0]}* | {ui.fmt(row[1])}\n{row[2]}" if row else "Item not found."
        rows = db_module.db.execute("SELECT name,price FROM items ORDER BY price").fetchall()
    if not rows:
        return "No items yet."
    return "*Catalog*\n" + "\n".join(f"`{n}` • {ui.fmt(p)}" for n, p in rows) + "\nDetails: `/catalog <item>`"

#For the buying if you dont have any arguments it reject and tells you to add some arguments or easier said stuff to buy
@cmd("buy")
def buy(uid, args):
    if not args:
        return "How to use: `/buy <item> [amount]` and yes no arrows"
    amount = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    with db_module.lock:
        item = db_module.db.execute("SELECT price FROM items WHERE name=?", (args[0],)).fetchone()
    if not item:
        return "Item not found."
    total_cost = item[0] * amount
    cash, _ = db_module.get_user(uid)
    if amount < 1 or total_cost > cash:
        return f"You so broke lol no cash.Cost: {ui.fmt(total_cost)}, you have {ui.fmt(cash)}."
    db_module.change_money(uid, cash=-total_cost)
    db_module.change_inv(uid, args[0], amount)
    return f"Yh you bought {amount}x `{args[0]}` for {ui.fmt(total_cost)}."

@cmd("inventory")
def inventory(uid, args):
    with db_module.lock:
        rows = db_module.db.execute(
            "SELECT name,amount FROM inv WHERE uid=? AND amount>0", (uid,)
        ).fetchall()
    if not rows:
        return "You didnt buy anything gng."
    return "*Inventory*\n" + "\n".join(f"`{n}` x{a}" for n, a in rows)

@cmd("use")
def use(uid, args):
    if not args:
        return "How to use: `/use <item> [amount]`"
    amount = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    if amount < 1 or db_module.get_inv_amount(uid, args[0]) < amount:
        return "You dont get enough cash homie."
    db_module.change_inv(uid, args[0], -amount)
    return f" You used {amount}x `{args[0]}`."
