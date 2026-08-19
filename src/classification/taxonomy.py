"""
taxonomy.py -- Controlled taxonomy vocabulary for T5 Classification.

Provides the canonical Dept > Class > Fine hierarchy that the classifier
MUST constrain its output to.  The LLM is never allowed to invent taxonomy
values outside this list.

Structure
---------
TAXONOMY is a list of dicts:
    {
        "dept":      str,   # top-level department
        "class_name": str,  # mid-level class
        "fine":      str,   # fine category
        "classpath": str,   # "Dept>Class>Fine"  (pre-computed for speed)
        "keywords":  list[str],  # hint words for semantic matching
    }

Seeded from confirmed ground-truth rows (Frigidaire + Whirlpool dishwashers)
plus a broad industrial/hardware/appliance coverage set that matches the
kinds of products seen in the 200-row input dataset.

Extend this list as new categories surface during evaluation.
"""

from __future__ import annotations
from typing import Optional


# ---------------------------------------------------------------------------
# Taxonomy entries
# ---------------------------------------------------------------------------

_RAW: list[tuple[str, str, str, list[str]]] = [
    # (Dept, Class, Fine, keywords)

    # ── Appliances ────────────────────────────────────────────────────────────
    ("Appliances", "Kitchen Appliances", "Dishwashers",
     ["dishwasher", "dish washer", "pdsh", "dishwash"]),
    ("Appliances", "Kitchen Appliances", "Refrigerators",
     ["refrigerator", "fridge", "freezer", "french door", "side by side"]),
    ("Appliances", "Kitchen Appliances", "Ranges & Ovens",
     ["range", "oven", "stove", "cooktop", "cook top"]),
    ("Appliances", "Kitchen Appliances", "Microwaves",
     ["microwave", "microwave oven"]),
    ("Appliances", "Kitchen Appliances", "Dishwasher Accessories",
     ["dishwasher rack", "dishwasher basket", "dishwasher part"]),
    ("Appliances", "Laundry Appliances", "Washers",
     ["washer", "washing machine", "front load", "top load"]),
    ("Appliances", "Laundry Appliances", "Dryers",
     ["dryer", "clothes dryer", "gas dryer", "electric dryer"]),
    ("Appliances", "Laundry Appliances", "Washer Dryer Combos",
     ["washer dryer combo", "laundry center", "laundry combo"]),
    ("Appliances", "HVAC", "Air Conditioners",
     ["air conditioner", "ac unit", "window ac", "portable ac", "split system"]),
    ("Appliances", "HVAC", "Furnaces",
     ["furnace", "gas furnace", "electric furnace", "forced air"]),
    ("Appliances", "HVAC", "Heat Pumps",
     ["heat pump", "mini split", "ductless"]),
    ("Appliances", "Water Heaters", "Tank Water Heaters",
     ["water heater", "hot water heater", "tank water heater"]),
    ("Appliances", "Water Heaters", "Tankless Water Heaters",
     ["tankless", "on demand water heater", "instantaneous"]),

    # ── Plumbing ──────────────────────────────────────────────────────────────
    ("Plumbing", "Pipe Fittings", "Couplings",
     ["coupling", "cplg", "pipe coupling", "union"]),
    ("Plumbing", "Pipe Fittings", "Elbows",
     ["elbow", "elb", "ell", "90 degree", "45 degree", "street elbow"]),
    ("Plumbing", "Pipe Fittings", "Tees",
     ["tee", "pipe tee", "reducing tee"]),
    ("Plumbing", "Pipe Fittings", "Reducers",
     ["reducer", "red", "reducing", "bushing", "bush"]),
    ("Plumbing", "Pipe Fittings", "Nipples",
     ["nipple", "nip", "pipe nipple", "hex nipple", "close nipple"]),
    ("Plumbing", "Pipe Fittings", "Flanges",
     ["flange", "flg", "pipe flange", "blind flange"]),
    ("Plumbing", "Pipe Fittings", "Caps & Plugs",
     ["cap", "plug", "pipe cap", "pipe plug", "end cap"]),
    ("Plumbing", "Pipe Fittings", "Adapters",
     ["adapter", "adpt", "pipe adapter", "male adapter", "female adapter"]),
    ("Plumbing", "Valves", "Ball Valves",
     ["ball valve", "ball vlv", "full port ball", "two piece ball"]),
    ("Plumbing", "Valves", "Gate Valves",
     ["gate valve", "gate vlv"]),
    ("Plumbing", "Valves", "Check Valves",
     ["check valve", "chk", "swing check", "spring check"]),
    ("Plumbing", "Valves", "Globe Valves",
     ["globe valve", "glb", "globe vlv"]),
    ("Plumbing", "Valves", "Needle Valves",
     ["needle valve", "ndl", "needle vlv"]),
    ("Plumbing", "Valves", "Butterfly Valves",
     ["butterfly valve", "butterfly vlv"]),
    ("Plumbing", "Pipe", "Steel Pipe",
     ["steel pipe", "black pipe", "schedule 40", "schedule 80", "sch 40", "sch 80"]),
    ("Plumbing", "Pipe", "Copper Pipe",
     ["copper pipe", "copper tube", "copper tubing", "type l", "type k", "type m"]),
    ("Plumbing", "Pipe", "PVC Pipe",
     ["pvc pipe", "pvc tube", "cpvc pipe"]),
    ("Plumbing", "Faucets", "Kitchen Faucets",
     ["kitchen faucet", "kitchen tap", "pull down faucet", "pull out faucet"]),
    ("Plumbing", "Faucets", "Bathroom Faucets",
     ["bathroom faucet", "lavatory faucet", "bath faucet", "sink faucet"]),
    ("Plumbing", "Faucets", "Shower Faucets",
     ["shower faucet", "shower valve", "shower trim", "tub shower"]),
    ("Plumbing", "Faucets", "Utility Faucets",
     ["utility faucet", "laundry faucet", "hose bib", "sillcock"]),
    ("Plumbing", "Drains & Traps", "P-Traps",
     ["p-trap", "p trap", "drain trap", "bottle trap"]),
    ("Plumbing", "Drains & Traps", "Floor Drains",
     ["floor drain", "area drain", "shower drain"]),

    # ── Electrical ────────────────────────────────────────────────────────────
    ("Electrical", "Wiring Devices", "Outlets & Receptacles",
     ["outlet", "receptacle", "duplex outlet", "gfci outlet", "usb outlet"]),
    ("Electrical", "Wiring Devices", "Switches",
     ["switch", "light switch", "toggle switch", "dimmer switch", "rocker switch"]),
    ("Electrical", "Wiring Devices", "Circuit Breakers",
     ["circuit breaker", "breaker", "gfci breaker", "arc fault"]),
    ("Electrical", "Lighting", "LED Bulbs",
     ["led bulb", "led lamp", "led light bulb", "a19", "par30", "par38"]),
    ("Electrical", "Lighting", "Fluorescent Lighting",
     ["fluorescent", "t8", "t5", "t12", "fluorescent tube", "cfl"]),
    ("Electrical", "Lighting", "Fixtures",
     ["light fixture", "luminaire", "ceiling fixture", "wall fixture"]),
    ("Electrical", "Wire & Cable", "Building Wire",
     ["building wire", "thhn", "romex", "nm cable", "wire"]),
    ("Electrical", "Wire & Cable", "Conduit",
     ["conduit", "emt conduit", "rigid conduit", "pvc conduit"]),
    ("Electrical", "Motors", "Electric Motors",
     ["electric motor", "motor", "ac motor", "dc motor", "fractional hp"]),

    # ── Tools & Hardware ──────────────────────────────────────────────────────
    ("Tools & Hardware", "Hand Tools", "Wrenches",
     ["wrench", "adjustable wrench", "pipe wrench", "combination wrench", "torque wrench"]),
    ("Tools & Hardware", "Hand Tools", "Pliers",
     ["pliers", "needle nose", "channel lock", "locking pliers", "lineman"]),
    ("Tools & Hardware", "Hand Tools", "Screwdrivers",
     ["screwdriver", "flathead", "phillips", "torx", "nut driver"]),
    ("Tools & Hardware", "Hand Tools", "Hammers",
     ["hammer", "mallet", "sledge", "ball peen"]),
    ("Tools & Hardware", "Power Tools", "Drills",
     ["drill", "drill driver", "hammer drill", "rotary hammer", "cordless drill"]),
    ("Tools & Hardware", "Power Tools", "Saws",
     ["saw", "circular saw", "reciprocating saw", "jigsaw", "miter saw", "table saw"]),
    ("Tools & Hardware", "Fasteners", "Bolts",
     ["bolt", "hex bolt", "carriage bolt", "anchor bolt", "stud bolt"]),
    ("Tools & Hardware", "Fasteners", "Nuts",
     ["nut", "hex nut", "lock nut", "coupling nut", "wing nut"]),
    ("Tools & Hardware", "Fasteners", "Screws",
     ["screw", "machine screw", "wood screw", "sheet metal screw", "self tapping"]),
    ("Tools & Hardware", "Fasteners", "Washers",
     ["washer", "flat washer", "lock washer", "fender washer", "split washer"]),

    # ── Safety ────────────────────────────────────────────────────────────────
    ("Safety", "Personal Protective Equipment", "Gloves",
     ["glove", "work glove", "safety glove", "cut resistant", "nitrile glove"]),
    ("Safety", "Personal Protective Equipment", "Safety Glasses",
     ["safety glasses", "safety goggles", "eye protection", "face shield"]),
    ("Safety", "Personal Protective Equipment", "Hard Hats",
     ["hard hat", "safety helmet", "bump cap"]),
    ("Safety", "Personal Protective Equipment", "Respirators",
     ["respirator", "dust mask", "n95", "half mask", "full face respirator"]),
    ("Safety", "Safety Signage", "Warning Signs",
     ["warning sign", "caution sign", "danger sign", "safety sign"]),

    # ── HVAC Supplies ─────────────────────────────────────────────────────────
    ("HVAC", "Filters", "Air Filters",
     ["air filter", "furnace filter", "hvac filter", "merv", "hepa filter"]),
    ("HVAC", "Ductwork", "Duct Fittings",
     ["duct fitting", "duct elbow", "duct tee", "duct reducer", "duct collar"]),
    ("HVAC", "Thermostats", "Programmable Thermostats",
     ["thermostat", "programmable thermostat", "smart thermostat", "wifi thermostat"]),
    ("HVAC", "Refrigerants", "Refrigerant",
     ["refrigerant", "r-22", "r-410a", "r-134a", "freon"]),
]


# ---------------------------------------------------------------------------
# Build the taxonomy list
# ---------------------------------------------------------------------------

TAXONOMY: list[dict] = []
for _dept, _cls, _fine, _kw in _RAW:
    TAXONOMY.append({
        "dept": _dept,
        "class_name": _cls,
        "fine": _fine,
        "classpath": f"{_dept}>{_cls}>{_fine}",
        "keywords": [k.lower() for k in _kw],
    })

# Pre-built set of all valid classpaths for O(1) validation
VALID_CLASSPATHS: set[str] = {entry["classpath"] for entry in TAXONOMY}


def get_entry_by_classpath(classpath: str) -> Optional[dict]:
    """Return the taxonomy entry for a given classpath, or None."""
    for entry in TAXONOMY:
        if entry["classpath"] == classpath:
            return entry
    return None
