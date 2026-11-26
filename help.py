#Help part when pinging the bot and like the /ecohelp command
import ui
from commands import ADMINS, cmd

INTRO = ("Yo, this is my gambling bot. Type `/` in the chat to see za commands")

PLAIN_COMMANDS = (
    "/balance · /deposit · /withdraw · /give · /leaderboard · /stats · "
    "/work · /crime · /rob · /collect · /blackjack · /slots · /higher-lower · "
    "/roulette · /lesgamble · /rps · /ttt · /roll · /catalog · /buy · /inventory · "
    "/use · /ecohelp · /admin"
)


def help_blocks(admin=False):
    parts = [
        f"*Money*\n"
        "`/balance [@user]` – see how much cash you got and how much in bank. Cash can be robbed, bank can't.\n"
        "`/deposit <amount|half|all>` –  put za cash in the bank so u not robbalbe.\n"
        "`/withdraw <amount|half|all>` – take money out of the bank.\n"
        "`/give @user <amount>` – send cash to someone.\n"
        "`/leaderboard [page]` – THE RICHEST THE ELITE YOU CAN SEE THEM HERE\n"
        "`/stats` – how many coins exist in total.",

        "*Earn coins*\n"
        "`/work` – Ts a safe job and you aint my homie if u do it,doesnt pay alot.\n"
        "`/crime` – 60% win 200-900 coins, but if you get caught you pay a fine\n"
        "`/rob @user` – This is where u get the big  u can get up to 90 percent of their *cash*. If you fail you pay them 15-30% of yours.\n"
        "`/collect` – daily reward of 1k\n"
        "Just chatting gives 10-30 coins every 30s.",

        "*Games vs the bot* (only you see them)\n"
        "`/blackjack <bet>` – beat the dealer without going over 21. "
        "Or `/blackjack @user [bet]` to play a person: highest hand up to 21 wins.\n"
        "`/slots <bet>` – 3 reels. Pair 1x, three of a kind 4x, up to 30x for triple 7️⃣.\n"
        "`/higher-lower <bet>` – guess if the next card is higher or lower. Riskier guesses pay more.\n"
        "`/roulette <bet>` – russian roulette, 1 bullet in 6 (i feel like a sheriff). Survive and win 20%, else lose the bet.\n"
        "`/rps <bet>` – rock paper scissors against the bot, win 2x.",

        "*Roulette* (shared table, everybody can join!)\n"
        "`/lesgamble <space> <bet>` – the first bet opens a table, anyone can join with their own bet. "
        "The wheel spins 10s after the last bet (max 60s) and everybody gets paid at the same time.\n"

        "*Play against people*\n"
        "`/rps @user [bet]` – rock paper scissors vs a person.\n"
        "`/ttt @user [bet]` – tic tac toe vs a person (pick squares from the dropdown).\n"
        "`/roll [max]` – roll a dice, or `/roll pizza, more pizza, pineapple` to pick for you.",

        "*Shop*\n"
        "`/catalog [item]` – items for sale. `/buy <item> [amount]` · `/inventory` · `/use <item> [amount]`",

        f"*Good to know*\n"
        f"Bets accept numbers, `5k`, `half` or `all`. Amounts also accept suffixes: "
        "`k` `m` `b` `t` `q` `qi` `z` `y` (so `9qi` = 9,000,000,000,000,000,000). There are no bet limits. "
        "Payouts shrink a little when you're very rich (over 100k) so nobody snowballs forever. "
        "Money and solo-game commands are only visible to you; rob, give, lesgamble and challenges are public.\n"
        "Top the `/leaderboard` and you can win prizes too! One star = one quintillion you hold.",
    ]
    if admin:
        parts.append("*Admin (only you can see this)*\n"
                     "`/admin help` lists every admin tool (nuke, cap, set, take, undo, ban, item-remove…)\n"
                     "`/admin add-money @user <amount>` · `/admin create-item <name> <price> <description>` · "
                     "`/admin delete-item <name>` · `/admin audit @user`\n"
                     "`/admin set-decks <1-8>` · "
                     "`/admin set-cooldown <usages> <duration>` (e.g. `4 5m`)")
    parts.append(f"*All commands*\n{PLAIN_COMMANDS}")
    return [ui.section(INTRO)] + [ui.section(part) for part in parts]


@cmd("ecohelp")
def ecohelp(uid, args):
    return {"text": INTRO, "blocks": help_blocks(uid in ADMINS), "response_type": "ephemeral", "nolog": True}
