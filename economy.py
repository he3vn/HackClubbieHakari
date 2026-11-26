#These are going to be the basic "economy" controls like ur balance and how you make money i explained stuff in the manifest.


import random
import re
import time
import database as db_module
import ui
from commands import ADMINS, cmd, check_game_rate, parse_amount, parse_user

#how many people fit on za leadebaords
LB_SIZE = 10
#how long somebody has to be around before you can rob them (days)
ACTIVE_DAYS = 3
#talking in the chat gives coins too
CHAT_COOLDOWN = 30
CHAT_MIN, CHAT_MAX = 10, 30

#Yh so now im going to make like the balance uhh js basic error debuging and commands to check.
@cmd("balance")
def balance(uid, args):
    target = parse_user(args[0]) if args else uid
    if not target:
        return "YOU NEED TO TYPE: `/balance [@user]`"
    cash, bank = db_module.get_user(target)
    return ui.embed(f"*{ui.tag(target)}'s balance*", ui.BLUE, nolog=True,
                    fields=[f"*Cash*\n{ui.fmt(cash)}", f"*Bank*\n{ui.fmt(bank)}",
                            f"*Net worth*\n{ui.fmt(cash + bank)} {ui.stars(cash + bank)}"],
                    footer="Cash can be robbed. Bank money is safe: /deposit it")

#Now the deposit code and withdrawal too
@cmd("deposit")
def deposit(uid, args):
    cash, _ = db_module.get_user(uid)
    amount = parse_amount(args[0], cash) if args else None
    if not amount or amount <= 0 or amount > cash:
        return f"How use: `/deposit <amount|half|all>` (you have {ui.fmt(cash)} cash)"
    db_module.change_money(uid, cash=-amount, bank=amount)
    return f"You deposited {ui.fmt(amount)}."


@cmd("withdraw")
def withdraw(uid, args):
    _, bank = db_module.get_user(uid)
    amount = parse_amount(args[0], bank) if args else None
    if not amount or amount <= 0 or amount > bank:
        return f"How to use: `/withdraw <amount|half|all>` (you have {ui.fmt(bank)} in bank)"
    db_module.change_money(uid, cash=amount, bank=-amount)
    return f"You withdrew {ui.fmt(amount)}."


@cmd("give")
def give(uid, args):
    if len(args) < 2 or not parse_user(args[0]):
        return "HOW USE COMMAND: `/give @user <amount|half|all>`"
    target = parse_user(args[0])
    cash, _ = db_module.get_user(uid)
    amount = parse_amount(args[1], cash)
    if target == uid or not amount or amount <= 0 or amount > cash:
        return f"Invalid. You have {ui.fmt(cash)} cash."
    db_module.change_money(uid, cash=-amount)
    db_module.change_money(target, cash=amount)
    return f"{ui.tag(uid)} gave {ui.fmt(amount)} to {ui.tag(target)}."


@cmd("stats")
def stats(uid, args):
    with db_module.lock:
        rows = db_module.db.execute("SELECT cash, bank, cash_x, bank_x FROM users").fetchall()
    #i add the numbers up in python, sqlite would overflow on the big ones
    cash = sum(int(row[0] or 0) + int(row[2] or 0) * db_module.UNIT for row in rows)
    bank = sum(int(row[1] or 0) + int(row[3] or 0) * db_module.UNIT for row in rows)
    return (f"*Economy stats*\nPlayers: {len(rows):,}\nTotal cash: {ui.fmt(cash)}\n"
            f"Total bank: {ui.fmt(bank)}\nTotal: {ui.fmt(cash + bank)}")


def leaderboard_page(uid, page):
    with db_module.lock:
        admin_ids = list(ADMINS)
        marks = ",".join("?" * len(admin_ids))
        raw = db_module.db.execute(
            f"SELECT uid, cash, bank, cash_x, bank_x FROM users WHERE uid NOT IN ({marks})",
            admin_ids).fetchall()

    totals = []
    for player_id, cash, bank, cash_x, bank_x in raw:
        total = int(cash or 0) + int(bank or 0) + (int(cash_x or 0) + int(bank_x or 0)) * db_module.UNIT
        if total > 0:
            totals.append((player_id, total))
    totals.sort(key=lambda row: (-row[1], row[0]))
