"""Generate DF item raws for the shop goods of a specific AP seed.

The AP shop sells arbitrary multiworld items whose names are only known once the
client scouts them. DF can only render names that exist in the raws, so before
the world is generated we bake the scouted shop list into raws the native trade
screen can show with no overlay.

Layout (chosen so DF's own trade screen groups the goods under one header per
tier): every good is a copy of a shared per-tier AP-logo tool, so DF files them
all under a single "AP Items (Tier N)" category. The good's individual name rides
in a custom inorganic material (one per slot), so the trade row reads
"<good name> AP Items (Tier N)". Five tier tools are static; the materials are
per-seed.

No entity is granted these tools, so no civilization crafts or trades them -- they
only exist when the mod DFHack-creates one for the Archipelago caravan.
"""
import os
import re
import unicodedata

TOOL_PREFIX = "ITEM_TOOL_AP_TIER"      # shared per-tier grouping tool
MAT_PREFIX = "AP_SHOP_"                # per-slot inorganic carrying the good name
TILE_PAGE = "DWARFIPELAGO_ITEMS"       # shared AP-logo tile page (tile_page_dwarfipelago.txt)
MAX_TIER = 5
_MAX_NAME = 48                         # keep DF name tokens sane
# DF values a tool as (item [VALUE]) x (material MATERIAL_VALUE). The tier tools
# carry TOOL_VALUE; the per-slot material carries MATERIAL_VALUE = price/TOOL_VALUE,
# so the native trade screen charges each slot's rolled price (tier-banded and
# scaled by shop_price_multiplier at gen time).
TOOL_VALUE = 100


# Punctuation other games use that NFKD leaves alone; without these a name like
# "Hero’s Laurels" has no ASCII form at all.
_PUNCT = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
    "\u2013": "-", "\u2014": "-", "\u2015": "-", "\u2212": "-", "\u00b7": "-",
    "\u2026": "...", "\u00d7": "x", "\u00f7": "/", "\u00a0": " ",
    "\u2122": "TM", "\u00ae": "(R)", "\u00a9": "(C)",
    "\u00e6": "ae", "\u00c6": "AE", "\u0153": "oe", "\u0152": "OE",
    "\u00df": "ss", "\u00f8": "o", "\u00d8": "O", "\u0142": "l", "\u0141": "L",
    "\u00f0": "d", "\u00d0": "D", "\u00fe": "th", "\u00de": "Th",
}


def sanitize_name(text: str, fallback: str = "Archipelago Item") -> str:
    """Make an arbitrary multiworld item name safe for a DF name token.

    DF raws are single-byte text, so the name has to survive as ASCII: accents are
    folded (Pokémon -> Pokemon), the punctuation above is mapped, and anything
    still outside printable ASCII (CJK, emoji, box drawing) is dropped. Also drops
    the token delimiters [ ] : |, collapses whitespace, and caps the length.
    Returns `fallback` when nothing usable is left -- an unrenderable name must not
    produce an empty token."""
    text = "".join(_PUNCT.get(ch, ch) for ch in str(text))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = "".join(ch if 32 <= ord(ch) < 127 else " " for ch in text)
    text = re.sub(r"[\[\]:|]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(" -")   # dropped scripts can leave a dangling separator
    return (text or fallback)[:_MAX_NAME]


def _clamp_tier(v) -> int:
    try:
        t = int(v)
    except (TypeError, ValueError):
        t = 1
    return max(1, min(MAX_TIER, t))


def _material_value(price) -> int:
    """The MATERIAL_VALUE that makes DF value this good at `price` on the trade
    screen (item value = TOOL_VALUE x MATERIAL_VALUE). Quantized to TOOL_VALUE."""
    try:
        p = int(price)
    except (TypeError, ValueError):
        return 1
    return max(1, round(p / TOOL_VALUE))


def build_shop_goods(shop_entries):
    """shop_entries: iterable of dicts with slot, item, player, tier, price.
    Returns [{slot, tier, mat_id, name, material_value}] -- one custom inorganic
    per slot, named after the good and priced via its material value."""
    goods = []
    for e in shop_entries:
        slot = int(e["slot"])
        # A slot whose scout reply has not arrived still gets its material, so the
        # price is always baked; only the name falls back to the slot number.
        base = sanitize_name(e.get("item") or "", f"Archipelago Item (Slot {slot})")
        player = sanitize_name(e.get("player") or "", "")
        name = f"{base} ({player})" if player else base
        name = name[:_MAX_NAME]
        goods.append({
            "slot": slot,
            "tier": _clamp_tier(e.get("tier", 1)),
            "mat_id": f"{MAT_PREFIX}{slot}",
            "name": name,
            "material_value": _material_value(e.get("price")),
        })
    goods.sort(key=lambda g: g["slot"])
    return goods


def render_item_raws() -> str:
    """The five static per-tier grouping tools. Every good is a copy of one of
    these, so DF groups them under "AP Items (Tier N)"."""
    out = ["item_dwarfipelago_shop", "", "[OBJECT:ITEM]", ""]
    out.append("\tShared per-tier AP-logo tools. The good's real name lives in a")
    out.append("\tper-slot inorganic material (inorganic_dwarfipelago_shop.txt).")
    out.append("")
    for tier in range(1, MAX_TIER + 1):
        name = f"AP Items (Tier {tier})"
        out += [
            f"[ITEM_TOOL:{TOOL_PREFIX}{tier}]",
            f"\t[NAME:{name}:{name}]",
            f"\t[VALUE:{TOOL_VALUE}]",
            "\t[TILE:15]",
            "\t[HARD_MAT]",
            "\t[SIZE:200]",
            "\t[MATERIAL_SIZE:1]",
            "\t[NO_DEFAULT_JOB]",
            "",
        ]
    return "\n".join(out) + "\n"


def render_inorganic_raws(goods) -> str:
    """One inorganic per slot; its solid-state name is the good's display name,
    so the trade row reads "<good name> AP Items (Tier N)"."""
    out = ["inorganic_dwarfipelago_shop", "", "[OBJECT:INORGANIC]", ""]
    out.append("\tOne stone per shop slot, named after the good it stands for.")
    out.append("")
    for g in goods:
        out += [
            f"[INORGANIC:{g['mat_id']}]",
            "\t[USE_MATERIAL_TEMPLATE:STONE_TEMPLATE]",
            f"\t[STATE_NAME_ADJ:ALL_SOLID:{g['name']}]",
            # Prices the good on the native trade screen: item value =
            # TOOL_VALUE x MATERIAL_VALUE (see TOOL_VALUE).
            f"\t[MATERIAL_VALUE:{g['material_value']}]",
            "\t[DISPLAY_COLOR:7:0:0]",
            "\t[IS_STONE]",
            "",
        ]
    return "\n".join(out) + "\n"


def render_graphics_raws() -> str:
    out = ["graphics_dwarfipelago_shop", "", "[OBJECT:GRAPHICS]", ""]
    out.append("\tEvery tier tool renders with the shared AP-logo tile.")
    out.append("")
    for tier in range(1, MAX_TIER + 1):
        out.append(f"[TOOL_GRAPHICS:{TILE_PAGE}:0:0:{TOOL_PREFIX}{tier}]")
    return "\n".join(out) + "\n"


def _write_raw(path, text):
    """Write one raw file. DF reads raws as single-byte text; errors="replace" is a
    backstop so a character sanitize_name missed degrades to "?" instead of raising
    mid-write and leaving the file truncated (which silently costs every good its
    name and price)."""
    with open(path, "w", encoding="latin-1", errors="replace") as f:
        f.write(text)


def generate(shop_entries, objects_dir, graphics_dir):
    """Write the per-seed shop raws and return the slot -> {tier, mat_id} map the
    in-game side uses to create the right tool+material per slot."""
    goods = build_shop_goods(shop_entries)
    os.makedirs(objects_dir, exist_ok=True)
    os.makedirs(graphics_dir, exist_ok=True)
    _write_raw(os.path.join(objects_dir, "item_dwarfipelago_shop.txt"), render_item_raws())
    _write_raw(os.path.join(objects_dir, "inorganic_dwarfipelago_shop.txt"),
               render_inorganic_raws(goods))
    _write_raw(os.path.join(graphics_dir, "graphics_dwarfipelago_shop.txt"), render_graphics_raws())
    return {str(g["slot"]): {"tier": g["tier"], "mat_id": g["mat_id"]} for g in goods}


if __name__ == "__main__":
    import tempfile
    sample = [
        {"slot": 1, "item": "Forge Blueprint", "player": "You", "tier": 1, "price": 2500},
        {"slot": 2, "item": "Progressive Sword: Tier [3]", "player": "Alice", "tier": 2, "price": 30000},
        {"slot": 3, "item": "Hero\u2019s Laurels \u2014 Pok\u00e9mon", "player": "Bob", "tier": 5, "price": 90000},
        {"slot": 4, "item": "", "player": "", "tier": 3, "price": 50000},  # scout not in yet
    ]
    d = tempfile.mkdtemp()
    m = generate(sample, d, d)
    print("slot->good:", m)
    print("--- item raws ---")
    print(open(os.path.join(d, "item_dwarfipelago_shop.txt")).read())
    print("--- inorganic raws ---")
    print(open(os.path.join(d, "inorganic_dwarfipelago_shop.txt")).read())
