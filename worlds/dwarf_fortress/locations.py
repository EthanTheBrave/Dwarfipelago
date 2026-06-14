from dataclasses import dataclass
from typing import List, Optional

BASE_ID = 37370000


@dataclass
class LocationData:
    name: str
    ap_id: int
    region: str = "Fortress"
    goal_only: bool = False  # if True, only relevant for a specific goal
    material_type: str = ""
    df_item: str = ""
    threshold: int = 0


# ── Wealth Milestones ─────────────────────────────────────────────────────────
WEALTH_LOCATIONS: list[LocationData] = [
    LocationData("Humble Beginnings (1,000)",    BASE_ID + 0,  "Fortress"),
    LocationData("Growing Stronghold (10,000)",  BASE_ID + 1,  "Fortress"),
    LocationData("Prosperous Fortress (50,000)", BASE_ID + 2,  "Fortress"),
    LocationData("Rich Citadel (100,000)",       BASE_ID + 3,  "Fortress"),
    LocationData("Legendary Vault (500,000)",    BASE_ID + 4,  "Fortress"),
]

# ── First Production Milestones ───────────────────────────────────────────────
PRODUCTION_LOCATIONS: list[LocationData] = [
    LocationData("First Crafted Item",       BASE_ID + 100, "Fortress"),
    LocationData("First Weapon Forged",      BASE_ID + 101, "Fortress"),
    LocationData("First Armor Crafted",      BASE_ID + 102, "Fortress"),
    LocationData("First Furniture Made",     BASE_ID + 103, "Fortress"),
    LocationData("First Prepared Meal",      BASE_ID + 104, "Fortress"),
    LocationData("First Brew Complete",      BASE_ID + 105, "Fortress"),
    LocationData("First Metal Bar Smelted",  BASE_ID + 106, "Fortress"),
    LocationData("First Block Cut",          BASE_ID + 107, "Fortress"),
    LocationData("First Cloth Woven",        BASE_ID + 108, "Fortress"),
    LocationData("First Leather Tanned",     BASE_ID + 109, "Fortress"),
    LocationData("First Gem Cut",            BASE_ID + 110, "Fortress"),
    LocationData("First Mechanism Made",     BASE_ID + 111, "Fortress"),
    LocationData("First Trap Built",         BASE_ID + 112, "Fortress"),
    LocationData("First Cage Constructed",   BASE_ID + 113, "Fortress"),
    LocationData("First Barrel Made",        BASE_ID + 114, "Fortress"),
    LocationData("First Chest Made",         BASE_ID + 115, "Fortress"),
    LocationData("First Table Made",         BASE_ID + 116, "Fortress"),
    LocationData("First Bed Made",           BASE_ID + 117, "Fortress"),
    LocationData("First Anvil Made",         BASE_ID + 118, "Fortress"),
    LocationData("First Millstone Made",     BASE_ID + 119, "Fortress"),
    LocationData("First Minecart Made",      BASE_ID + 120, "Fortress"),
]

# ── Trade / Export Milestones ─────────────────────────────────────────────────
TRADE_LOCATIONS: list[LocationData] = [
    LocationData("Dwarven Caravan Visit",          BASE_ID + 202, "Fortress"),
    LocationData("Elven Caravan Visit",            BASE_ID + 203, "Fortress"),
    LocationData("Human Caravan Visit",            BASE_ID + 204, "Fortress"),
    LocationData("Outpost Liaison Meeting",        BASE_ID + 205, "Fortress"),
    LocationData("First Raid",                     BASE_ID + 206, "Fortress"),
    LocationData("First Artifact Recovery",        BASE_ID + 207, "Fortress"),
    LocationData("First Act of Diplomacy",         BASE_ID + 208, "Fortress"),
]

# ── Fortress Status / Noble Appointments ──────────────────────────────────────
# IDs match checks.lua (BASE_ID + 300+).
# These track the civilisation's recognition of the fortress, from a mayor-run
# settlement up to a capital with a resident monarch.
STATUS_LOCATIONS: list[LocationData] = [
    LocationData("Mayor Elected",           BASE_ID + 300, "Fortress"),
    LocationData("Baron Appointed",         BASE_ID + 301, "Fortress"),
    LocationData("Count Appointed",         BASE_ID + 302, "Fortress"),
    LocationData("Duke Appointed",          BASE_ID + 303, "Fortress"),
    LocationData("Monarch Takes Residence", BASE_ID + 304, "Fortress"),
]

# ── Fortress Title Milestones ─────────────────────────────────────────────────
# Each title requires population AND either created-wealth OR exported-wealth.
# See https://dwarffortresswiki.org/index.php/Fortress
TITLE_LOCATIONS: list[LocationData] = [
    LocationData("Hamlet Established",      BASE_ID + 400, "Fortress"),
    LocationData("Village Established",     BASE_ID + 401, "Fortress"),
    LocationData("Town Established",        BASE_ID + 402, "Fortress"),
    LocationData("City Established",        BASE_ID + 403, "Fortress"),
    LocationData("Metropolis Established",  BASE_ID + 404, "Fortress"),
]


# ── Mining Milestones ─────────────────────────────────────────────────────────
# Depth = surface z-level minus the deepest z any mining job has reached.
# Tiles = cumulative count of completed dig/channel/staircase/ramp jobs.
# IDs match checks.lua (BASE_ID + 700 depth, +710 tiles).
MINING_LOCATIONS: list[LocationData] = [
    LocationData("Delved 10 Levels Deep",       BASE_ID + 700, "Fortress"),
    LocationData("Delved 25 Levels Deep",       BASE_ID + 701, "Fortress"),
    LocationData("Delved 50 Levels Deep",       BASE_ID + 702, "Fortress"),
    LocationData("Delved 75 Levels Deep",       BASE_ID + 703, "Fortress"),
    LocationData("Delved 100 Levels Deep",      BASE_ID + 704, "Fortress"),
    LocationData("Excavator I (100 tiles)",     BASE_ID + 710, "Fortress"),
    LocationData("Excavator II (500 tiles)",    BASE_ID + 711, "Fortress"),
    LocationData("Excavator III (2,000 tiles)", BASE_ID + 712, "Fortress"),
    LocationData("Excavator IV (5,000 tiles)",  BASE_ID + 713, "Fortress"),
    LocationData("Excavator V (10,000 tiles)",  BASE_ID + 714, "Fortress"),
    LocationData("First Cavern Breached",        BASE_ID + 720, "Fortress"),
    LocationData("Second Cavern Breached",       BASE_ID + 721, "Fortress"),
    LocationData("Third Cavern Breached",        BASE_ID + 722, "Fortress"),
    LocationData("Reached the Magma Sea",        BASE_ID + 723, "Fortress"),
    LocationData("Welcome to the Circus",          BASE_ID + 724, "Fortress"),
]

# ── Farming Milestones ────────────────────────────────────────────────────────
# Cumulative count of harvested crops (PLANT items created). IDs match checks.lua
# (BASE_ID + 730).
FARMING_LOCATIONS: list[LocationData] = [
    LocationData("Harvest 50 Crops",    BASE_ID + 730, "Fortress"),
    LocationData("Harvest 100 Crops",   BASE_ID + 731, "Fortress"),
    LocationData("Harvest 250 Crops",   BASE_ID + 732, "Fortress"),
    LocationData("Harvest 500 Crops",   BASE_ID + 733, "Fortress"),
    LocationData("Harvest 1,000 Crops", BASE_ID + 734, "Fortress"),
]

# ── Infrastructure Milestones ─────────────────────────────────────────────────
INFRASTRUCTURE_LOCATIONS: list[LocationData] = [
    LocationData("Built a Well",   BASE_ID + 740, "Fortress"),
    LocationData("Pumped Water",   BASE_ID + 741, "Fortress"),
    LocationData("Pumped Magma",   BASE_ID + 742, "Fortress"),
]

# ── Biology / Animal Milestones ───────────────────────────────────────────────
BIOLOGY_LOCATIONS: list[LocationData] = [
    # "First Eggs Hatched" (BASE_ID + 750) disabled: hatch detection unreliable on DF v50.
    # LocationData("First Eggs Hatched",  BASE_ID + 750, "Fortress"),
    LocationData("Caged a Hostile Beast",   BASE_ID + 751, "Fortress"),
]

# ── Deep / Endgame Milestones ─────────────────────────────────────────────────
ENDGAME_LOCATIONS: list[LocationData] = [
    LocationData("Mined Adamantine",  BASE_ID + 760, "Fortress"),
    LocationData("Sold an Artifact",  BASE_ID + 761, "Fortress"),
]

SKILLS: list[LocationData] = [
    LocationData("Novice Stonecutter",         BASE_ID + 800, "Fortress"),
    LocationData("Adequate Stonecutter",       BASE_ID + 801, "Fortress"),
    LocationData("Competent Stonecutter",      BASE_ID + 802, "Fortress"),
    LocationData("Skilled Stonecutter",        BASE_ID + 803, "Fortress"),
    LocationData("Proficient Stonecutter",     BASE_ID + 804, "Fortress"),
    LocationData("Talented Stonecutter",       BASE_ID + 805, "Fortress"),
    LocationData("Adept Stonecutter",          BASE_ID + 806, "Fortress"),
    LocationData("Expert Stonecutter",         BASE_ID + 807, "Fortress"),
    LocationData("Professional Stonecutter",   BASE_ID + 808, "Fortress"),
    LocationData("Accomplished Stonecutter",   BASE_ID + 809, "Fortress"),
    LocationData("Great Stonecutter",          BASE_ID + 810, "Fortress"),
    LocationData("Master Stonecutter",         BASE_ID + 811, "Fortress"),
    LocationData("High Master Stonecutter",    BASE_ID + 812, "Fortress"),
    LocationData("Grand Master Stonecutter",   BASE_ID + 813, "Fortress"),
    LocationData("Legendary Stonecutter",      BASE_ID + 814, "Fortress"),

    LocationData("Novice Engraver",             BASE_ID + 815, "Fortress"),
    LocationData("Adequate Engraver",           BASE_ID + 816, "Fortress"),
    LocationData("Competent Engraver",          BASE_ID + 817, "Fortress"),
    LocationData("Skilled Engraver",            BASE_ID + 818, "Fortress"),
    LocationData("Proficient Engraver",         BASE_ID + 819, "Fortress"),
    LocationData("Talented Engraver",           BASE_ID + 820, "Fortress"),
    LocationData("Adept Engraver",              BASE_ID + 821, "Fortress"),
    LocationData("Expert Engraver",             BASE_ID + 822, "Fortress"),
    LocationData("Professional Engraver",       BASE_ID + 823, "Fortress"),
    LocationData("Accomplished Engraver",       BASE_ID + 824, "Fortress"),
    LocationData("Great Engraver",              BASE_ID + 825, "Fortress"),
    LocationData("Master Engraver",             BASE_ID + 826, "Fortress"),
    LocationData("High Master Engraver",        BASE_ID + 827, "Fortress"),
    LocationData("Grand Master Engraver",       BASE_ID + 828, "Fortress"),
    LocationData("Legendary Engraver",          BASE_ID + 829, "Fortress"),

    LocationData("Novice Miner",                BASE_ID + 830, "Fortress"),
    LocationData("Adequate Miner",              BASE_ID + 831, "Fortress"),
    LocationData("Competent Miner",             BASE_ID + 832, "Fortress"),
    LocationData("Skilled Miner",               BASE_ID + 833, "Fortress"),
    LocationData("Proficient Miner",            BASE_ID + 834, "Fortress"),
    LocationData("Talented Miner",              BASE_ID + 835, "Fortress"),
    LocationData("Adept Miner",                 BASE_ID + 836, "Fortress"),
    LocationData("Expert Miner",                BASE_ID + 837, "Fortress"),
    LocationData("Professional Miner",          BASE_ID + 838, "Fortress"),
    LocationData("Accomplished Miner",          BASE_ID + 839, "Fortress"),
    LocationData("Great Miner",                 BASE_ID + 840, "Fortress"),
    LocationData("Master Miner",                BASE_ID + 841, "Fortress"),
    LocationData("High Master Miner",           BASE_ID + 842, "Fortress"),
    LocationData("Grand Master Miner",          BASE_ID + 843, "Fortress"),
    LocationData("Legendary Miner",             BASE_ID + 844, "Fortress"),

    LocationData("Novice Wood Cutter",          BASE_ID + 845, "Fortress"),
    LocationData("Adequate Wood Cutter",        BASE_ID + 846, "Fortress"),
    LocationData("Competent Wood Cutter",       BASE_ID + 847, "Fortress"),
    LocationData("Skilled Wood Cutter",         BASE_ID + 848, "Fortress"),
    LocationData("Proficient Wood Cutter",      BASE_ID + 849, "Fortress"),
    LocationData("Talented Wood Cutter",        BASE_ID + 850, "Fortress"),
    LocationData("Adept Wood Cutter",           BASE_ID + 851, "Fortress"),
    LocationData("Expert Wood Cutter",          BASE_ID + 852, "Fortress"),
    LocationData("Professional Wood Cutter",    BASE_ID + 853, "Fortress"),
    LocationData("Accomplished Wood Cutter",    BASE_ID + 854, "Fortress"),
    LocationData("Great Wood Cutter",           BASE_ID + 855, "Fortress"),
    LocationData("Master Wood Cutter",          BASE_ID + 856, "Fortress"),
    LocationData("High Master Wood Cutter",     BASE_ID + 857, "Fortress"),
    LocationData("Grand Master Wood Cutter",    BASE_ID + 858, "Fortress"),
    LocationData("Legendary Wood Cutter",       BASE_ID + 859, "Fortress"),

    LocationData("Novice Herbalist",            BASE_ID + 860, "Fortress"),
    LocationData("Adequate Herbalist",          BASE_ID + 861, "Fortress"),
    LocationData("Competent Herbalist",         BASE_ID + 862, "Fortress"),
    LocationData("Skilled Herbalist",           BASE_ID + 863, "Fortress"),
    LocationData("Proficient Herbalist",        BASE_ID + 864, "Fortress"),
    LocationData("Talented Herbalist",          BASE_ID + 865, "Fortress"),
    LocationData("Adept Herbalist",             BASE_ID + 866, "Fortress"),
    LocationData("Expert Herbalist",            BASE_ID + 867, "Fortress"),
    LocationData("Professional Herbalist",      BASE_ID + 868, "Fortress"),
    LocationData("Accomplished Herbalist",      BASE_ID + 869, "Fortress"),
    LocationData("Great Herbalist",             BASE_ID + 870, "Fortress"),
    LocationData("Master Herbalist",            BASE_ID + 871, "Fortress"),
    LocationData("High Master Herbalist",       BASE_ID + 872, "Fortress"),
    LocationData("Grand Master Herbalist",      BASE_ID + 873, "Fortress"),
    LocationData("Legendary Herbalist",         BASE_ID + 874, "Fortress"),

    LocationData("Novice Spinner",              BASE_ID + 875, "Fortress"),
    LocationData("Adequate Spinner",            BASE_ID + 876, "Fortress"),
    LocationData("Competent Spinner",           BASE_ID + 877, "Fortress"),
    LocationData("Skilled Spinner",             BASE_ID + 878, "Fortress"),
    LocationData("Proficient Spinner",          BASE_ID + 879, "Fortress"),
    LocationData("Talented Spinner",            BASE_ID + 880, "Fortress"),
    LocationData("Adept Spinner",               BASE_ID + 881, "Fortress"),
    LocationData("Expert Spinner",              BASE_ID + 882, "Fortress"),
    LocationData("Professional Spinner",        BASE_ID + 883, "Fortress"),
    LocationData("Accomplished Spinner",        BASE_ID + 884, "Fortress"),
    LocationData("Great Spinner",               BASE_ID + 885, "Fortress"),
    LocationData("Master Spinner",              BASE_ID + 886, "Fortress"),
    LocationData("High Master Spinner",         BASE_ID + 887, "Fortress"),
    LocationData("Grand Master Spinner",        BASE_ID + 888, "Fortress"),
    LocationData("Legendary Spinner",           BASE_ID + 889, "Fortress"),

    LocationData("Novice Fisherdwarf",          BASE_ID + 890, "Fortress"),
    LocationData("Adequate Fisherdwarf",        BASE_ID + 891, "Fortress"),
    LocationData("Competent Fisherdwarf",       BASE_ID + 892, "Fortress"),
    LocationData("Skilled Fisherdwarf",         BASE_ID + 893, "Fortress"),
    LocationData("Proficient Fisherdwarf",      BASE_ID + 894, "Fortress"),
    LocationData("Talented Fisherdwarf",        BASE_ID + 895, "Fortress"),
    LocationData("Adept Fisherdwarf",           BASE_ID + 896, "Fortress"),
    LocationData("Expert Fisherdwarf",          BASE_ID + 897, "Fortress"),
    LocationData("Professional Fisherdwarf",    BASE_ID + 898, "Fortress"),
    LocationData("Accomplished Fisherdwarf",    BASE_ID + 899, "Fortress"),
    LocationData("Great Fisherdwarf",           BASE_ID + 900, "Fortress"),
    LocationData("Master Fisherdwarf",          BASE_ID + 901, "Fortress"),
    LocationData("High Master Fisherdwarf",     BASE_ID + 902, "Fortress"),
    LocationData("Grand Master Fisherdwarf",    BASE_ID + 903, "Fortress"),
    LocationData("Legendary Fisherdwarf",       BASE_ID + 904, "Fortress"),

    LocationData("Novice Ambusher",             BASE_ID + 905, "Fortress"),
    LocationData("Adequate Ambusher",           BASE_ID + 906, "Fortress"),
    LocationData("Competent Ambusher",          BASE_ID + 907, "Fortress"),
    LocationData("Skilled Ambusher",            BASE_ID + 908, "Fortress"),
    LocationData("Proficient Ambusher",         BASE_ID + 909, "Fortress"),
    LocationData("Talented Ambusher",           BASE_ID + 910, "Fortress"),
    LocationData("Adept Ambusher",              BASE_ID + 911, "Fortress"),
    LocationData("Expert Ambusher",             BASE_ID + 912, "Fortress"),
    LocationData("Professional Ambusher",       BASE_ID + 913, "Fortress"),
    LocationData("Accomplished Ambusher",       BASE_ID + 914, "Fortress"),
    LocationData("Great Ambusher",              BASE_ID + 915, "Fortress"),
    LocationData("Master Ambusher",             BASE_ID + 916, "Fortress"),
    LocationData("High Master Ambusher",        BASE_ID + 917, "Fortress"),
    LocationData("Grand Master Ambusher",       BASE_ID + 918, "Fortress"),
    LocationData("Legendary Ambusher",          BASE_ID + 919, "Fortress"),

    LocationData("Novice Trapper",              BASE_ID + 920, "Fortress"),
    LocationData("Adequate Trapper",            BASE_ID + 921, "Fortress"),
    LocationData("Competent Trapper",           BASE_ID + 922, "Fortress"),
    LocationData("Skilled Trapper",             BASE_ID + 923, "Fortress"),
    LocationData("Proficient Trapper",          BASE_ID + 924, "Fortress"),
    LocationData("Talented Trapper",            BASE_ID + 925, "Fortress"),
    LocationData("Adept Trapper",               BASE_ID + 926, "Fortress"),
    LocationData("Expert Trapper",              BASE_ID + 927, "Fortress"),
    LocationData("Professional Trapper",        BASE_ID + 928, "Fortress"),
    LocationData("Accomplished Trapper",        BASE_ID + 929, "Fortress"),
    LocationData("Great Trapper",               BASE_ID + 930, "Fortress"),
    LocationData("Master Trapper",              BASE_ID + 931, "Fortress"),
    LocationData("High Master Trapper",         BASE_ID + 932, "Fortress"),
    LocationData("Grand Master Trapper",        BASE_ID + 933, "Fortress"),
    LocationData("Legendary Trapper",           BASE_ID + 934, "Fortress"),

    LocationData("Novice Glassmaker",           BASE_ID + 935, "Fortress"),
    LocationData("Adequate Glassmaker",         BASE_ID + 936, "Fortress"),
    LocationData("Competent Glassmaker",        BASE_ID + 937, "Fortress"),
    LocationData("Skilled Glassmaker",          BASE_ID + 938, "Fortress"),
    LocationData("Proficient Glassmaker",       BASE_ID + 939, "Fortress"),
    LocationData("Talented Glassmaker",         BASE_ID + 940, "Fortress"),
    LocationData("Adept Glassmaker",            BASE_ID + 941, "Fortress"),
    LocationData("Expert Glassmaker",           BASE_ID + 942, "Fortress"),
    LocationData("Professional Glassmaker",     BASE_ID + 943, "Fortress"),
    LocationData("Accomplished Glassmaker",     BASE_ID + 944, "Fortress"),
    LocationData("Great Glassmaker",            BASE_ID + 945, "Fortress"),
    LocationData("Master Glassmaker",           BASE_ID + 946, "Fortress"),
    LocationData("High Master Glassmaker",      BASE_ID + 947, "Fortress"),
    LocationData("Grand Master Glassmaker",     BASE_ID + 948, "Fortress"),
    LocationData("Legendary Glassmaker",        BASE_ID + 949, "Fortress"),

    LocationData("Novice Metal Crafter",        BASE_ID + 950, "Fortress"),
    LocationData("Adequate Metal Crafter",      BASE_ID + 951, "Fortress"),
    LocationData("Competent Metal Crafter",     BASE_ID + 952, "Fortress"),
    LocationData("Skilled Metal Crafter",       BASE_ID + 953, "Fortress"),
    LocationData("Proficient Metal Crafter",    BASE_ID + 954, "Fortress"),
    LocationData("Talented Metal Crafter",      BASE_ID + 955, "Fortress"),
    LocationData("Adept Metal Crafter",         BASE_ID + 956, "Fortress"),
    LocationData("Expert Metal Crafter",        BASE_ID + 957, "Fortress"),
    LocationData("Professional Metal Crafter",  BASE_ID + 958, "Fortress"),
    LocationData("Accomplished Metal Crafter",  BASE_ID + 959, "Fortress"),
    LocationData("Great Metal Crafter",         BASE_ID + 960, "Fortress"),
    LocationData("Master Metal Crafter",        BASE_ID + 961, "Fortress"),
    LocationData("High Master Metal Crafter",   BASE_ID + 962, "Fortress"),
    LocationData("Grand Master Metal Crafter",  BASE_ID + 963, "Fortress"),
    LocationData("Legendary Metal Crafter",     BASE_ID + 964, "Fortress"),

    LocationData("Novice Gem Cutter",           BASE_ID + 965, "Fortress"),
    LocationData("Adequate Gem Cutter",         BASE_ID + 966, "Fortress"),
    LocationData("Competent Gem Cutter",        BASE_ID + 967, "Fortress"),
    LocationData("Skilled Gem Cutter",          BASE_ID + 968, "Fortress"),
    LocationData("Proficient Gem Cutter",       BASE_ID + 969, "Fortress"),
    LocationData("Talented Gem Cutter",         BASE_ID + 970, "Fortress"),
    LocationData("Adept Gem Cutter",            BASE_ID + 971, "Fortress"),
    LocationData("Expert Gem Cutter",           BASE_ID + 972, "Fortress"),
    LocationData("Professional Gem Cutter",     BASE_ID + 973, "Fortress"),
    LocationData("Accomplished Gem Cutter",     BASE_ID + 974, "Fortress"),
    LocationData("Great Gem Cutter",            BASE_ID + 975, "Fortress"),
    LocationData("Master Gem Cutter",           BASE_ID + 976, "Fortress"),
    LocationData("High Master Gem Cutter",      BASE_ID + 977, "Fortress"),
    LocationData("Grand Master Gem Cutter",     BASE_ID + 978, "Fortress"),
    LocationData("Legendary Gem Cutter",        BASE_ID + 979, "Fortress"),

    LocationData("Novice Stone Crafter",        BASE_ID + 980, "Fortress"),
    LocationData("Adequate Stone Crafter",      BASE_ID + 981, "Fortress"),
    LocationData("Competent Stone Crafter",     BASE_ID + 982, "Fortress"),
    LocationData("Skilled Stone Crafter",       BASE_ID + 983, "Fortress"),
    LocationData("Proficient Stone Crafter",    BASE_ID + 984, "Fortress"),
    LocationData("Talented Stone Crafter",      BASE_ID + 985, "Fortress"),
    LocationData("Adept Stone Crafter",         BASE_ID + 986, "Fortress"),
    LocationData("Expert Stone Crafter",        BASE_ID + 987, "Fortress"),
    LocationData("Professional Stone Crafter",  BASE_ID + 988, "Fortress"),
    LocationData("Accomplished Stone Crafter",  BASE_ID + 989, "Fortress"),
    LocationData("Great Stone Crafter",         BASE_ID + 990, "Fortress"),
    LocationData("Master Stone Crafter",        BASE_ID + 991, "Fortress"),
    LocationData("High Master Stone Crafter",   BASE_ID + 992, "Fortress"),
    LocationData("Grand Master Stone Crafter",  BASE_ID + 993, "Fortress"),
    LocationData("Legendary Stone Crafter",     BASE_ID + 994, "Fortress"),

    LocationData("Novice Wood Crafter",         BASE_ID + 995, "Fortress"),
    LocationData("Adequate Wood Crafter",       BASE_ID + 996, "Fortress"),
    LocationData("Competent Wood Crafter",      BASE_ID + 997, "Fortress"),
    LocationData("Skilled Wood Crafter",        BASE_ID + 998, "Fortress"),
    LocationData("Proficient Wood Crafter",     BASE_ID + 999, "Fortress"),
    LocationData("Talented Wood Crafter",       BASE_ID + 1000, "Fortress"),
    LocationData("Adept Wood Crafter",          BASE_ID + 1001, "Fortress"),
    LocationData("Expert Wood Crafter",         BASE_ID + 1002, "Fortress"),
    LocationData("Professional Wood Crafter",   BASE_ID + 1003, "Fortress"),
    LocationData("Accomplished Wood Crafter",   BASE_ID + 1004, "Fortress"),
    LocationData("Great Wood Crafter",          BASE_ID + 1005, "Fortress"),
    LocationData("Master Wood Crafter",         BASE_ID + 1006, "Fortress"),
    LocationData("High Master Wood Crafter",    BASE_ID + 1007, "Fortress"),
    LocationData("Grand Master Wood Crafter",   BASE_ID + 1008, "Fortress"),
    LocationData("Legendary Wood Crafter",      BASE_ID + 1009, "Fortress"),

    LocationData("Novice Gem Setter",           BASE_ID + 1010, "Fortress"),
    LocationData("Adequate Gem Setter",         BASE_ID + 1011, "Fortress"),
    LocationData("Competent Gem Setter",        BASE_ID + 1012, "Fortress"),
    LocationData("Skilled Gem Setter",          BASE_ID + 1013, "Fortress"),
    LocationData("Proficient Gem Setter",       BASE_ID + 1014, "Fortress"),
    LocationData("Talented Gem Setter",         BASE_ID + 1015, "Fortress"),
    LocationData("Adept Gem Setter",            BASE_ID + 1016, "Fortress"),
    LocationData("Expert Gem Setter",           BASE_ID + 1017, "Fortress"),
    LocationData("Professional Gem Setter",     BASE_ID + 1018, "Fortress"),
    LocationData("Accomplished Gem Setter",     BASE_ID + 1019, "Fortress"),
    LocationData("Great Gem Setter",            BASE_ID + 1020, "Fortress"),
    LocationData("Master Gem Setter",           BASE_ID + 1021, "Fortress"),
    LocationData("High Master Gem Setter",      BASE_ID + 1022, "Fortress"),
    LocationData("Grand Master Gem Setter",     BASE_ID + 1023, "Fortress"),
    LocationData("Legendary Gem Setter",        BASE_ID + 1024, "Fortress"),

    LocationData("Novice Furnace Operator",     BASE_ID + 1025, "Fortress"),
    LocationData("Adequate Furnace Operator",   BASE_ID + 1026, "Fortress"),
    LocationData("Competent Furnace Operator",  BASE_ID + 1027, "Fortress"),
    LocationData("Skilled Furnace Operator",    BASE_ID + 1028, "Fortress"),
    LocationData("Proficient Furnace Operator", BASE_ID + 1029, "Fortress"),
    LocationData("Talented Furnace Operator",   BASE_ID + 1030, "Fortress"),
    LocationData("Adept Furnace Operator",      BASE_ID + 1031, "Fortress"),
    LocationData("Expert Furnace Operator",     BASE_ID + 1032, "Fortress"),
    LocationData("Professional Furnace Operator", BASE_ID + 1033, "Fortress"),
    LocationData("Accomplished Furnace Operator", BASE_ID + 1034, "Fortress"),
    LocationData("Great Furnace Operator",      BASE_ID + 1035, "Fortress"),
    LocationData("Master Furnace Operator",     BASE_ID + 1036, "Fortress"),
    LocationData("High Master Furnace Operator",  BASE_ID + 1037, "Fortress"),
    LocationData("Grand Master Furnace Operator", BASE_ID + 1038, "Fortress"),
    LocationData("Legendary Furnace Operator",  BASE_ID + 1039, "Fortress"),

    LocationData("Novice Strand Extractor",     BASE_ID + 1040, "Fortress"),
    LocationData("Adequate Strand Extractor",   BASE_ID + 1041, "Fortress"),
    LocationData("Competent Strand Extractor",  BASE_ID + 1042, "Fortress"),
    LocationData("Skilled Strand Extractor",    BASE_ID + 1043, "Fortress"),
    LocationData("Proficient Strand Extractor", BASE_ID + 1044, "Fortress"),
    LocationData("Talented Strand Extractor",   BASE_ID + 1045, "Fortress"),
    LocationData("Adept Strand Extractor",      BASE_ID + 1046, "Fortress"),
    LocationData("Expert Strand Extractor",     BASE_ID + 1047, "Fortress"),
    LocationData("Professional Strand Extractor", BASE_ID + 1048, "Fortress"),
    LocationData("Accomplished Strand Extractor", BASE_ID + 1049, "Fortress"),
    LocationData("Great Strand Extractor",      BASE_ID + 1050, "Fortress"),
    LocationData("Master Strand Extractor",     BASE_ID + 1051, "Fortress"),
    LocationData("High Master Strand Extractor",  BASE_ID + 1052, "Fortress"),
    LocationData("Grand Master Strand Extractor", BASE_ID + 1053, "Fortress"),
    LocationData("Legendary Strand Extractor",  BASE_ID + 1054, "Fortress"),

    LocationData("Novice Planter",              BASE_ID + 1055, "Fortress"),
    LocationData("Adequate Planter",            BASE_ID + 1056, "Fortress"),
    LocationData("Competent Planter",           BASE_ID + 1057, "Fortress"),
    LocationData("Skilled Planter",             BASE_ID + 1058, "Fortress"),
    LocationData("Proficient Planter",          BASE_ID + 1059, "Fortress"),
    LocationData("Talented Planter",            BASE_ID + 1060, "Fortress"),
    LocationData("Adept Planter",               BASE_ID + 1061, "Fortress"),
    LocationData("Expert Planter",              BASE_ID + 1062, "Fortress"),
    LocationData("Professional Planter",        BASE_ID + 1063, "Fortress"),
    LocationData("Accomplished Planter",        BASE_ID + 1064, "Fortress"),
    LocationData("Great Planter",               BASE_ID + 1065, "Fortress"),
    LocationData("Master Planter",              BASE_ID + 1066, "Fortress"),
    LocationData("High Master Planter",         BASE_ID + 1067, "Fortress"),
    LocationData("Grand Master Planter",        BASE_ID + 1068, "Fortress"),
    LocationData("Legendary Planter",           BASE_ID + 1069, "Fortress"),

    LocationData("Novice Animal Trainer",       BASE_ID + 1070, "Fortress"),
    LocationData("Adequate Animal Trainer",     BASE_ID + 1071, "Fortress"),
    LocationData("Competent Animal Trainer",    BASE_ID + 1072, "Fortress"),
    LocationData("Skilled Animal Trainer",      BASE_ID + 1073, "Fortress"),
    LocationData("Proficient Animal Trainer",   BASE_ID + 1074, "Fortress"),
    LocationData("Talented Animal Trainer",     BASE_ID + 1075, "Fortress"),
    LocationData("Adept Animal Trainer",        BASE_ID + 1076, "Fortress"),
    LocationData("Expert Animal Trainer",       BASE_ID + 1077, "Fortress"),
    LocationData("Professional Animal Trainer", BASE_ID + 1078, "Fortress"),
    LocationData("Accomplished Animal Trainer", BASE_ID + 1079, "Fortress"),
    LocationData("Great Animal Trainer",        BASE_ID + 1080, "Fortress"),
    LocationData("Master Animal Trainer",       BASE_ID + 1081, "Fortress"),
    LocationData("High Master Animal Trainer",  BASE_ID + 1082, "Fortress"),
    LocationData("Grand Master Animal Trainer", BASE_ID + 1083, "Fortress"),
    LocationData("Legendary Animal Trainer",    BASE_ID + 1084, "Fortress"),

    LocationData("Novice Siege Engineer",       BASE_ID + 1085, "Fortress"),
    LocationData("Adequate Siege Engineer",     BASE_ID + 1086, "Fortress"),
    LocationData("Competent Siege Engineer",    BASE_ID + 1087, "Fortress"),
    LocationData("Skilled Siege Engineer",      BASE_ID + 1088, "Fortress"),
    LocationData("Proficient Siege Engineer",   BASE_ID + 1089, "Fortress"),
    LocationData("Talented Siege Engineer",     BASE_ID + 1090, "Fortress"),
    LocationData("Adept Siege Engineer",        BASE_ID + 1091, "Fortress"),
    LocationData("Expert Siege Engineer",       BASE_ID + 1092, "Fortress"),
    LocationData("Professional Siege Engineer", BASE_ID + 1093, "Fortress"),
    LocationData("Accomplished Siege Engineer", BASE_ID + 1094, "Fortress"),
    LocationData("Great Siege Engineer",        BASE_ID + 1095, "Fortress"),
    LocationData("Master Siege Engineer",       BASE_ID + 1096, "Fortress"),
    LocationData("High Master Siege Engineer",  BASE_ID + 1097, "Fortress"),
    LocationData("Grand Master Siege Engineer", BASE_ID + 1098, "Fortress"),
    LocationData("Legendary Siege Engineer",    BASE_ID + 1099, "Fortress"),

    LocationData("Novice Weaponsmith",          BASE_ID + 1100, "Fortress"),
    LocationData("Adequate Weaponsmith",        BASE_ID + 1101, "Fortress"),
    LocationData("Competent Weaponsmith",       BASE_ID + 1102, "Fortress"),
    LocationData("Skilled Weaponsmith",         BASE_ID + 1103, "Fortress"),
    LocationData("Proficient Weaponsmith",      BASE_ID + 1104, "Fortress"),
    LocationData("Talented Weaponsmith",        BASE_ID + 1105, "Fortress"),
    LocationData("Adept Weaponsmith",           BASE_ID + 1106, "Fortress"),
    LocationData("Expert Weaponsmith",          BASE_ID + 1107, "Fortress"),
    LocationData("Professional Weaponsmith",    BASE_ID + 1108, "Fortress"),
    LocationData("Accomplished Weaponsmith",    BASE_ID + 1109, "Fortress"),
    LocationData("Great Weaponsmith",           BASE_ID + 1110, "Fortress"),
    LocationData("Master Weaponsmith",          BASE_ID + 1111, "Fortress"),
    LocationData("High Master Weaponsmith",     BASE_ID + 1112, "Fortress"),
    LocationData("Grand Master Weaponsmith",    BASE_ID + 1113, "Fortress"),
    LocationData("Legendary Weaponsmith",       BASE_ID + 1114, "Fortress"),

    LocationData("Novice Armorsmith",           BASE_ID + 1115, "Fortress"),
    LocationData("Adequate Armorsmith",         BASE_ID + 1116, "Fortress"),
    LocationData("Competent Armorsmith",        BASE_ID + 1117, "Fortress"),
    LocationData("Skilled Armorsmith",          BASE_ID + 1118, "Fortress"),
    LocationData("Proficient Armorsmith",       BASE_ID + 1119, "Fortress"),
    LocationData("Talented Armorsmith",         BASE_ID + 1120, "Fortress"),
    LocationData("Adept Armorsmith",            BASE_ID + 1121, "Fortress"),
    LocationData("Expert Armorsmith",           BASE_ID + 1122, "Fortress"),
    LocationData("Professional Armorsmith",     BASE_ID + 1123, "Fortress"),
    LocationData("Accomplished Armorsmith",     BASE_ID + 1124, "Fortress"),
    LocationData("Great Armorsmith",            BASE_ID + 1125, "Fortress"),
    LocationData("Master Armorsmith",           BASE_ID + 1126, "Fortress"),
    LocationData("High Master Armorsmith",      BASE_ID + 1127, "Fortress"),
    LocationData("Grand Master Armorsmith",     BASE_ID + 1128, "Fortress"),
    LocationData("Legendary Armorsmith",        BASE_ID + 1129, "Fortress"),
]


# Craft locations are NOT included here. They are computed deterministically by
# craftsanity.build_craft_location_table() and merged into the World's
# location_name_to_id in __init__.py (see _FULL_LOCATION_TABLE). Keeping them out
# of this module avoids a circular import (craftsanity imports from locations).
ALL_LOCATIONS: list[LocationData] = (
    WEALTH_LOCATIONS + PRODUCTION_LOCATIONS + TRADE_LOCATIONS
    + STATUS_LOCATIONS + TITLE_LOCATIONS + MINING_LOCATIONS
    + FARMING_LOCATIONS + INFRASTRUCTURE_LOCATIONS
    + BIOLOGY_LOCATIONS + ENDGAME_LOCATIONS
)
LOCATION_TABLE: dict[str, int] = {loc.name: loc.ap_id for loc in ALL_LOCATIONS}
