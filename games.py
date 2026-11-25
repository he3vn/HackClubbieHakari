#This is going to be like the solo gambling games and the 2 players ones too yh
#So commands is supposed to parse the amount it takes in text and checks the number and return maximum or maximum/2 yh ima use this
import random
import database as db_module
import ui
from commands import cmd, parse_amount, add_usage_hint, scaled_win, GAME_TIMEOUT
import re
import uuid
import threading

SUITS = "♠♥♦♣"

def card_str(c):
    face = {1: "A", 11: "J", 12: "Q", 13: "K"}.get(c[0], str(c[0]))
    return f"`{face}{c[1]}`"

def hand_str(hand):
    return " ".join(card_str(c) for c in hand)

def schedule_refund(store, game_id):
    def refund():
        with db_module.lock:
            game = store.pop(game_id, None)
            if game:
                db_module.change_money(game["uid"], cash=game["bet"])
    t = threading.Timer(GAME_TIMEOUT, refund)
    t.daemon = True
    t.start()

def universalhelper(bet_text,maximum):
    if not bet_text:
        return None,"Enter a number"
    bet=parse_amount(bet_text,maximum)
    if bet is None:
        return None,"Type a valid number, 'half' or 'all'"
    if bet < 1:
        return None,"Bet should be at least 1 coin."
    if bet >maximum:
        return None,"You dont have enough cash gng"

    return bet,None


#Ima start with the easiest game to build(russina roulette baby)
def _rr_play(uid, bet_text):
    cash, _ = db_module.get_user(uid)
    bet, err = universalhelper(bet_text, cash)
    if err:
        return err
    number=random.randint(1,6) #Let me make some research on how russian roulette actually works,this is all I actually know its like you pick 1 number from 6
#Ok i get how it works i should like pick a number like 1 and then if that number = the random number that means he lost and he chose the wrong one
    mynumber=1
    if number == mynumber:
        db_module.change_money(uid,cash=-bet)
        return "You chose the wrong one bucko,now get shot!"
    else:
        profit=int(bet*0.2)
        db_module.change_money(uid,cash=profit)
        return "Bro actually didnt shoot himself lmao.Here is 20% more of ur money"

@cmd("roulette")
def russian_roulette(uid, args):
    return _rr_play(uid, args[0] if args else "")

#Now lets make rock-paper-scissors its way easier
_rps_games= {}
RPS_CHOICES={"rock":"🪨","paper":"📄","scissors": "✂️"}
RPS_BEATS= {"rock":"scissors","paper":"rock","scissors":"paper"}

@cmd("rps")
def rps(uid,args):
    if args and args[0].startswith("<"):
        return _make_challenge(uid,args,"rps")
    cash, _ = db_module.get_user(uid)
    bet,err=universalhelper(args[0] if args else "", cash)
    if err:
        return add_usage_hint(err, "\nHow to use gng: `/rps <bet|half|all>` (vs bot) or `/rps @user [bet]` (vs person)")
    db_module.change_money(uid,cash=-bet)
    gid = uuid.uuid4().hex[:8]
    _rps_games[gid]= {"gid":gid,"uid":uid,"bet":bet}
    schedule_refund(_rps_games,gid)
    buttons = [ui.button(f"{emoji} {move.title()}", f"rps_{move}", gid) for move, emoji in RPS_CHOICES.items()]
    return ui.embed(
        f"✊ *Rock Paper Scissors* · {ui.tag(uid)} bet {ui.fmt(bet)}\nPick your move!",
        ui.BLUE, nolog=True, buttons=buttons + [ui.HELP_BUTTON],
    )
#Finish second part of rps,back(will be adding less comments to avoid fraud)
def register_rps_action(slack_app):
    @slack_app.action(re.compile(r"^rps_(rock|paper|scissors)$"))
    def rps_action(ack,body,respond,action):
        ack()
        with db_module.lock:
            game = _rps_games.get(action["value"])
            if not game:
                ui.only_you(respond,"That game ended bro.")
                return
            if body["user"]["id"] != game["uid"]:
                ui.only_you(respond,"This aint your game😭")
                return
            player_move = action["action_id"][4:]
            bot_move=random.choice(list(RPS_CHOICES))
            uid, bet = game["uid"], game["bet"]
            if player_move==bot_move:
                profit,result,color= 0, "Tie,the money is returned",ui.GREY
            elif RPS_BEATS[player_move]==bot_move:
                profit,result,color=scaled_win(uid,bet,2),"You win.",ui.GREEN
            else:
                profit,result,color= -bet,"You lose haaha.",ui.RED
            if bet + profit:
                db_module.change_money(uid,cash=bet +profit)
            _rps_games.pop(action["value"], None)
            ui.swap(respond,ui.embed(
                f"*Rock Paper Scissors* · {ui.tag(uid)} bet {ui.fmt(bet)}\n"
                f"You: {RPS_CHOICES[player_move]} {player_move}  vs  Bot: {RPS_CHOICES[bot_move]} {bot_move}\n"
                f"*{result}*  *{ui.signed(profit)}*",
                color, nolog=True, buttons=[ui.HELP_BUTTON],
            ), db_module.db, db_module.lock)

#Time to do roulette
@cmd("lesgamble")
def lesgamble(uid,args):
    if len(args) <2:
        return "How to use: /lesgamble <red|black|green|0-36> <bet>"
    choice=args[0].lower()
    integer=random.randint(0,36)
    valid_colors=("red","black","green")
    if choice not in valid_colors and not (choice.isdigit() and 0 <= int(choice) <= 36):
        return "Pick red,black, gren or a number from 0 to 36.read!"
    red={1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36} #the others are black
    green=0
    if integer in red:
        rolledcolor="red"
    elif integer == green:
        rolledcolor="green"
    else:
        rolledcolor="black"
    cash, _ = db_module.get_user(uid)
    bet,err=universalhelper(args[1],cash)
    if err:
        return add_usage_hint(err, "\nHow to use: /lesgamble <red|black|green|0-36> <bet>")
    if choice.isdigit():
        profit=bet *35 if int(choice)==integer else -bet
    elif choice =="green":
        profit=bet*14 if rolledcolor=="green" else -bet
    else:
        profit=bet if choice ==rolledcolor else -bet
    db_module.change_money(uid,cash=profit)
    return f"Ball landed on *{integer} ({rolledcolor})* | {ui.signed(profit)}"

#Les do higher/lower should be pretty free
hl_games={}
def get_hl_multiplier(chance):
    if chance <= 0:
        return None
    payout=0.97/chance
    if payout > 12.0:
        return 12.0
    return payout
def build_hl_screen(game):
    first_card = game["card"]
    card_number=first_card[0]

    higher_chance=(13-card_number)/13
    lower_chance=(card_number-1)/13
    buttons =[]

    if higher_chance >0:
        high_mult=get_hl_multiplier(higher_chance)
        buttons.append(ui.button(f"⬆️ Higher  x{high_mult:.2f}", "hl_higher", game["gid"], "primary"))
    if lower_chance >0:
        low_mult=get_hl_multiplier(lower_chance)
        buttons.append(ui.button(f"⬇️ Lower  x{low_mult:.2f}", "hl_lower", game["gid"]))
    buttons.append(ui.HELP_BUTTON)

    return ui.embed(
        f"🔼 *Higher or Lower* · {ui.tag(game['uid'])} · bet {ui.fmt(game['bet'])}\n\n"
        f"Current card: {card_str(first_card)}\n"
        f"Will the next card be higher or lower? (A is low, K is high, ties lose)",
        ui.BLUE,
        nolog=True,
        buttons=buttons,
        footer="The payour is bigger when the guess is less likely."
    )

def start_hl_game(uid,bet_text):
    cash,_=db_module.get_user(uid)
    bet,err=universalhelper(bet_text,cash)
    if err:
        return add_usage_hint(err, "\nUsage: `/higher-lower <bet|half|all>`")

    db_module.change_money(uid,cash=-bet)
    game_id = uuid.uuid4().hex[:8]
    starting_card = (random.randint(1, 13), random.choice(SUITS))
    game= {
        "gid":game_id,
        "uid":uid,
        "bet":bet,
        "card":starting_card
    }
    hl_games[game_id]=game
    schedule_refund(hl_games,game_id)
    return build_hl_screen(game)

@cmd("higher-lower")
def higher_lower(uid,args):
    bet_text = args[0] if args else ""
    return start_hl_game(uid,bet_text)

def register_hl_action(slack_app):
    @slack_app.action(re.compile(r"^hl_(higher|lower)$"))
    def hl_action(ack,body,respond,action):
        ack()
        with db_module.lock:
            game_id = action["value"]
            game=hl_games.get(game_id)

            if not game:
                ui.only_you(respond,"The game ended bro.")
                return
            uid=game["uid"]
            bet=game["bet"]

            if body["user"]["id"] != uid:
                ui.only_you(respond,"This ain't your game!")
                return

            hl_games.pop(game_id)
            first_card=game["card"]
            next_card = (random.randint(1, 13), random.choice(SUITS))
            first_number = first_card[0]
            next_number=next_card[0]
            if action["action_id"] == "hl_higher":
                chance=(13-first_number)/13
                player_won=next_number >first_number
            else:
                chance=(first_number-1) /13
                player_won=next_number < first_number

            if player_won:
                mult=get_hl_multiplier(chance)
                profit=scaled_win(uid,bet,mult-1)
                db_module.change_money(uid,cash=bet+profit)
                result_text="You win💢"
                card_color=ui.GREEN
            else:
                profit= -bet
                result_text="You lose HAHAA"
                card_color=ui.RED

            play_again_btn = ui.button("▶️ Play Again", "hl_again", f"{uid}:{bet}", "primary")

            ui.swap(
                respond,
                ui.embed(
                    f"🔼 *Higher or Lower* · {ui.tag(uid)} · bet {ui.fmt(bet)}\n\n"
                    f"{card_str(first_card)} → {card_str(next_card)}\n"
                    f"*Result:* {result_text}  *{ui.signed(profit)}*",
                    card_color,
                    nolog=True,
                    buttons=[play_again_btn, ui.HELP_BUTTON],
                ),
                db_module.db,
                db_module.lock,
            )

#Les do slots(this sounds really bad but i dont support gambling)
SLOT_SYMBOLS=["🍒", "🍒", "🍒", "🍋", "🍋", "🍇", "🔔", "💎", "7️⃣"]
SLOT_PAYOUTS={
    "7️⃣":10,
    "💎":7,
    "🔔":5,
    "🍇":4,
    "🍋":3,
    "🍒":3,
}
@cmd("slots")
def slots(uid,args):
    cash,_=db_module.get_user(uid)
    bet_text=args[0] if args else ""
    bet,err=universalhelper(bet_text,cash)
    if err:
        return add_usage_hint(err, "\nUsage: `/slots <bet|half|all>`")
    reel1=random.choice(SLOT_SYMBOLS)
    reel2=random.choice(SLOT_SYMBOLS)
    reel3=random.choice(SLOT_SYMBOLS)

    if reel1 == reel2 == reel3:
        mult=SLOT_PAYOUTS[reel1]
        profit = scaled_win(uid, bet, mult - 1)
        result_text = f"JACKPOTTTTT! Triple {reel1}!"
        color=ui.GREEN
    elif reel1 ==reel2 or reel2 ==reel3 or reel1 ==reel3:
        profit= scaled_win(uid,bet,0.5)
        result_text="Nice. Two matched"
        color=ui.GREEN
    else:
        profit=-bet
        result_text="No match,better luck next time bozo."
        color=ui.RED
    db_module.change_money(uid,cash=profit)
    return ui.embed(
            f"🎰 *Slots* · {ui.tag(uid)} · bet {ui.fmt(bet)}\n\n"
            f"[ {reel1} | {reel2} | {reel3} ]\n\n"
            f"*{result_text}*  *{ui.signed(profit)}*",
            color,
            nolog=True,
            buttons=[ui.HELP_BUTTON],
    )

#Blackjack solo ima make 2 Player games later lowk
def new_deck():
    SUITS = ["♠", "♥", "♦", "♣"]
    deck = []
    for rank in range(1, 14):
        for s in SUITS:
            deck.append((rank, s))
    random.shuffle(deck)
    return deck
def hand_value(hand):
    total=0
    has_ace=False
    for card in hand:
        rank=card[0]
        if rank ==1:
            has_ace=True
            total +=1
        elif rank >=10:
            total += 10
        else:
            total +=rank
    if has_ace and total + 10 <= 21:
        total+=10
    return total
bj_games= {}
def build_bj_screen(game,finished=False):
    uid=game["uid"]
    bet=game["bet"]
    player_hand=game["player"]
    dealer_hand=game["dealer"]
    if finished:
        result_label,profit=game["result"]
        if profit >0:
            color=ui.GREEN
        elif profit == 0:
            color=ui.GREY
        else:
            color=ui.RED
        header = f"🃏 *Blackjack* · {ui.tag(uid)} · bet {ui.fmt(bet)}\n*Result:* {result_label}  *{ui.signed(profit)}*"
        dealer_text = f"{hand_str(dealer_hand)}\nValue: {hand_value(dealer_hand)}"
        play_again_btn = ui.button("▶️ Play Again", "bj_again", f"{uid}:{game['bet0']}", "primary")
        buttons = [play_again_btn, ui.HELP_BUTTON]
    else:
        color=ui.BLUE
        header = f"🃏 *Blackjack* · {ui.tag(uid)} · bet {ui.fmt(bet)}"
        dealer_text = f"{card_str(dealer_hand[0])} `?`\nValue: ?"
        buttons =[
            ui.button("Hit", "bj_hit", game["gid"], "primary"),
            ui.button("Stand", "bj_stand", game["gid"]),
        ]
        cash,_=db_module.get_user(uid)
        if len(player_hand)== 2 and cash >= bet:
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
def finish_bj_game(game,natural=False):
    player_val = hand_value(game["player"])
    #Ima start commeting more lemme make sure the dealer keeps hitting until he reaches 17
    while hand_value(game["dealer"]) <17 and player_val <= 21:
        game["dealer"].append(game["deck"].pop())
    dealer_val = hand_value(game["dealer"])
    bet=game["bet"]
    uid=game["uid"]

    if player_val>21:
        label="Bust"
        profit=-bet
    elif natural and dealer_val !=21:
        label="Blackjack!"
        profit=scaled_win(uid,bet,5)
    elif dealer_val >21 or player_val > dealer_val:
        if dealer_val > 21:
            label="Dealer got over 21.You win"
        else:
            label="You win"
        if player_val==21:
            label="21! " + label
            profit=scaled_win(uid,bet,3)
        else:
            profit=scaled_win(uid,bet,2)
    elif player_val == dealer_val:
        label="Push"
        profit=0
    else:
        label="Dealer wins."
        profit=-bet
    if bet+ profit >0:
        db_module.change_money(uid,cash=bet + profit)

    bj_games.pop(game["gid"], None)
    game["result"] = (label, profit)

def bj_timeout(gid):
    with db_module.lock:
        game=bj_games.get(gid)
        if game:
            finish_bj_game(game)
def start_bj_game(uid,bet_text):
    cash,_=db_module.get_user(uid)
    bet,err=universalhelper(bet_text,cash)
    if err:
        return add_usage_hint(err, "\nUsage: `/blackjack <bet|half|all>`")
    db_module.change_money(uid,cash=-bet)
    deck=new_deck()
    game_id=uuid.uuid4().hex[:8]

    game={
        "gid":game_id,
        "uid":uid,
        "bet":bet,
        "bet0":bet,
        "deck":deck,
        "player": [deck.pop(), deck.pop()],
        "dealer": [deck.pop(), deck.pop()],
    }
    bj_games[game_id]=game

    timer=threading.Timer(GAME_TIMEOUT,lambda:bj_timeout(game_id))
    timer.daemon=True
    timer.start()

    if hand_value(game["player"]) == 21:
        finish_bj_game(game,natural=True)
        return build_bj_screen(game,finished=True)

    return build_bj_screen(game)

@cmd("blackjack")
def blackjack(uid,args):
    if args and args[0].startswith("<"):
        return _make_challenge(uid,args,"bj")
    bet_text=args[0] if args else ""
    return start_bj_game(uid,bet_text)
def register_bj_actions(slack_app):
    @slack_app.action(re.compile(r"^bj_(hit|stand|double)$"))
    def bj_action(ack,body,respond,action):
        ack()
        with db_module.lock:
            game_id=action["value"]
            game=bj_games.get(game_id)
            if not game:
                ui.only_you(respond,"The game ended bro.")
                return
            if body["user"]["id"] != game["uid"]:
                ui.only_you(respond,"This aint your game")
                return
            btn_clicked=action["action_id"]

            if btn_clicked=="bj_hit":
                game["player"].append(game["deck"].pop())
                if hand_value(game["player"]) < 21:
                    ui.swap(respond,build_bj_screen(game),db_module.db,db_module.lock)
                    return
            elif btn_clicked=="bj_double":
                cash, _ = db_module.get_user(game["uid"])
                if len(game["player"]) != 2 or cash < game["bet"]:
                    ui.only_you(respond,"You cant double down now.")
                    return
                db_module.change_money(game["uid"], cash=-game["bet"])
                game["bet"] *= 2
                game["player"].append(game["deck"].pop())

            finish_bj_game(game)
            ui.swap(respond, build_bj_screen(game, finished=True), db_module.db, db_module.lock)
