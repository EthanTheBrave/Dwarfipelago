"""Generate DF item raws for the shop goods of a specific AP seed.

The AP shop sells arbitrary multiworld items whose names are only known once the
client scouts them. DF can only render an item name that exists in the raws, so
before the DF world is generated we turn the scouted shop list into one
"orphan" AP-logo tool per slot (named exactly per the good) plus its graphics
mapping. World-gen then bakes those items in with real names, and the caravan
can carry them on the native trade screen with no overlay.

No entity is ever granted these tools, so no civilization crafts or trades them
-- they only exist when the mod DFHack-creates one for the Archipelago caravan.
"""
import json
import os
import re

TOOL_PREFIX = "ITEM_TOOL_AP_SHOP_"
TILE_PAGE = "DWARFIPELAGO_ITEMS"   # shared AP-logo tile page (tile_page_dwarfipelago.txt)
_MAX_NAME = 48                     # keep DF [NAME] tokens sane


def sanitize_name(text: str) -> str:
    """Make an arbitrary multiworld item name safe for a DF [NAME:...] token:
    drop the token delimiters [ ] :, collapse whitespace, and cap the length."""
    text = re.sub(r"[\[\]:|]", " ", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        text = "Archipelago Item"
    return text[:_MAX_NAME]


def build_shop_tools(shop_entries):
    """shop_entries: iterable of dicts with slot, item, player (as _sync_shop
    builds). Returns [{slot, tool_id, name, item, player}] with a stable tool id
    per slot."""
    tools = []
    for e in shop_entries:
        slot = int(e["slot"])
        # Name the good, tagging the recipient so identical items on different
        # slots stay distinguishable, e.g. "Forge Blueprint (Alice)".
        base = sanitize_name(e.get("item", "Archipelago Item"))
        player = str(e.get("player", "")).strip()
        name = f"{base} ({player})" if player else base
        name = name[:_MAX_NAME]
        tools.append({
            "slot": slot,
            "tool_id": f"{TOOL_PREFIX}{slot}",
            "name": name,
            "item": e.get("item", ""),
            "player": player,
        })
    tools.sort(key=lambda t: t["slot"])
    return tools


def _plural(name: str) -> str:
    # These are unique display-only trade goods (one per slot), so a plural is
    # never actually shown; reuse the singular to avoid odd "...(You)s" forms.
    return name


def render_item_raws(tools) -> str:
    out = ["item_dwarfipelago_shop", "", "[OBJECT:ITEM]", ""]
    out.append("\tGenerated per AP seed by apraws.py -- one orphan AP-logo tool")
    out.append("\tper shop slot, named after the good it stands for.")
    out.append("")
    for t in tools:
        out += [
            f"[ITEM_TOOL:{t['tool_id']}]",
            f"\t[NAME:{t['name']}:{_plural(t['name'])}]",
            "\t[VALUE:100]",
            "\t[TILE:15]",
            "\t[HARD_MAT]",
            "\t[SIZE:200]",
            "\t[MATERIAL_SIZE:1]",
            "\t[NO_DEFAULT_JOB]",
            "",
        ]
    return "\n".join(out) + "\n"


def render_graphics_raws(tools) -> str:
    out = ["graphics_dwarfipelago_shop", "", "[OBJECT:GRAPHICS]", ""]
    out.append("\tEvery shop good renders with the shared AP-logo tile.")
    out.append("")
    for t in tools:
        out.append(f"[TOOL_GRAPHICS:{TILE_PAGE}:0:0:{t['tool_id']}]")
    return "\n".join(out) + "\n"


def generate(shop_entries, objects_dir, graphics_dir):
    """Write the per-seed shop item + graphics raws and return the slot->tool_id
    map (which the in-game side uses to inject the right tool per slot)."""
    tools = build_shop_tools(shop_entries)
    os.makedirs(objects_dir, exist_ok=True)
    os.makedirs(graphics_dir, exist_ok=True)
    with open(os.path.join(objects_dir, "item_dwarfipelago_shop.txt"), "w", encoding="latin-1") as f:
        f.write(render_item_raws(tools))
    with open(os.path.join(graphics_dir, "graphics_dwarfipelago_shop.txt"), "w", encoding="latin-1") as f:
        f.write(render_graphics_raws(tools))
    return {str(t["slot"]): t["tool_id"] for t in tools}


if __name__ == "__main__":
    # quick self-test with a couple of fake shop entries
    import tempfile
    sample = [
        {"slot": 1, "item": "Forge Blueprint", "player": "You"},
        {"slot": 2, "item": "Progressive Sword: Tier [3]", "player": "Alice"},
        {"slot": 3, "item": "50 Rupees", "player": "Bob"},
    ]
    d = tempfile.mkdtemp()
    m = generate(sample, d, d)
    print("slot->tool:", m)
    print("--- item raws ---")
    print(open(os.path.join(d, "item_dwarfipelago_shop.txt")).read())
