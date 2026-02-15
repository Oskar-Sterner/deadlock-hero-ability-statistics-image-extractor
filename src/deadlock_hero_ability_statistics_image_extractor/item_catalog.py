from dataclasses import dataclass
from typing import List, Sequence, Tuple


@dataclass(frozen=True)
class ItemTooltipTarget:
    item_id: int
    item_name: str
    hover_position_1440p: Tuple[int, int]


@dataclass(frozen=True)
class ItemTooltipTab:
    tab_id: int
    tab_name: str
    tab_click_position_1440p: Tuple[int, int]
    items: Sequence[ItemTooltipTarget]


TAB_CLICK_POSITIONS_1440P = {
    1: (786, 370),
    2: (787, 480),
    3: (786, 591),
}


_TAB1_ITEMS = [
    (1342610602, "Close Quarters", (960, 363)),
    (1548066885, "Extended Magazine", (1076, 363)),
    (2010028405, "Headshot Booster", (1188, 363)),
    (3077079169, "High-Velocity Rounds", (1300, 363)),
    (1009965641, "Monster Rounds", (1415, 363)),
    (668299740, "Rapid Rounds", (960, 530)),
    (3862866912, "Restorative Shot", (1076, 530)),
    (381961617, "Active Reload", (1594, 192)),
    (98582110, "Backstabber", (1707, 192)),
    (3403085434, "Fleetfoot", (1821, 192)),
    (2407033488, "Intensifying Magazine", (1930, 192)),
    (3977876567, "Kinetic Dash", (2047, 192)),
    (3331811235, "Long Range", (2160, 192)),
    (26002154, "Melee Charge", (1594, 358)),
    (395867183, "Mystic Shot", (1707, 358)),
    (2064029594, "Opening Rounds", (1821, 358)),
    (1763073141, "Recharging Rush", (1930, 358)),
    (393974127, "Slowing Bullets", (2047, 358)),
    (1144549437, "Spirit Shredder Bullets", (2160, 358)),
    (3647584222, "Split Shot", (1594, 526)),
    (4104549924, "Swift Striker", (1707, 526)),
    (2356412290, "Titanic Magazine", (1821, 526)),
    (1770441818, "Weakening Headshot", (1930, 526)),
    (1932939246, "Alchemical Fire", (962, 826)),
    (3294954488, "Ballistic Enchantment", (1076, 826)),
    (1414319208, "Berserker", (1188, 826)),
    (989206714, "Blood Tribute", (1302, 826)),
    (2739107182, "Burst Fire", (1414, 826)),
    (709540378, "Cultist Sacrifice", (1528, 826)),
    (2463960640, "Escalating Resilience", (962, 998)),
    (690458959, "Express Shot", (1076, 998)),
    (4053935515, "Headhunter", (1188, 998)),
    (2108215830, "Heroic Aura", (1302, 998)),
    (2678489038, "Hollow Point", (1414, 998)),
    (2481177645, "Hunter's Aura", (1528, 998)),
    (2095565695, "Point Blank", (962, 1170)),
    (2152872419, "Sharpshooter", (1076, 1170)),
    (4075861416, "Spirit Rend", (1188, 1170)),
    (811521119, "Tesla Bullets", (1302, 1170)),
    (3696726732, "Toxic Bullets", (1414, 1170)),
    (3791587546, "Weighted Shots", (1528, 1170)),
    (673001892, "Armor Piercing Rounds", (1704, 822)),
    (710436191, "Capacitor", (1819, 822)),
    (3884003354, "Crippling Headshot", (1934, 822)),
    (800008313, "Crushing Fists", (2049, 822)),
    (339443430, "Frenzy", (2164, 822)),
    (365620721, "Glass Cannon", (1704, 995)),
    (1396247347, "Lucky Shot", (1819, 995)),
    (2480592370, "Ricochet", (1934, 995)),
    (1798666702, "Shadow Weave", (2049, 995)),
    (1113837674, "Silencer", (2164, 995)),
    (2221211450, "Spellslinger", (1704, 1168)),
    (2226497419, "Spiritual Overflow", (1819, 1168)),
]


_TAB2_ITEMS_RAW = [
    (3633614685, "Extra Health", None),
    (2829638276, "Extra Regen", None),
    (4139877411, "Extra Stamina", None),
    (1710079648, "Healing Rite", None),
    (1437614329, "Melee Lifesteal", None),
    (4204808176, "Rebuttal", None),
    (3399065363, "Sprint Boots", None),
    (1235347618, "Battle Vest", None),
    (499683006, "Bullet Lifesteal", None),
    (1047818222, "Debuff Reducer", None),
    (3970837787, "Enchanter's Emblem", None),
    (2447176615, "Enduring Speed", None),
    (857669956, "Guardian Ward", None),
    (2603935618, "Healbane", None),
    (2566692615, "Healing Booster", None),
    (1644605047, "Reactive Barrier", None),
    (2059712766, "Restorative Locket", None),
    (3361075077, "Return Fire", None),
    (876563814, "Spirit Lifesteal", None),
    (112198670, "Spirit Shielding", None),
    (805079544, "Weapon Shielding", None),
    (3140772621, "Bullet Resilience", (962, 826)),
    (1414025773, "Counterspell", (1076, 826)),
    (3731635960, "Dispel Magic", (1188, 826)),
    (3585132399, "Fortitude", (1302, 826)),
    (1409190604, "Fury Trance", (1414, 826)),
    (2956256701, "Healing Nova", (962, 998)),
    (1252627263, "Lifestrike", (1076, 998)),
    (600033864, "Majestic Leap", (1188, 998)),
    (1378931225, "Metal Skin", (1302, 998)),
    (1804594021, "Rescue Beam", (1414, 998)),
    (2163598980, "Spirit Resilience", (962, 1172)),
    (334300056, "Stamina Mastery", (1076, 1172)),
    (3074274290, "Trophy Collector", (1188, 1172)),
    (865958998, "Veil Walker", (1302, 1172)),
    (3270001687, "Warp Stone", (1414, 1172)),
    (3361811174, "Cheat Death", (1598, 824)),
    (2407781327, "Colossus", (1712, 824)),
    (1662311306, "Divine Barrier", (1824, 824)),
    (2820116164, "Diviner's Kevlar", (1938, 824)),
    (1427630806, "Healing Tempo", (2050, 824)),
    (1797283378, "Infuser", (2164, 824)),
    (2037039379, "Inhibitor", (1598, 998)),
    (1250307611, "Juggernaut", (1712, 998)),
    (865846625, "Leech", (1824, 998)),
    (1371725689, "Phantom Strike", (1938, 998)),
    (3491236900, "Plated Armor", (2050, 998)),
    (1282141666, "Siphon Bullets", (2164, 998)),
    (1955841979, "Spellbreaker", (1598, 1170)),
    (3357231760, "Unstoppable", (1712, 1170)),
    (1055679805, "Vampiric Burst", (1824, 1170)),
    (3028234315, "Witchmail", (1938, 1170)),
]


_TAB3_ITEMS_RAW = [
    (3776945997, "Extra Charge", "tab1"),
    (968099481, "Extra Spirit", "tab1"),
    (1998374645, "Mystic Burst", "tab1"),
    (754480263, "Mystic Expansion", "tab1"),
    (1439347412, "Mystic Regeneration", "tab1"),
    (2922054143, "Rusted Barrel", "tab1"),
    (465043967, "Spirit Strike", "tab1"),
    (1150006784, "Arcane Surge", "tab1"),
    (2971868509, "Bullet Resist Shredder", "tab1"),
    (1976391348, "Cold Front", "tab1"),
    (380806748, "Compress Cooldown", "tab1"),
    (2951612397, "Duration Extender", "tab1"),
    (7409189, "Improved Spirit", "tab1"),
    (1102081447, "Mystic Slow", "tab1"),
    (2081037738, "Mystic Vulnerability", "tab1"),
    (84321454, "Quicksilver Reload", "tab1"),
    (1813726886, "Slowing Hex", "tab1"),
    (1219329868, "Spirit Sap", "tab1"),
    (1925087134, "Suppressor", "tab1"),
    (3144988365, "Decay", (962, 826)),
    (2061878743, "Disarming Hex", (1076, 826)),
    (1193964439, "Greater Expansion", (1188, 826)),
    (1254091416, "Knockdown", (1302, 826)),
    (2947183272, "Radiant Regeneration", (1414, 826)),
    (787198704, "Rapid Recharge", (962, 998)),
    (619484391, "Silence Wave", (1076, 998)),
    (3190916303, "Spirit Snatch", (1188, 998)),
    (3261353684, "Superior Cooldown", (1302, 998)),
    (2717651715, "Superior Duration", (1414, 998)),
    (1292979587, "Surge of Power", (962, 1170)),
    (2121044373, "Tankbuster", (1076, 1170)),
    (395944548, "Torment Pulse", (1188, 1170)),
    (3812615317, "Arctic Blast", (1598, 824)),
    (2519598785, "Boundless Spirit", (1712, 824)),
    (2617435668, "Cursed Relic", (1824, 824)),
    (630839635, "Echo Shard", (1938, 824)),
    (3005970438, "Escalating Exposure", (2050, 824)),
    (2533252781, "Ethereal Shift", (2164, 824)),
    (2142980412, "Focus Lens", (1598, 998)),
    (493591231, "Lightning Scroll", (1712, 998)),
    (2800629741, "Magic Carpet", (1824, 998)),
    (3919289022, "Mercurial Magnum", (1938, 998)),
    (3577481646, "Mystic Reverb", (2050, 998)),
    (677738769, "Refresher", (2164, 998)),
    (2417568017, "Scourge", (1598, 1170)),
    (343572757, "Spirit Burn", (1712, 1170)),
    (915014646, "Transcendent Cooldown", (1824, 1170)),
    (1152158042, "Vortex Web", (1938, 1170)),
]


def _build_tab2_items(tab1_items: Sequence[ItemTooltipTarget]) -> List[ItemTooltipTarget]:
    items: List[ItemTooltipTarget] = []
    for index, (item_id, item_name, coord) in enumerate(_TAB2_ITEMS_RAW):
        hover_position = coord if coord is not None else tab1_items[index].hover_position_1440p
        items.append(
            ItemTooltipTarget(
                item_id=item_id,
                item_name=item_name,
                hover_position_1440p=hover_position,
            )
        )
    return items


def _build_tab3_items(
    tab1_items: Sequence[ItemTooltipTarget], tab2_items: Sequence[ItemTooltipTarget]
) -> List[ItemTooltipTarget]:
    items: List[ItemTooltipTarget] = []
    for index, (item_id, item_name, source) in enumerate(_TAB3_ITEMS_RAW):
        if isinstance(source, tuple):
            hover_position = source
        elif source == "tab1":
            hover_position = tab1_items[index].hover_position_1440p
        elif source == "tab2":
            hover_position = tab2_items[index].hover_position_1440p
        else:
            raise ValueError(f"Unknown tab3 coordinate source: {source}")

        items.append(
            ItemTooltipTarget(
                item_id=item_id,
                item_name=item_name,
                hover_position_1440p=hover_position,
            )
        )
    return items


def build_item_tooltip_tabs() -> List[ItemTooltipTab]:
    tab1_items = [
        ItemTooltipTarget(item_id=item_id, item_name=item_name, hover_position_1440p=hover_position)
        for item_id, item_name, hover_position in _TAB1_ITEMS
    ]
    tab2_items = _build_tab2_items(tab1_items)
    tab3_items = _build_tab3_items(tab1_items, tab2_items)

    return [
        ItemTooltipTab(
            tab_id=1,
            tab_name="Weapon",
            tab_click_position_1440p=TAB_CLICK_POSITIONS_1440P[1],
            items=tab1_items,
        ),
        ItemTooltipTab(
            tab_id=2,
            tab_name="Vitality",
            tab_click_position_1440p=TAB_CLICK_POSITIONS_1440P[2],
            items=tab2_items,
        ),
        ItemTooltipTab(
            tab_id=3,
            tab_name="Spirit",
            tab_click_position_1440p=TAB_CLICK_POSITIONS_1440P[3],
            items=tab3_items,
        ),
    ]
