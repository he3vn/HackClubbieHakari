#This is going to be like the solo gambling games and the 2 players ones too yh
#So commands is supposed to parse the amount it takes in text and checks the number and return maximum or maximum/2 yh ima use this
import random
import database as db_module
import ui
from commands import cmd, parse_amount

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
