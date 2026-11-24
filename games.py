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
    if args and args(0).startswith("<"):
        return _make_challenge(uid,args,"rps")
    bet,err=universalhelper(uid,args,"rps")
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
#Finish second part of rps
