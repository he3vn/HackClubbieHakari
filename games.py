#This is going to be like the solo gambling games and the 2 players ones too yh
#So commands is supposed to parse the amount it takes in text and checks the number and return maximum or maximum/2 yh ima use this

import random
import re
import threading
import time
import uuid

from slack_sdk.webhook import WebhookClient

import commands
import database as db_module
import ui
from commands import (ADMINS, GAME_TIMEOUT, add_usage_hint, check_bet, check_game_rate, cmd,
                      log_move, parse_amount, parse_user, scaled_win, set_context)

SUITS = "♠♥♦♣"
RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}


def card_str(card):
    face = {1: "A", 11: "J", 12: "Q", 13: "K"}.get(card[0], str(card[0]))
    return f"`{face}{card[1]}`"


def hand_str(hand):
    return " ".join(card_str(card) for card in hand)


def hand_value(hand):
    total = 0
    has_ace = False
    for card in hand:
        rank = card[0]
        if rank == 1:
            has_ace = True
            total += 1
        elif rank >= 10:
            total += 10
        else:
            total += rank
    if has_ace and total + 10 <= 21:
        total += 10
    return total


def refund_later(store, game_id):
    def refund():
        with db_module.lock:
            game = store.pop(game_id, None)
            if game:
                db_module.change_money(game["uid"], cash=game["bet"])
    timer = threading.Timer(GAME_TIMEOUT, refund)
    timer.daemon = True
    timer.start()


def universalhelper(bet_text, maximum):
    if not bet_text:
        return None, "Enter a number"
    bet = parse_amount(bet_text, maximum)
    if bet is None:
        return None, "Type a valid number, 'half' or 'all'"
    if bet < 1:
        return None, "Bet should be at least 1 coin."
    if bet > maximum:
        return None, "You dont have enough cash gng"
    return bet, None


#Ima start with the easiest game to build(russina roulette baby)
def _rr_play(uid, bet_text):
    cash, _ = db_module.get_user(uid)
    bet, err = universalhelper(bet_text, cash)
    if err:
        return err
    rate_error = check_game_rate(uid)
    if rate_error:
        return rate_error
    #we take the bet first, then we give it back if you survive
    db_module.change_money(uid, cash=-bet)
    #Let me make some research on how russian roulette actually works,this is all I actually know its like you pick 1 number from 6
    number = random.randint(1, 6)
    mynumber = 1
    if number == mynumber:
        profit = -bet
        text = "You chose the wrong one bucko,now get shot!"
        color = ui.RED
    else:
        profit = scaled_win(uid, bet, 0.2)
        db_module.change_money(uid, cash=bet + profit)
        text = "Bro actually didnt shoot himself lmao.Here is 20% more of ur money"
        color = ui.GREEN
    log_move(uid, f"played russian roulette (bet {ui.fmt(bet)})", ui.signed(profit))
    ui.celebrate(uid, profit)
    return ui.embed(f"{text}\n{ui.tag(uid)} bet {ui.fmt(bet)} · *Result:* *{ui.signed(profit)}*",
                    color, nolog=True,
                    footer="1 bullet in 6 chambers. Survive to win 20% of your bet.",
                    buttons=[ui.button("Again", "rr_again", f"{uid}:{bet}", "danger"), ui.HELP_BUTTON])


@cmd("roulette")
def russian_roulette(uid, args):
    return _rr_play(uid, args[0] if args else "")


#Now lets make rock-paper-scissors its way easier
_rps_games = {}
RPS_CHOICES = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


@cmd("rps")
def rps(uid, args):
    if args and args[0].startswith("<"):
        return _make_challenge(uid, args, "rps")
    cash, _ = db_module.get_user(uid)
    bet, err = universalhelper(args[0] if args else "", cash)
    if err:
        return add_usage_hint(err, "\nHow to use gng: `/rps <bet|half|all>` (vs bot) or `/rps @user [bet]` (vs person)")
    rate_error = check_game_rate(uid)
    if rate_error:
        return rate_error
    db_module.change_money(uid, cash=-bet)
    gid = uuid.uuid4().hex[:8]
    _rps_games[gid] = {"gid": gid, "uid": uid, "bet": bet}
    refund_later(_rps_games, gid)
    buttons = [ui.button(f"{emoji} {move.title()}", f"rps_{move}", gid) for move, emoji in RPS_CHOICES.items()]
    return ui.embed(
        f"*Rock Paper Scissors* · {ui.tag(uid)} bet {ui.fmt(bet)}\nPick your move!",
        ui.BLUE, nolog=True, buttons=buttons + [ui.HELP_BUTTON],
    )


#Finish second part of rps,back(will be adding less comments to avoid fraud)
def register_rps_action(slack_app):
    @slack_app.action(re.compile(r"^rps_(rock|paper|scissors)$"))
    def rps_action(ack, body, respond, action, client):
        ack()
        set_context(client, body)
        with db_module.lock:
            game = _rps_games.get(action["value"])
            if not game:
                ui.only_you(respond, "That game ended bro.", client, body)
                return
            if body["user"]["id"] != game["uid"]:
                ui.only_you(respond, "This aint your game", client, body)
                return
            player_move = action["action_id"][4:]
            bot_move = random.choice(list(RPS_CHOICES))
            uid, bet = game["uid"], game["bet"]
            if player_move == bot_move:
                profit, result, color = 0, "Tie,the money is returned", ui.GREY
            elif RPS_BEATS[player_move] == bot_move:
                profit, result, color = scaled_win(uid, bet, 2), "You win.", ui.GREEN
            else:
                profit, result, color = -bet, "You lose haaha.", ui.RED
            if bet + profit:
                db_module.change_money(uid, cash=bet + profit)
            _rps_games.pop(action["value"], None)
            log_move(uid, f"played rps vs the bot (bet {ui.fmt(bet)})", f"{player_move} vs {bot_move}: {result}")
            ui.celebrate(uid, profit)
            ui.swap(respond, ui.embed(
                f"*Rock Paper Scissors* · {ui.tag(uid)} bet {ui.fmt(bet)}\n"
                f"You: {RPS_CHOICES[player_move]} {player_move}  vs  Bot: {RPS_CHOICES[bot_move]} {bot_move}\n"
                f"*{result}*  *{ui.signed(profit)}*",
                color, nolog=True, buttons=[ui.HELP_BUTTON],
            ), client, body)


#Time to do roulette (the wheel one everybody can join)
lesgamble_games = {}
#how long you have to join after somebody put a bet in, and the max time for the whole table
LESGAMBLE_JOIN, LESGAMBLE_MAX = 10, 60


def lesgamble_space(space):
    if space in ("red", "black"):
        return space, 2, lambda n: n != 0 and ((n in RED_NUMBERS) == (space == "red"))
    if space in ("odd", "even"):
        #0 is even, so even wins on 0
        return space, 2, lambda n: (n % 2 == 1) if space == "odd" else (n % 2 == 0)
    if space in ("1-18", "19-36"):
        low, high = map(int, space.split("-"))
        return space, 2, lambda n: low <= n <= high
    dozens = {"1st": (1, 12), "2nd": (13, 24), "3rd": (25, 36),
              "1-12": (1, 12), "13-24": (13, 24), "25-36": (25, 36)}
    if space in dozens:
        low, high = dozens[space]
        return f"{low}-{high}", 4, lambda n: low <= n <= high
    if space.isdigit() and 0 <= int(space) <= 36:
        return space, 70, lambda n: n == int(space)
    return None


LESGAMBLE_USAGE = ("\nUsage: `/lesgamble <red|black|odd|even|1st|2nd|3rd|1-12|13-24|25-36|1-18|19-36|0-36> <bet>`")


@cmd("lesgamble")
def lesgamble(uid, args):
    if len(args) < 2:
        return "How to use: /lesgamble <red|black|green|0-36> <bet>" + LESGAMBLE_USAGE
    space = args[0].lower()
    the_space = lesgamble_space(space)
    if not the_space:
        return "Pick red,black, gren or a number from 0 to 36.read!" + LESGAMBLE_USAGE
    cash, _ = db_module.get_user(uid)
    bet, err = universalhelper(args[1], cash)
    if err:
        return add_usage_hint(err, LESGAMBLE_USAGE)
    rate_error = check_game_rate(uid)
    if rate_error:
        return rate_error

    channel = getattr(commands.cur, "channel", None)
    now = time.time()
    db_module.change_money(uid, cash=-bet)

    game = lesgamble_games.get(channel)
    new_table = game is None
    if new_table:
        game = lesgamble_games[channel] = {"channel": channel, "start": now, "bets": [],
                                           "timer": None, "url": getattr(commands.cur, "url", None)}
    game["bets"].append((uid, bet, space, the_space))

    #every new bet pushes the spin a bit further away
    left = max(1, int(min(LESGAMBLE_JOIN, game["start"] + LESGAMBLE_MAX - now)))
    if game["timer"]:
        game["timer"].cancel()
    game["timer"] = threading.Timer(left, lesgamble_spin, args=(channel,))
    game["timer"].daemon = True
    game["timer"].start()

    players = len({bet_row[0] for bet_row in game["bets"]})
    pot = sum(bet_row[1] for bet_row in game["bets"])
    head = "🎡 *New roulette game started!*" if new_table else "🎡 *Roulette*"
    return ui.embed(f"{head}\n{ui.tag(uid)} placed a bet of {ui.fmt(bet)} on `{space}`\n"
                    f"{players} player{'s' if players != 1 else ''} · {ui.fmt(pot)} on the table · "
                    f"spinning in *{left}s*",
                    ui.BLUE, response_type="in_channel", nolog=True,
                    footer=f"Join with /lesgamble <space> <bet>. "
                           f"Time remaining: {LESGAMBLE_JOIN}s after each bet (max {LESGAMBLE_MAX}s).")


def lesgamble_spin(channel):
    with db_module.lock:
        game = lesgamble_games.pop(channel, None)
        if not game:
            return
        number = random.randint(0, 36)
        color = "green" if number == 0 else ("red" if number in RED_NUMBERS else "black")
        results = {}
        for uid, bet, raw_space, (label, multiplier, wins) in game["bets"]:
            row = results.setdefault(uid, [0, 0])
            if wins(number):
                profit = scaled_win(uid, bet, multiplier)
                db_module.change_money(uid, cash=bet + profit)
                row[0] += profit
            else:
                row[1] += bet
        lines = []
        for uid, (won, lost) in results.items():
            net = won - lost
            ui.celebrate(uid, net)
            mark = "✅" if net > 0 else ("➖" if net == 0 else "❌")
            lines.append(f"{mark} <@{uid}> *{ui.signed(net)}*")
            log_move(uid, "played roulette", f"ball on {color} {number}: {ui.signed(net)}")
        total = sum(bet_row[1] for bet_row in game["bets"])

    text = f"🎡 *The ball landed on {color} {number}!*\n" + "\n".join(lines)
    body = {"text": f"🎡 The ball landed on {color} {number}!",
            "attachments": [{"color": {"red": ui.RED, "black": ui.GREY, "green": ui.GREEN}[color],
                             "blocks": [ui.section(text),
                                        {"type": "context", "elements": [
                                            {"type": "mrkdwn",
                                             "text": f"{len(results)} player(s) · {ui.fmt(total)} bet in total"}]}]}]}
    try:
        commands.app.client.chat_postMessage(channel=channel, **ui.wire(body))
    except Exception as error:
        print("roulette result via chat.postMessage failed, trying response_url:", repr(error))
        try:
            WebhookClient(game["url"]).send(response_type="in_channel", **ui.wire(body))
        except Exception as error2:
            print("roulette result could not be posted:", repr(error2))


#Les do higher/lower should be pretty free
hl_games = {}


def get_hl_multiplier(chance):
    if chance <= 0:
        return None
    payout = 0.97 / chance
    if payout > 12.0:
        return 12.0
    return payout


def build_hl_screen(game):
    first_card = game["card"]
    card_number = first_card[0]

    higher_chance = (13 - card_number) / 13
    lower_chance = (card_number - 1) / 13
    buttons = []

    if higher_chance > 0:
        high_mult = get_hl_multiplier(higher_chance)
        buttons.append(ui.button(f"⬆️ Higher  x{high_mult:.2f}", "hl_higher", game["gid"], "primary"))
    if lower_chance > 0:
        low_mult = get_hl_multiplier(lower_chance)
        buttons.append(ui.button(f"⬇️ Lower  x{low_mult:.2f}", "hl_lower", game["gid"]))
    buttons.append(ui.HELP_BUTTON)

    return ui.embed(
        f"*Higher or Lower* · {ui.tag(game['uid'])} · bet {ui.fmt(game['bet'])}\n\n"
        f"Current card: {card_str(first_card)}\n"
        f"Will the next card be higher or lower? (A is low, K is high, ties lose)",
        ui.BLUE,
        nolog=True,
        buttons=buttons,
        footer="The payour is bigger when the guess is less likely."
    )


def start_hl_game(uid, bet_text):
    cash, _ = db_module.get_user(uid)
    bet, err = universalhelper(bet_text, cash)
    if err:
        return add_usage_hint(err, "\nUsage: `/higher-lower <bet|half|all>`")
    rate_error = check_game_rate(uid)
    if rate_error:
        return rate_error
    db_module.change_money(uid, cash=-bet)
    game_id = uuid.uuid4().hex[:8]
    starting_card = (random.randint(1, 13), random.choice(SUITS))
    game = {
        "gid": game_id,
        "uid": uid,
        "bet": bet,
        "card": starting_card
    }
    hl_games[game_id] = game
    refund_later(hl_games, game_id)
    return build_hl_screen(game)


@cmd("higher-lower")
def higher_lower(uid, args):
    bet_text = args[0] if args else ""
    return start_hl_game(uid, bet_text)


def register_hl_action(slack_app):
    @slack_app.action(re.compile(r"^hl_(higher|lower)$"))
    def hl_action(ack, body, respond, action, client):
        ack()
        set_context(client, body)
        with db_module.lock:
            game_id = action["value"]
            game = hl_games.get(game_id)

            if not game:
                ui.only_you(respond, "The game ended bro.", client, body)
                return
            uid = game["uid"]
            bet = game["bet"]

            if body["user"]["id"] != uid:
                ui.only_you(respond, "This ain't your game!", client, body)
                return

            hl_games.pop(game_id)
            first_card = game["card"]
            next_card = (random.randint(1, 13), random.choice(SUITS))
            first_number = first_card[0]
            next_number = next_card[0]
            if action["action_id"] == "hl_higher":
                chance = (13 - first_number) / 13
                player_won = next_number > first_number
            else:
                chance = (first_number - 1) / 13
                player_won = next_number < first_number

            if player_won:
                mult = get_hl_multiplier(chance)
                profit = scaled_win(uid, bet, mult - 1)
                db_module.change_money(uid, cash=bet + profit)
                result_text = "You win"
                card_color = ui.GREEN
            else:
                profit = -bet
                result_text = "You lose HAHAA"
                card_color = ui.RED

            log_move(uid, f"played higher-lower (bet {ui.fmt(bet)})",
                     f"{card_str(first_card)} then {card_str(next_card)} {ui.signed(profit)}")
            ui.celebrate(uid, profit)

            play_again_btn = ui.button("Play Again", "hl_again", f"{uid}:{bet}", "primary")

            ui.swap(
                respond,
                ui.embed(
                    f"*Higher or Lower* · {ui.tag(uid)} · bet {ui.fmt(bet)}\n\n"
                    f"{card_str(first_card)} → {card_str(next_card)}\n"
                    f"*Result:* {result_text}  *{ui.signed(profit)}*",
                    card_color,
                    nolog=True,
                    buttons=[play_again_btn, ui.HELP_BUTTON],
                ),
                client,
                body,
            )


#Les do slots(this sounds really bad but i dont support gambling)
SLOT_SYMBOLS = ["🍒", "🍒", "🍒", "🍋", "🍋", "🍇", "🔔", "💎", "7️⃣"]
SLOT_PAYOUTS = {
    "7️⃣": 10,
    "💎": 7,
    "🔔": 5,
    "🍇": 4,
    "🍋": 3,
    "🍒": 3,
}


@cmd("slots")
def slots(uid, args):
    cash, _ = db_module.get_user(uid)
    bet_text = args[0] if args else ""
    bet, err = universalhelper(bet_text, cash)
    if err:
        return add_usage_hint(err, "\nUsage: `/slots <bet|half|all>`")
    rate_error = check_game_rate(uid)
    if rate_error:
        return rate_error
    db_module.change_money(uid, cash=-bet)
    reel1 = random.choice(SLOT_SYMBOLS)
    reel2 = random.choice(SLOT_SYMBOLS)
    reel3 = random.choice(SLOT_SYMBOLS)

    if reel1 == reel2 == reel3:
        mult = SLOT_PAYOUTS[reel1]
        profit = scaled_win(uid, bet, mult - 1)
        result_text = f"JACKPOTTTTT! Triple {reel1}!"
        color = ui.GREEN
    elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
        profit = scaled_win(uid, bet, 0.5)
        result_text = "Nice. Two matched"
        color = ui.GREEN
    else:
        profit = -bet
        result_text = "No match,better luck next time bozo."
        color = ui.RED
    if bet + profit:
        db_module.change_money(uid, cash=bet + profit)
    log_move(uid, f"spun the slots (bet {ui.fmt(bet)})", f"{reel1}{reel2}{reel3} {result_text}")
    ui.celebrate(uid, profit)
    return ui.embed(
        f"*Slots* · {ui.tag(uid)} · bet {ui.fmt(bet)}\n\n"
        f"[ {reel1} | {reel2} | {reel3} ]\n\n"
        f"*{result_text}*  *{ui.signed(profit)}*",
        color,
        nolog=True,
        buttons=[ui.button("Spin Again", "slots_again", f"{uid}:{bet}", "primary"), ui.HELP_BUTTON],
    )


#Blackjack solo ima make 2 Player games later lowk
def new_deck():
    deck = []
    for rank in range(1, 14):
        for suit in SUITS:
            deck.append((rank, suit))
    random.shuffle(deck)
    return deck


bj_games = {}


def build_bj_screen(game, finished=False):
    uid = game["uid"]
    bet = game["bet"]
    player_hand = game["player"]
    dealer_hand = game["dealer"]
    if finished:
        result_label, profit = game["result"]
        if profit > 0:
            color = ui.GREEN
        elif profit == 0:
            color = ui.GREY
        else:
            color = ui.RED
        header = f"🃏 *Blackjack* · {ui.tag(uid)} · bet {ui.fmt(bet)}\n*Result:* {result_label}  *{ui.signed(profit)}*"
        dealer_text = f"{hand_str(dealer_hand)}\nValue: {hand_value(dealer_hand)}"
        play_again_btn = ui.button("Play Again", "bj_again", f"{uid}:{game['bet0']}", "primary")
        buttons = [play_again_btn, ui.HELP_BUTTON]
    else:
        color = ui.BLUE
        header = f"🃏 *Blackjack* · {ui.tag(uid)} · bet {ui.fmt(bet)}"
        dealer_text = f"{card_str(dealer_hand[0])} `?`\nValue: ?"
        buttons = [
            ui.button("Hit", "bj_hit", game["gid"], "primary"),
            ui.button("Stand", "bj_stand", game["gid"]),
        ]
        cash, _ = db_module.get_user(uid)
        if len(player_hand) == 2 and cash >= bet:
            buttons.append(ui.button("Double Down", "bj_double", game["gid"]))
        buttons.append(ui.HELP_BUTTON)

    return ui.embed(
        header,
        color,
        nolog=True,
        buttons=buttons,
        footer=f"Cards remaining: {len(game['deck'])}",
        fields=[
            f"*Your Hand*\n{hand_str(player_hand)}\nValue: {hand_value(player_hand)}",
            f"*Dealer Hand*\n{dealer_text}",
        ],
    )


def finish_bj_game(game, natural=False):
    player_val = hand_value(game["player"])
    #Ima start commeting more lemme make sure the dealer keeps hitting until he reaches 17
    while hand_value(game["dealer"]) < 17 and player_val <= 21:
        game["dealer"].append(game["deck"].pop())
    dealer_val = hand_value(game["dealer"])
    bet = game["bet"]
    uid = game["uid"]

    if player_val > 21:
        label = "Bust"
        profit = -bet
    elif natural and dealer_val != 21:
        label = "Blackjack!"
        profit = scaled_win(uid, bet, 5)
    elif dealer_val > 21 or player_val > dealer_val:
        if dealer_val > 21:
            label = "Dealer got over 21.You win"
        else:
            label = "You win"
        if player_val == 21:
            label = "21! " + label
            profit = scaled_win(uid, bet, 3)
        else:
            profit = scaled_win(uid, bet, 2)
    elif player_val == dealer_val:
        label = "Push"
        profit = 0
    else:
        label = "Dealer wins."
        profit = -bet
    if bet + profit > 0:
        db_module.change_money(uid, cash=bet + profit)

    bj_games.pop(game["gid"], None)
    game["result"] = (label, profit)
    log_move(uid, f"played blackjack (bet {ui.fmt(bet)})", f"{label} {ui.signed(profit)}")
    ui.celebrate(uid, profit)


def bj_timeout(gid):
    with db_module.lock:
        game = bj_games.get(gid)
        if game:
            finish_bj_game(game)


def start_bj_game(uid, bet_text):
    cash, _ = db_module.get_user(uid)
    bet, err = universalhelper(bet_text, cash)
    if err:
        return add_usage_hint(err, "\nUsage: `/blackjack <bet|half|all>`")
    rate_error = check_game_rate(uid)
    if rate_error:
        return rate_error
    db_module.change_money(uid, cash=-bet)
    deck = new_deck()
    game_id = uuid.uuid4().hex[:8]

    game = {
        "gid": game_id,
        "uid": uid,
        "bet": bet,
        "bet0": bet,
        "deck": deck,
        "player": [deck.pop(), deck.pop()],
        "dealer": [deck.pop(), deck.pop()],
    }
    bj_games[game_id] = game

    timer = threading.Timer(GAME_TIMEOUT, lambda: bj_timeout(game_id))
    timer.daemon = True
    timer.start()

    if hand_value(game["player"]) == 21:
        finish_bj_game(game, natural=True)
        return build_bj_screen(game, finished=True)

    return build_bj_screen(game)


@cmd("blackjack")
def blackjack(uid, args):
    if args and args[0].startswith("<"):
        return _make_challenge(uid, args, "bj")
    bet_text = args[0] if args else ""
    return start_bj_game(uid, bet_text)


def register_bj_actions(slack_app):
    @slack_app.action(re.compile(r"^bj_(hit|stand|double)$"))
    def bj_action(ack, body, respond, action, client):
        ack()
        set_context(client, body)
        with db_module.lock:
            game_id = action["value"]
            game = bj_games.get(game_id)
            if not game:
                ui.only_you(respond, "The game ended bro.", client, body)
                return
            if body["user"]["id"] != game["uid"]:
                ui.only_you(respond, "This aint your game", client, body)
                return
            btn_clicked = action["action_id"]

            if btn_clicked == "bj_hit":
                game["player"].append(game["deck"].pop())
                if hand_value(game["player"]) < 21:
                    ui.swap(respond, build_bj_screen(game), client, body)
                    return
            elif btn_clicked == "bj_double":
                cash, _ = db_module.get_user(game["uid"])
                if len(game["player"]) != 2 or cash < game["bet"]:
                    ui.only_you(respond, "You cant double down now.", client, body)
                    return
                db_module.change_money(game["uid"], cash=-game["bet"])
                game["bet"] *= 2
                game["player"].append(game["deck"].pop())

            finish_bj_game(game)
            ui.swap(respond, build_bj_screen(game, finished=True), client, body)


#the play again buttons (blackjack, slots, higher-lower, russian roulette)
def register_again_action(slack_app):
    @slack_app.action(re.compile(r"^(bj|slots|hl|rr)_again$"))
    def again_action(ack, body, respond, action, client):
        ack()
        set_context(client, body)
        kind = action["action_id"].split("_")[0]
        uid, bet = action["value"].split(":")
        with db_module.lock:
            if body["user"]["id"] != uid:
                ui.only_you(respond, "This aint your game", client, body)
                return
            if kind == "bj":
                answer = start_bj_game(uid, bet)
            elif kind == "slots":
                answer = slots(uid, [bet])
            elif kind == "hl":
                answer = start_hl_game(uid, bet)
            else:
                answer = _rr_play(uid, bet)
        if isinstance(answer, str):
            ui.only_you(respond, answer, client, body)
        else:
            ui.swap(respond, answer, client, body)


#Les start the 2 player games im so tired i want to sleep but i gotta do it
challenges = {}
pvp_games = {}
PVP_BONUS = 1
GAME_NAMES = {"rps": "Rock Paper Scissors", "ttt": "Tic Tac Toe", "bj": "Blackjack",}


def stake_text(bet):
    if bet > 0:
        return f"{ui.fmt(bet)} each"
    return "no bet"


def pay_pvp_winner(winner, bet):
    bonus = bet * PVP_BONUS
    db_module.change_money(winner, cash=bet * 2 + bonus)
    return bet + bonus


def win_text(winner, loser, bet, gain=None):
    if gain is None:
        gain = bet * (1 + PVP_BONUS)
    ui.celebrate(winner, gain)
    if bet:
        ui.celebrate(loser, -bet)
    if bet > 0:
        return f"{ui.tag(winner)} wins *{ui.fmt(gain)}* ({ui.tag(loser)} loses {ui.fmt(bet)})!"
    return f"{ui.tag(winner)} wins!"


def replace_message(respond, text, extra_blocks=None, client=None, body=None):
    blocks = [ui.section(text)]
    if extra_blocks:
        blocks += extra_blocks
    message = ui.wire(ui.render({"text": text, "blocks": blocks}, False))
    respond(replace_original=True, **message)


def expire_pvp(gid):
    with db_module.lock:
        game = pvp_games.pop(gid, None)
        if not game:
            return
        db_module.change_money(game["a"], cash=game["bet"])
        db_module.change_money(game["b"], cash=game["bet"])
    try:
        text = f"{GAME_NAMES[game['kind']]} timed out. Bets were returned."
        body = ui.wire(ui.render({"text": text, "blocks": [ui.section(text)]}, False))
        WebhookClient(game["url"]).send(replace_original=True, **body)
    except Exception as err:
        print("Could not edit expired game:", repr(err))


def arm_pvp_timer(game):
    if game.get("timer"):
        game["timer"].cancel()
    timer = threading.Timer(GAME_TIMEOUT, expire_pvp, args=(game["gid"],))
    timer.daemon = True
    game["timer"] = timer
    timer.start()


def _make_challenge(uid, args, kind):
    usage = f"\nUsage: `/{kind} @user [bet]`"
    target = parse_user(args[0])
    if not target or target == uid:
        return "Pick someone else to challenge gng." + usage

    cash, _ = db_module.get_user(uid)
    bet = 0
    if len(args) > 1:
        bet = parse_amount(args[1], cash)
        if bet is None or bet < 0 or bet > cash:
            return f"Invalid bet. You have {ui.fmt(cash)} cash." + usage

    rate_err = check_game_rate(uid)
    if rate_err:
        return rate_err

    gid = uuid.uuid4().hex[:8]
    challenges[gid] = {
        "kind": kind,
        "a": uid,
        "b": target,
        "bet": bet,
    }
    timer = threading.Timer(GAME_TIMEOUT, lambda: challenges.pop(gid, None))
    timer.daemon = True
    timer.start()

    text = f"<@{target}> {ui.tag(uid)} challenges you to *{GAME_NAMES[kind]}* ({stake_text(bet)})!"
    return {
        "text": text,
        "response_type": "in_channel",
        "blocks": [
            ui.section(text),
            {
                "type": "actions",
                "elements": [
                    ui.button("Accept", "ch_accept", gid, "primary"),
                    ui.button("Decline", "ch_decline", gid, "danger"),
                ],
            },
        ],
    }


def register_challenge_actions(slack_app):
    @slack_app.action(re.compile(r"^ch_(accept|decline)$"))
    def ch_action(ack, body, respond, action, client):
        ack()
        set_context(client, body)
        with db_module.lock:
            gid = action["value"]
            user = body["user"]["id"]
            challenge = challenges.get(gid)

            if not challenge:
                ui.only_you(respond, "That challenge expired bro.", client, body)
                return

            if action["action_id"] == "ch_decline":
                if user != challenge["a"] and user != challenge["b"]:
                    ui.only_you(respond, "This challenge isn't for you!", client, body)
                    return
                challenges.pop(gid)
                replace_message(respond, f"❌ {ui.tag(user)} cancelled the {GAME_NAMES[challenge['kind']]} challenge.",
                                client=client, body=body)
                return

            if user != challenge["b"]:
                ui.only_you(respond, "This challenge isn't for you!", client, body)
                return

            bet = challenge["bet"]
            cash_a, _ = db_module.get_user(challenge["a"])
            cash_b, _ = db_module.get_user(challenge["b"])
            if cash_a < bet or cash_b < bet:
                challenges.pop(gid)
                replace_message(respond, "Challenge cancelled:One of you cant afford it.",
                                client=client, body=body)
                return
            challenges.pop(gid)
            db_module.change_money(challenge["a"], cash=-bet)
            db_module.change_money(challenge["b"], cash=-bet)

            game = {
                "gid": gid,
                "kind": challenge["kind"],
                "a": challenge["a"],
                "b": challenge["b"],
                "bet": bet,
                "url": body.get("response_url"),
                "timer": None,
            }
            if game["kind"] == "rps":
                game["picks"] = {}
            elif game["kind"] == "bj":
                deck = new_deck()
                game["deck"] = deck
                game["h"] = {game["a"]: [deck.pop(), deck.pop()], game["b"]: [deck.pop(), deck.pop()]}
                game["done"] = {player for player in (game["a"], game["b"]) if hand_value(game["h"][player]) == 21}
            else:
                game["board"] = [None] * 9
                game["turn"] = game["a"]
            pvp_games[gid] = game
            arm_pvp_timer(game)

            if game["kind"] == "bj" and len(game["done"]) == 2:
                pvp_games.pop(gid, None)
                replace_message(respond, bj2_result(game), client=client, body=body)
                return
            if game["kind"] == "rps":
                view = rps_view(game)
            elif game["kind"] == "bj":
                view = bj2_view(game)
            else:
                view = ttt_view(game)
            respond(replace_original=True, **ui.wire(ui.render(view, False)))


#the 2 player rock paper scissors
def rps_view(game):
    picks = game["picks"]
    status = " | ".join(f"{ui.tag(player)} {'picked' if player in picks else 'thinking'}"
                        for player in (game["a"], game["b"]))
    text = f"*Rock Paper Scissors* | {ui.tag(game['a'])} vs {ui.tag(game['b'])} ({stake_text(game['bet'])})\n{status}"
    buttons = [ui.button(f"{emoji} {move.title()}", f"prps_{move}", game["gid"]) for move, emoji in RPS_CHOICES.items()]
    return {"text": text, "blocks": [ui.section(text), {"type": "actions", "elements": buttons}]}


def register_pvp_rps_action(slack_app):
    @slack_app.action(re.compile(r"^prps_(rock|paper|scissors)$"))
    def prps_action(ack, body, respond, action, client):
        ack()
        set_context(client, body)
        with db_module.lock:
            game = pvp_games.get(action["value"])
            user = body["user"]["id"]
            if not game:
                ui.only_you(respond, "That game has ended.", client, body)
                return
            if user not in (game["a"], game["b"]):
                ui.only_you(respond, "This isn't your game!", client, body)
                return
            if user in game["picks"]:
                ui.only_you(respond, "You already picked, waiting for your opponent.", client, body)
                return
            move = action["action_id"][5:]
            game["picks"][user] = move
            game["url"] = body.get("response_url") or game["url"]
            if len(game["picks"]) < 2:
                arm_pvp_timer(game)
                respond(replace_original=True, **ui.wire(ui.render(rps_view(game), False)))
                ui.only_you(respond, f"You picked {RPS_CHOICES[move]} {move}. Waiting for your opponent...", client, body)
                return
            player_a, player_b, bet = game["a"], game["b"], game["bet"]
            pick_a, pick_b = game["picks"][player_a], game["picks"][player_b]
            if game.get("timer"):
                game["timer"].cancel()
            pvp_games.pop(game["gid"], None)
            head = f"*Rock Paper Scissors* | {ui.tag(player_a)} {RPS_CHOICES[pick_a]} {pick_a}  vs  {ui.tag(player_b)} {RPS_CHOICES[pick_b]} {pick_b}\n"
            if pick_a == pick_b:
                db_module.change_money(player_a, cash=bet)
                db_module.change_money(player_b, cash=bet)
                result = "Tie, bets returned."
            else:
                winner, loser = (player_a, player_b) if RPS_BEATS[pick_a] == pick_b else (player_b, player_a)
                result = win_text(winner, loser, bet, pay_pvp_winner(winner, bet))
            log_move(player_a, f"played rps vs {ui.tag(player_b)}", result)
            replace_message(respond, head + result, client=client, body=body)


#the 2 player blackjack
def bj2_state(game, player):
    value = hand_value(game["h"][player])
    if value > 21:
        return "💥 bust"
    if player in game["done"]:
        return "✋ stood"
    return "🤔 playing"


def bj2_view(game):
    text = (f"🃏 *Blackjack* | {ui.tag(game['a'])} vs {ui.tag(game['b'])} ({stake_text(game['bet'])})\n"
            + "\n".join(f"{ui.tag(player)}: {bj2_state(game, player)} · {len(game['h'][player])} cards"
                        for player in (game["a"], game["b"])))
    buttons = [ui.button("Hit", "pbj_hit", game["gid"], "primary"), ui.button("Stand", "pbj_stand", game["gid"]),
               ui.button("My hand", "pbj_hand", game["gid"])]
    return {"text": text, "blocks": [ui.section(text), {"type": "actions", "elements": buttons}]}


def bj2_result(game):
    player_a, player_b, bet = game["a"], game["b"], game["bet"]
    value_a, value_b = hand_value(game["h"][player_a]), hand_value(game["h"][player_b])
    score_a = 0 if value_a > 21 else value_a
    score_b = 0 if value_b > 21 else value_b
    head = (f"🃏 *Blackjack* | {ui.tag(player_a)} {hand_str(game['h'][player_a])} = *{value_a}*  vs  "
            f"{ui.tag(player_b)} {hand_str(game['h'][player_b])} = *{value_b}*\n")
    if score_a == score_b:
        db_module.change_money(player_a, cash=bet)
        db_module.change_money(player_b, cash=bet)
        result = "Tie, bets returned."
    else:
        winner, loser = (player_a, player_b) if score_a > score_b else (player_b, player_a)
        result = win_text(winner, loser, bet, pay_pvp_winner(winner, bet))
    log_move(player_a, f"played blackjack vs {ui.tag(player_b)}", result)
    return head + result


def register_pvp_bj_action(slack_app):
    @slack_app.action(re.compile(r"^pbj_(hit|stand|hand)$"))
    def pbj_action(ack, body, respond, action, client):
        ack()
        set_context(client, body)
        with db_module.lock:
            game = pvp_games.get(action["value"])
            user = body["user"]["id"]
            if not game:
                ui.only_you(respond, "That game has ended.", client, body)
                return
            if user not in (game["a"], game["b"]):
                ui.only_you(respond, "This isn't your game!", client, body)
                return
            hand = game["h"][user]
            kind = action["action_id"][4:]

            def my_hand():
                return f"Your hand: {hand_str(hand)} = *{hand_value(hand)}*"

            if kind == "hand":
                ui.only_you(respond, my_hand(), client, body)
                return
            if user in game["done"]:
                ui.only_you(respond, f"You're done, waiting for your opponent.\n{my_hand()}", client, body)
                return
            game["url"] = body.get("response_url") or game["url"]
            if kind == "hit":
                hand.append(game["deck"].pop())
                if hand_value(hand) >= 21:
                    game["done"].add(user)
            else:
                game["done"].add(user)
            busted = any(hand_value(game["h"][player]) > 21 for player in (game["a"], game["b"]))
            if busted or len(game["done"]) == 2:
                if game.get("timer"):
                    game["timer"].cancel()
                pvp_games.pop(game["gid"], None)
                replace_message(respond, bj2_result(game), client=client, body=body)
                return
            arm_pvp_timer(game)
            respond(replace_original=True, **ui.wire(ui.render(bj2_view(game), False)))
            ui.only_you(respond, my_hand(), client, body)


#tic tac toe
LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
CELL = {None: "⬜", "X": "❌", "O": "⭕"}
NUMS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]


def ttt_head(game):
    return f"*Tic Tac Toe* | ❌ {ui.tag(game['a'])} vs ⭕ {ui.tag(game['b'])} ({stake_text(game['bet'])})"


def board_text(board, numbers=False):
    def one_cell(index):
        if numbers and not board[index]:
            return NUMS[index]
        return CELL[board[index]]
    return "\n".join("".join(one_cell(row * 3 + column) for column in range(3)) for row in range(3))


def ttt_view(game):
    mark = "❌" if game["turn"] == game["a"] else "⭕"
    text = f"{ttt_head(game)}\nTurn: {mark} {ui.tag(game['turn'])}\n\n{board_text(game['board'], True)}"
    options = [{"text": {"type": "plain_text", "text": f"Square {index + 1}"}, "value": f"{game['gid']}:{index}"}
               for index in range(9) if not game["board"][index]]
    blocks = [ui.section(text), {"type": "actions", "elements": [
        {"type": "static_select", "action_id": "ttt_pick",
         "placeholder": {"type": "plain_text", "text": "Pick a square (1-9)"}, "options": options}]}]
    return {"text": text, "blocks": blocks}


@cmd("ttt")
def ttt(uid, args):
    if not args or not args[0].startswith("<"):
        return "❌ Usage: `/ttt @user [bet]`"
    return _make_challenge(uid, args, "ttt")


def register_ttt_action(slack_app):
    @slack_app.action("ttt_pick")
    def ttt_action(ack, body, respond, action, client):
        ack()
        set_context(client, body)
        with db_module.lock:
            pick = action.get("selected_option") or {}
            picked = pick.get("value") or action.get("value")
            if not picked:
                ui.only_you(respond, "Pick a square.", client, body)
                return
            gid, index = picked.split(":")
            game = pvp_games.get(gid)
            user = body["user"]["id"]
            if not game:
                ui.only_you(respond, "That game has ended.", client, body)
                return
            if user not in (game["a"], game["b"]):
                ui.only_you(respond, "This isn't your game!", client, body)
                return
            if user != game["turn"]:
                ui.only_you(respond, "It's not your turn!", client, body)
                return
            square = int(index)
            if game["board"][square]:
                ui.only_you(respond, "That square is taken.", client, body)
                return
            mark = "X" if user == game["a"] else "O"
            game["board"][square] = mark
            game["url"] = body.get("response_url") or game["url"]
            won = any(all(game["board"][spot] == mark for spot in line) for line in LINES)
            full = all(game["board"])
            if won or full:
                if game.get("timer"):
                    game["timer"].cancel()
                pvp_games.pop(game["gid"], None)
                bet = game["bet"]
                if won:
                    other = game["b"] if user == game["a"] else game["a"]
                    result = win_text(user, other, bet, pay_pvp_winner(user, bet))
                else:
                    db_module.change_money(game["a"], cash=bet)
                    db_module.change_money(game["b"], cash=bet)
                    result = "Draw, bets returned."
                log_move(game["a"], f"played tic tac toe vs {ui.tag(game['b'])}", result)
                replace_message(respond, f"{ttt_head(game)}\n{board_text(game['board'])}\n{result}",
                                client=client, body=body)
                return
            game["turn"] = game["b"] if user == game["a"] else game["a"]
            arm_pvp_timer(game)
            respond(replace_original=True, **ui.wire(ui.render(ttt_view(game), False)))
