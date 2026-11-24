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
_name_cache={}
app=None
