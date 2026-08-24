"""Every place, route and doodle on panel 2.5, with its real coordinates.

Panel 2 of maps.html holds the same content at invented positions. This is the
same list with the true latitude and longitude of each item, so the build
script can put it where it belongs. Nothing is dropped and nothing is moved: a
place too tight to draw at one scale gets its doodle on the sheet one rung up
the ladder, at its own true position there.

Fields on a POI:
    key     internal name
    name    the hover text, word for word as on panel 2
    at      (lat, lon)
    ic      glyph id from panel 2's defs, or None for a plain chart stop
    label   ('text', dx, dy, anchor, cls) drawn always; or ('hover', ...) which
            only appears on hover, exactly as on panel 2
    lead    optional (dx, dy) leader line from the glyph out to the label
"""

# ------------------------------------------------------------------ the sheets
# A ladder of scales rather than one sheet. The arithmetic decides the rungs: a
# doodle needs about 26 units of clearance, so a sheet can only carry places
# whose spacing beats 26 / (units per km). One screen of the whole Salish Sea
# gives 4.3 units/km, which is 6 km per doodle, and the villages are 60 m across.
# So the whole water is sheet 1, and the places it cannot hold get a plan of
# their own at a scale where they can breathe.
#
# Each pane is defined by its centre and the scale it must reach, and the frame
# follows from the box it is drawn in. Defining it the other way round is how a
# pane ends up 20% short of the scale its own contents need.
SHEETS = [
    dict(key="overview", kind="map", doodles=False, poi_names="towns", eps=1.2,
         title="SALISH SEA", short="the whole Salish Sea",
         sub="· the index sheet: every frame that follows ·",
         frame=(-124.78, 47.20, -120.52, 49.12),
         blurb=[
             "One Mercator window, one scale. Every",
             "coast, island, distance and course here",
             "is the real one. Panel 2 of the chart",
             "above is the same water drawn by hand,",
             "where the crest comes half as far and",
             "the parks lie along an invented shore.",
             "",
             "This sheet carries no drawings. At 3.3",
             "units per km a doodle covers 8 km of",
             "water, so each one lives on a numbered",
             "sheet that follows, at its own scale.",
             "",
             "Rainier and Olympia sit below the south",
             "edge, on sheets 6 and 5: one frame that",
             "reached both the Pacific and Rainier is",
             "more water than a screen holds.",
             "",
             "Two tones. Full colour is land I have",
             "set foot on; the lighter tone is land I",
             "have only passed: Lopez, Shaw, Camano,",
             "Blake, Lummi, the Gulf Islands and the",
             "Kitsap. The edge between them is a",
             "shore everywhere but one place, and the",
             "one circle on these sheets is Poulsbo.",
         ]),
    dict(key="sanjuans", kind="map",
         title="THE SAN JUANS", short="The San Juans &amp; Haro Strait",
         sub="· Anacortes, Lopez, Shaw, Orcas, San Juan ·",
         frame=(-123.50, 48.32, -122.58, 48.82),
         blurb=[
             "Five times the index sheet, and the",
             "only one where the three ferry legs out",
             "of Anacortes are far enough apart to",
             "read as three separate courses.",
             "",
             "San Juan Island and Orcas are mine, and",
             "so is Fidalgo: Anacortes is on it and",
             "the drive to the boat crosses it. Lopez",
             "and Shaw are the lighter tone. The",
             "ferry called there and I stayed aboard.",
             "",
             "The boundary runs down the middle of",
             "Haro Strait and out through Boundary",
             "Pass, as the 1846 treaty puts it. The",
             "drawings stop at it; the geography and",
             "the names do not.",
         ]),
    dict(key="north", kind="map",
         title="WHIDBEY, SKAGIT &amp; MOUNT BAKER",
         short="Whidbey, Skagit &amp; Baker",
         sub="· Deception Pass to the Skagit flats ·",
         # The frame carries the whole San Juan group and a corner of Victoria as
         # context, and those islands have their own sheet, so only this sheet's
         # own places are drawn here. The rest keep their dots and their names.
         only=("deception", "ebeys", "mukilteo", "clinton", "funko", "tulips",
               "anacortes", "port_townsend", "edmonds"),
         frame=(-123.48, 47.88, -121.72, 48.95),
         blurb=[
             "Whidbey is the long island the ferry",
             "from Mukilteo lands on, and the only",
             "way off its north end is the bridge at",
             "Deception Pass.",
             "",
             "The frame is set west so the island",
             "sits in the middle of it: the water it",
             "stands in is the subject as much as",
             "the island. East of the Skagit flats",
             "the sheet climbs to Mt. Baker, 10,781",
             "ft and 60 km behind the tulip fields.",
             "Diablo Lake and the pass beyond it are",
             "on the mountains sheet.",
             "",
             "Baker and Shuksan are half transparent.",
             "I have watched both all my life from",
             "the water and stood on neither.",
         ]),
    dict(key="olympic", kind="map",
         title="THE OLYMPIC PENINSULA &amp; HOOD CANAL",
         short="Olympic Pen. &amp; Hood Canal",
         sub="· the rain forest, the ridge and the oysters ·",
         frame=(-124.78, 46.95, -122.60, 48.30),
         blurb=[
             "The wettest corner of the country and",
             "the emptiest part of the frame. Three",
             "rain forests on the west side, a",
             "mile-high ridge in the middle, and a",
             "68 km fjord down the east.",
             "",
             "Hood Canal is a glacial trough, not a",
             "canal: 180 m deep and never more than",
             "3 km wide, which is why its oyster",
             "tideflats are drawn where they are.",
             "",
             "Forks and the werewolf beaches at La",
             "Push are out on the Pacific side, three",
             "hours from anywhere.",
             "",
             "Mt. Olympus is half transparent, and so",
             "is the state capitol at Olympia. The",
             "index sheet was cropped short of both",
             "until this sheet existed to hold them.",
         ]),
    dict(key="seattle", kind="map",
         title="SEATTLE &amp; THE EASTSIDE",
         short="Seattle &amp; the Eastside", glyph_scale=1.35,
         sub="· Elliott Bay to Lake Sammamish ·",
         frame=(-122.548, 47.495, -122.108, 47.755),
         blurb=[
             "Nine times the index sheet. The parks,",
             "the beaches, the locks, the sauna and",
             "the four south-end ferry slips, each on",
             "its own coordinates.",
             "",
             "This is the shape of the place the",
             "index sheet has to compress: Elliott",
             "Bay, the ship canal, Lake Union, Lake",
             "Washington and Mercer Island are all",
             "inside 33 km of longitude, which up",
             "there is 116 units of paper.",
             "",
             "Drawings sit on the side of the shore",
             "the thing is really on. The sailboat is",
             "in Meydenbauer Bay, the swim raft is",
             "off Madison Park, and Alki's Statue of",
             "Liberty stands on the beach.",
         ]),
    dict(key="sound", kind="map",
         title="BAINBRIDGE, VASHON &amp; THE SOUTH SOUND",
         short="Bainbridge, Vashon &amp; the south Sound",
         sub="· the island chain off Seattle's own shore ·",
         frame=(-123.02, 47.15, -122.35, 47.90),
         blurb=[
             "The chain you cross to get anywhere",
             "west: Kingston and Edmonds at the top,",
             "Bainbridge in the middle, Vashon and",
             "Maury at the bottom, and four ferry",
             "routes threading between them.",
             "",
             "Bainbridge, Vashon and Maury are in",
             "full colour. Vashon and Maury only",
             "earned it today. Blake Island, a state",
             "park you can reach only by boat, is",
             "still the lighter tone.",
             "",
             "The Kitsap is the lighter tone, with",
             "one dark circle on it: Poulsbo is the",
             "only town on that 60 km peninsula I",
             "have walked, and 4 km round it is",
             "honestly as far as I got.",
             "",
             "Three drawings are the day: Nashi",
             "Orchards pressing perry off its own",
             "Asian pears, and 10 km east on Maury,",
             "Oscar the Bird King, Dambo's troll in a",
             "grove crowned with birdhouses, five",
             "minutes up the trail from the Point",
             "Robinson light. Troll and light are two",
             "units apart here, so one rides out on a",
             "leader.",
             "",
             "A tall sheet: the chain runs 83 km",
             "north to south and the water is never",
             "wide, so the apron carries the rest.",
         ]),
    # Canada on one sheet. It used to be two: Vancouver and the Sea to Sky at
    # 4.8 units/km, the Rockies at 2.7. Two sheets is what a reader of the
    # trip does not have: I flew into YVR, drove Howe Sound, then drove east, and
    # the distance between those two halves is the fact the pair of sheets hid.
    # One frame states it: Victoria to the north end of Jasper, Vancouver Island
    # to Calgary, at one scale. The price is the scale, 1.5 units/km, and at that
    # scale a doodle covers 20 km, so Vancouver, YVR and UBC ride out to clear
    # paper on leaders. That is the honest trade and the leaders say so.
    dict(key="vancouver", kind="map", usa_only=False, glyph_scale=1.1,
         # The frame is set by arithmetic, not by taste: the map can be 1090 units
         # wide at most once the apron is paid for, so a 900-unit-high sheet can
         # hold 1.211 of Mercator aspect. 10.05 degrees of longitude therefore
         # buys exactly 5.3 of latitude, which is Victoria to north of Jasper.
         # Reaching south to Swartz Bay for the crossing catches the whole of the
         # San Juans; only these places are drawn here, and the rest keep their
         # dots and belong to the sheets they were cut for.
         only=("vancouver", "yvr", "ubc", "whistler", "tsawwassen", "swartz_bay",
               "victoria", "sidney", "calgary", "banff", "lake_louise", "yoho",
               "jasper"),
         poi_names="own",
         no_locator=True,
         title="CANADA: VANCOUVER, THE SEA TO SKY &amp; THE ROCKIES",
         short="Canada: Vancouver to Calgary",
         sub="· one frame from salt water to the continental divide ·",
         frame=(-123.62, 48.20, -113.70, 53.40),
         blurb=[
             "The only sheet that draws anything in",
             "Canada. Everywhere else the drawings",
             "stop at the treaty line and only the",
             "geography and the names cross it; here",
             "the sheet is Canada, so they do not.",
             "",
             "One frame, ten degrees of longitude:",
             "700 km of ground, salt water at the",
             "left edge and the continental divide",
             "two thirds of the way across. This was",
             "two sheets and should not have been.",
             "The 500 km from Howe Sound to Lake",
             "Louise is the thing the trip was about,",
             "and a page break is the one way a map",
             "cannot say it.",
             "",
             "I flew into YVR and took BC Ferries",
             "from Tsawwassen to Swartz Bay, which",
             "is the crossing drawn at the bottom",
             "left and the reason Victoria and",
             "Vancouver Island are in full colour on",
             "every sheet. The Sea to Sky runs from",
             "Horseshoe Bay up the sound to",
             "Whistler; then the road turns east and",
             "does not reach salt water again.",
             "",
             "Three of the four contiguous mountain",
             "parks are drawn: Banff, Yoho and",
             "Jasper, with Kootenay between them.",
             "The Icefields Parkway runs the length",
             "of it. The lakes are the reason to come",
             "and their colour is rock flour ground",
             "fine by the glaciers above them:",
             "Louise, Moraine, Peyto, Emerald,",
             "Maligne.",
         ]),
    dict(key="cascades", kind="map",
         title="THE CASCADES: RAINIER TO DIABLO LAKE",
         short="the Cascades, Rainier to Diablo",
         sub="· the crest, the four passes and the volcanoes ·",
         frame=(-122.15, 46.70, -120.52, 48.95),
         blurb=[
             "East of the lakes the ground goes up.",
             "Three passes carry the roads over the",
             "crest, and the crest itself is the line",
             "the weather stops at: rain forest on",
             "one side, sagebrush on the other.",
             "",
             "Snoqualmie Falls is 82 m, higher than",
             "Niagara, and 45 minutes from downtown.",
             "Mt. Si stands over it.",
             "",
             "Rainier is 14,411 ft and closes the",
             "south of the frame. It is the one the",
             "hand-drawn chart never had room for,",
             "and it is half transparent: from",
             "Seattle it is scenery, not a place I",
             "have been.",
         ]),
]

# The order the pager shows them in. The three island sheets sit together, north
# to south, because that is the way the water is travelled; then the city, then
# the peninsula, then the mountains.
_SHEET_ORDER = ["overview", "sanjuans", "north", "sound", "seattle", "olympic",
                "cascades", "vancouver"]
SHEETS.sort(key=lambda s: _SHEET_ORDER.index(s["key"]))

# Labels the index sheet leaves out. At 3.3 units per km a swim-beach lake and a
# 6 km inlet are noise, and they were the whole of that sheet's crowding: the
# sheet that draws the place names the water it sits on.
INDEX_OMIT_LABELS = {
    "Auburn", "Kent", "Renton", "Issaquah", "Maury I.", "Blake I.", "Sucia I.",
    "Lummi I.", "L. Wash.", "L. Sammamish", "Rattlesnake L.", "L. Cushman",
    "L. Crescent", "Colvos Passage", "East Passage", "Case Inlet", "Carr Inlet",
    "Budd Inlet", "Dungeness Spit", "Saanich", "Admiralty Inlet", "Hood Canal",
    "Fidalgo Island",   # Anacortes is named on the index; its island is not
    "Quinault Rain Forest",
    # The town names these already: Friday Harbor is on San Juan Island,
    # Eastsound is on Orcas, and Mercer Island has the Seattle sheet.
    "San Juan I.", "Orcas I.", "Vashon Island", "Mercer I.",
}

# ------------------------------------------------------------- the index sheet
# Which names the index sheet prints. Its job is to say where each of the six
# drawing sheets is cut from, so it names settlements and leaves the bookshop,
# the cafe and the museum to the sheet that can hold them. The label class
# cannot decide this: "The Whale Museum" and "Port Townsend" are both rt-label.
INDEX_NAMES = {
    "seattle", "anacortes", "friday_harbor", "eastsound", "port_angeles",
    "victoria", "port_townsend", "poulsbo", "mukilteo", "clinton", "funko",
    "capitol", "chateau", "bainbridge", "tulips",
}

# --------------------------------------------------------- where I have been
# Two tones, and only two: full colour for land I have set foot on, one lighter
# tone for land I have only sailed past. The unit the tone applies to is the
# island, whole, so the edge between the two is always a coastline and never a
# box, a circle or a polygon drawn through the middle of somewhere. An island is
# mine if it contains one of these points; anything else is not. Defaulting the
# unknown island to "not visited" is the honest direction to be wrong in.
MAINLAND_VISITED = [
    # The mainland, with enough points that every frame catches its own piece.
    (47.6062, -122.3321), (47.6130, -122.1900), (47.2529, -122.4443),
    (47.9787, -122.2043), (48.7519, -122.4787), (48.4201, -122.3341),
    (48.1100, -123.4300), (47.0357, -122.9053), (47.2151, -123.1007),
    (46.9754, -123.8157), (47.8021, -123.7110), (47.4877, -121.7233),
    (47.3900, -121.4100), (47.7500, -121.0900), (48.7300, -121.2200),
    (48.5250, -120.6500), (46.8523, -121.7603), (48.1118, -121.1132),
]

# Islands I have set foot on. Kept apart from the mainland only because the two
# lists are maintained differently: the mainland needs enough points that every
# frame catches its own piece of it, an island needs one.
ISLANDS_VISITED = [
    (48.5500, -123.1000),   # San Juan Island
    (48.6786, -122.8322),   # Orcas
    (48.2201, -122.6857),   # Whidbey, at Coupeville
    (47.6300, -122.5400),   # Bainbridge
    (47.4400, -122.4600),   # Vashon
    (47.5050, -122.4550),   # Vashon again, at the north tip: the Seattle sheet
                            # cuts the island and only sees this end of it
    (47.3830, -122.4300),   # Maury
    (48.2932, -122.6432),   # Whidbey again, at Oak Harbor
    (48.5347, -123.1489),   # San Juan Island again, at the county park
    (48.6100, -122.9400),   # Orcas again, at the landing
    (47.5860, -122.2320),   # Mercer Island: a hole in Lake Washington, not the sea
    (48.4900, -122.6300),   # Fidalgo: I drive to Anacortes to catch the ferry
    (48.5023, -122.6790),   # Fidalgo again, at the terminal
]

VISITED_LAND = MAINLAND_VISITED + ISLANDS_VISITED

# Ground I have not walked, drawn as polygons. Two jobs, and only one of them is
# paint. Every one of them fades the name of a town I have not been to. Exactly
# one of them, the Kitsap, is also painted, because that landmass is the one place
# on these sheets where an honest tone cannot be a landmass: I have been to
# Poulsbo on it and nowhere else. See PARTLY_VISITED below.
#
# The Kitsap ring is drawn along the water it stands in, vertex by vertex, so the
# only place its edge crosses dry land is the 6.5 km isthmus at the head of Hood
# Canal, which is where the peninsula genuinely ends. That is the difference
# between this and the wash boxes that came before it: a box edge fell wherever
# arithmetic put it, usually across the middle of an island.
KITSAP = dict(name="Kitsap Peninsula", ring=[
    # The cut, and the only edge of this ring that is meant to be seen: the
    # isthmus between the head of Hood Canal at Belfair and the head of North Bay
    # on Case Inlet, 4 km of dry ground and the one place the peninsula is
    # attached to anything. Everything below it is Shelton and Olympia, which are
    # the mainland and stay one tone.
    (47.440, -122.850),
    # West: down the east arm of Hood Canal to the Great Bend, then north up the
    # canal to Admiralty Inlet. Every vertex was read off the coastline in the
    # cache rather than guessed, which is why they are not on a round number: an
    # earlier pass put this line 15 km east of the water and washed the Olympic
    # side of the canal by mistake.
    (47.420, -122.884), (47.400, -122.930), (47.390, -122.950), (47.380, -122.985),
    (47.370, -123.005), (47.365, -123.012), (47.358, -123.022), (47.355, -123.045),
    (47.360, -123.062), (47.370, -123.090), (47.375, -123.120), (47.380, -123.130),
    (47.400, -123.125), (47.420, -123.115), (47.440, -123.100), (47.450, -123.092),
    (47.500, -123.044), (47.550, -123.016), (47.600, -122.956), (47.650, -122.874),
    (47.670, -122.800), (47.685, -122.770), (47.700, -122.762), (47.750, -122.740),
    (47.800, -122.714), (47.850, -122.650), (47.900, -122.615), (47.925, -122.625),
    (47.945, -122.645), (47.960, -122.600),
    # North and east: across Admiralty Inlet and down the middle of Puget Sound.
    # Bainbridge, Blake and Vashon fall inside this and are redrawn afterwards,
    # because an island answers for its own colour and no polygon should have to
    # dodge one.
    (47.970, -122.500), (47.850, -122.470), (47.700, -122.470), (47.550, -122.470),
    (47.460, -122.500), (47.420, -122.535), (47.380, -122.535), (47.340, -122.550),
    (47.300, -122.545), (47.270, -122.550), (47.240, -122.580), (47.210, -122.595),
    # South: round the foot of the Key Peninsula and back up Case Inlet.
    (47.190, -122.640), (47.180, -122.700), (47.165, -122.760), (47.175, -122.800),
    (47.190, -122.800), (47.220, -122.850), (47.260, -122.860), (47.300, -122.830),
    (47.340, -122.800), (47.380, -122.823), (47.405, -122.824),
])

UNVISITED_REGIONS = [
    KITSAP,
    # Vancouver Island: the island itself is mine, because Victoria is on it and
    # the ferry from Tsawwassen lands there. What this polygon is for is the names
    # on it that are not, and the small islands off its east coast.
    dict(name="Vancouver Island", ring=[
        (48.20, -123.15), (48.45, -123.30), (48.70, -123.55), (49.00, -123.75),
        (49.30, -124.05), (49.70, -124.60), (50.10, -125.20), (50.50, -125.70),
        (50.50, -128.00), (48.20, -128.00)]),
    dict(name="the south Sound", ring=[
        # Shelton and Olympia inside, Tacoma on the far side of the water and
        # outside. Names only: the land here is the mainland and stays one tone.
        (47.44, -122.51), (47.36, -122.56), (47.30, -122.72), (47.24, -122.92),
        (47.30, -123.14), (47.22, -123.30), (46.88, -123.30), (46.88, -122.46),
        (47.18, -122.46)]),
]

# The exception to one tone per landmass, and the only one. A peninsula 60 km long
# that I have touched at exactly one town cannot honestly be full colour, and
# painting all of it back is a lie in the other direction, so the Kitsap is drawn
# in the lighter tone with Poulsbo standing on it in full colour: the radius is
# how far I actually got, 4 km round the town and the head of Liberty Bay.
#
# The circle is the one edge on these sheets that is not a shore, and it is meant
# to be read as a mark rather than as geography, so the legend carries it. It is
# clipped to the land, so it never spills into the bay, and it is painted before
# the islands are, so it can never reach one.
PARTLY_VISITED = [dict(region=KITSAP,
                       spots=[("Poulsbo", 47.7362, -122.6465, 4.0)])]


def in_ring_latlon(lat: float, lon: float, ring) -> bool:
    """Point in a (lat, lon) ring. The rings in this file are written that way
    round, because they are read off a map and not out of a projection."""
    c = False
    for (la1, lo1), (la2, lo2) in zip(ring, ring[1:] + ring[:1]):
        if (la1 > lat) != (la2 > lat) and lon < lo1 + (lat-la1)/(la2-la1)*(lo2-lo1):
            c = not c
    return c


def in_unvisited_region(lat: float, lon: float) -> bool:
    return any(in_ring_latlon(lat, lon, r["ring"]) for r in UNVISITED_REGIONS)


# Settlements I have not been to. Faded, the same as the land: on the chart the
# name is still orientation, it is just not mine.
UNVISITED_LABELS = {
    "Gig Harbor", "Bremerton", "Mount Vernon", "Shelton", "Aberdeen",
    "Grays Harbor", "Sequim", "Kent", "Auburn", "Renton",
    "Quinault Rain Forest",
}

# The islands I have not set foot on used to be listed here, with a box round
# each group of them and a radius round the one spot on a peninsula that was
# mine. All of it existed to correct a default that had to be "visited", because
# the rule ran on frame-clipped rings and could not tell the mainland from an
# island. The rule now runs on each island's own closed coastline, where the
# default can be the honest one, so the exceptions are gone: an island is mine if
# a point above is inside it, and that is the whole of it. See island_is_mine in
# scripts/build_salish_geo_panel.py.

# The two floating bridges. They are the only way onto Mercer Island and they are
# the longest floating bridges in the world, so a chart of this water that leaves
# them out is wrong about how the place works.
BRIDGES = [
    ("I-90", [(47.5905, -122.2870), (47.5925, -122.2530)]),
    ("SR-520", [(47.6400, -122.2740), (47.6395, -122.2270)]),
]

# ----------------------------------------------------------------- ferry docks
# Terminal positions are the slips themselves, so the ferry tracks start on the
# right side of the water.
DOCKS = {
    "anacortes": (48.5023, -122.6790),
    "friday_harbor": (48.5352, -123.0139),
    "orcas_landing": (48.5975, -122.9440),
    "shaw": (48.5844, -122.9290),
    "lopez": (48.5711, -122.8837),
    "mukilteo": (47.9483, -122.3040),
    "clinton": (47.9750, -122.3505),
    "edmonds": (47.8114, -122.3855),
    "kingston": (47.7967, -122.4960),
    "bainbridge": (47.6229, -122.5108),
    "colman": (47.6026, -122.3387),
    "fauntleroy": (47.5232, -122.3937),
    "vashon_hts": (47.5133, -122.4640),
    "southworth": (47.5127, -122.4952),
    "sidney": (48.6437, -123.3944),
    # BC Ferries, Tsawwassen to Swartz Bay: how I got to Victoria.
    "tsawwassen": (49.0060, -123.1300),
    "swartz_bay": (48.6890, -123.4100),
}

# ------------------------------------------------------------------------ POIs
POIS = [
    # ---- Route I: the San Juan Islands ----
    dict(key="anacortes", name="Anacortes Ferry Terminal (WSF)",
         at=DOCKS["anacortes"], ic="anchor",
         label=("text", 4, -30, "middle", "rt-label big", ["Anacortes"]),
         sub=("text", 4, -17, "middle", "rt-sub", ["Ferry Terminal (WSF)"]),
         lead=(2, -24)),
    dict(key="friday_harbor", name="Friday Harbor Ferry Terminal (WSF)",
         at=DOCKS["friday_harbor"], ic="anchor",
         label=("text", -14, -14, "end", "rt-label", ["Friday Harbor"]),),
    dict(key="fh_dock", name="Friday Harbor Ferry Terminal (WSF)",
         at=DOCKS["friday_harbor"], ic="anchor", scale=0.85,
         label=("text", 13, -2, "start", "rt-sub", ["Ferry Terminal (WSF)"])),
    dict(key="downriggers", name="Downriggers", at=(48.5348, -123.0134),
         ic=None, label=("text", 6, 16, "start", "rt-label", ["Downriggers"])),
    dict(key="riptide", name="Riptide Cafe", at=(48.5346, -123.0147),
         ic=None, label=("text", -2, -8, "middle", "rt-label", ["Riptide Cafe"])),
    dict(key="whale_museum", name="The Whale Museum", at=(48.5364, -123.0155),
         ic="whale", scale=0.85,
         label=("text", 0, -16, "middle", "rt-label", ["The Whale Museum"])),
    dict(key="sj_county_park", name="San Juan County Park · camping",
         at=(48.5347, -123.1489), ic="tent", scale=0.85,
         label=("hover", 0, 24, "middle", None, ["San Juan County Park"])),
    dict(key="orcas_landing", name="Orcas Island Ferry Terminal (WSF)",
         at=DOCKS["orcas_landing"], ic="anchor", scale=0.9,
         label=("hover", -12, 12, "end", None, ["Orcas Island Ferry Terminal"])),
    dict(key="orcas_pottery", name="Orcas Island Pottery", at=(48.6656, -122.9803),
         ic="pot", scale=0.8,
         label=("hover", -12, 4, "end", None, ["Orcas Island Pottery"])),
    dict(key="eastsound", name="Eastsound", at=(48.6968, -122.9064), ic=None,
         stop_r=4,
         label=("text", 0, -20, "middle", "rt-label", ["Eastsound"]),
         lead=(0, -14)),
    dict(key="darvills", name="Darvill's Book Store", at=(48.6963, -122.9070),
         ic=None,
         label=("hover", 8, 14, "start", None, ["Darvill's Book Store"])),
    dict(key="madrona_bar", name="The Madrona Bar &amp; Grill", at=(48.6967, -122.9077),
         ic=None,
         label=("hover", 6, -8, "start", None, ["The Madrona Bar &amp; Grill"])),
    dict(key="island_market", name="Island Market", at=(48.6948, -122.9042),
         ic=None,
         label=("hover", 8, 4, "start", None, ["Island Market"])),
    dict(key="eastsound_stop", name="Eastsound", at=(48.6968, -122.9064),
         ic=None, stop_r=4,
         label=("text", 0, -14, "middle", "rt-label", ["Eastsound"]),
         sub=("text", 0, -2, "middle", "rt-sub", ["Darvill's · Madrona · Market"])),
    dict(key="mt_constitution", name="Mount Constitution: lookout tower",
         at=(48.6786, -122.8322), ic="tower", scale=0.8,
         label=("hover", 14, 4, "start", None, ["Mount Constitution"])),
    dict(key="cascade_trail", name="Cascade Falls Trail", at=(48.6560, -122.8395),
         ic=None,
         label=("hover", 10, -6, "start", None, ["Cascade Falls Trail"])),
    dict(key="cascade_falls", name="Cascade Falls", at=(48.6543, -122.8425),
         ic="falls", scale=0.8,
         label=("hover", 10, 8, "start", None, ["Cascade Falls"])),
    dict(key="rustic_falls", name="Rustic Falls", at=(48.6612, -122.8562),
         ic="falls", scale=0.8,
         label=("hover", -10, 4, "end", None, ["Rustic Falls"])),

    # ---- Route III: Whidbey ----
    dict(key="mukilteo", name="Mukilteo Ferry Terminal (WSF)", at=DOCKS["mukilteo"],
         ic="anchor", scale=0.9,
         label=("text", 13, 6, "start", "rt-label", ["Mukilteo"]),),
    dict(key="clinton", name="Clinton Ferry Terminal (WSF)", at=DOCKS["clinton"],
         ic="anchor", scale=0.9,
         label=("text", -13, -6, "end", "rt-label", ["Clinton"]),),
    dict(key="edmonds", name="Edmonds: the Kingston ferry (WSF)", at=DOCKS["edmonds"],
         ic="anchor", scale=0.75,
         label=("hover", 12, 4, "start", None, ["Edmonds"])),
    dict(key="funko", name="Funko HQ, downtown Everett", at=(47.9787, -122.2043),
         ic="funko",
         label=("text", 0, 26, "middle", "rt-label", ["Everett"]),
         sub=("text", 0, 39, "middle", "rt-sub", ["Funko HQ"])),
    dict(key="ebeys", name="Ebey's Landing: bluff trail", at=(48.1948, -122.7085),
         ic="bluff",
         label=("text", -18, -14, "end", "rt-label", ["Ebey's Landing"])),
    dict(key="deception", name="Deception Pass", at=(48.4062, -122.6440),
         ic=None,
         label=("hover", 12, 4, "start", None, ["Deception Pass"])),
    dict(key="tulips", name="Skagit Valley Tulip Festival: Mount Vernon / La Conner (April)",
         at=(48.4256, -122.3822), ic="tulips",
         label=("text", 0, -22, "middle", "rt-label", ["Skagit Valley"]),
         sub=("text", 0, 43, "middle", "rt-sub", ["Tulip Festival"])),

    # ---- Route II: Bainbridge & Poulsbo ----
    dict(key="bainbridge", name="Bainbridge Island Ferry Terminal (WSF) · Eagle Harbor",
         at=DOCKS["bainbridge"], ic="anchor",
         label=("text", -15, -18, "end", "rt-label", ["Bainbridge Island"]),),
    dict(key="poulsbo", name="Poulsbo: Little Norway", at=(47.7359, -122.6465),
         ic="viking",
         label=("text", 0, 28, "middle", "rt-label", ["Poulsbo"])),

    # ---- Route IV: Port Townsend, Victoria, the peninsula ----
    dict(key="port_townsend", name="Port Townsend: Victorian seaport",
         at=(48.1170, -122.7604), ic="light",
         label=("text", 16, 6, "start", "rt-label", ["Port Townsend"])),
    dict(key="victoria", name="Victoria, BC", at=(48.4197, -123.3701),
         ic="parl",
         label=("text", 0, 30, "middle", "rt-label", ["Victoria"])),
    dict(key="port_angeles", name="Port Angeles: gateway to Olympic NP",
         at=(48.1181, -123.4307), ic="pier",
         label=("text", 0, 26, "middle", "rt-label", ["Port Angeles"])),
    dict(key="olympic_np", name="Olympic National Park", at=(47.7000, -123.5600),
         ic="mtns",
         label=("text", 0, 30, "middle", "rt-sub", ["Olympic"]),
         sub=("text", 0, 42, "middle", "rt-sub", ["National Park"])),
    dict(key="forks", name="Forks: the logging town in the rain shadow of nothing",
         at=(47.9503, -124.3855), ic="pine", scale=1.1,
         label=("text", 0, -22, "middle", "rt-label", ["Forks"])),
    dict(key="kalaloch", name="Kalaloch Beach: the drift logs and the Tree of Life",
         at=(47.6120, -124.3745), ic="driftwood", scale=2.0,
         label=("text", 0, -22, "middle", "rt-label", ["Kalaloch Beach"])),
    dict(key="hurricane", name="Hurricane Ridge: mile-high viewpoint, Olympic NP",
         at=(47.9694, -123.4986), ic="ridge",
         label=("text", 0, -14, "middle", "rt-sub", ["Hurricane Ridge"])),
    dict(key="oysters", name="Hood Canal oysters: the tideflats between Lilliwaup and the Great Bend",
         at=(47.4200, -123.1100), ic="oyster",
         label=("hover", 12, 4, "start", None, ["Hood Canal oysters"])),
    dict(key="capitol", name="Washington State Capitol, Olympia", at=(47.0357, -122.9053),
         ic="capitol", scale=0.92, unvisited=True,
         label=("text", -18, 10, "end", "rt-label", ["Olympia"])),

    # ---- Seattle: the places the Seattle sheet draws ----
    dict(key="seattle", name="Seattle", at=(47.6062, -122.3321), ic="siren",
         extra=[("squirrel", 26, 14, 0.55)],
         label=("text", 0, 40, "middle", "rt-label big", ["Seattle"])),
    dict(key="space_needle", name="Space Needle", at=(47.6205, -122.3493),
         ic="needle", scale=0.72, off=(10, 10),
         label=("hover", 12, 4, "start", None, ["Space Needle"])),
    dict(key="cpa", name="Climate Pledge Arena: Seattle Kraken", at=(47.6221, -122.3540),
         ic="arena", scale=0.72, off=(-14, -10),
         label=("hover", -18, -10, "end", None, ["Climate Pledge Arena"])),
    dict(key="uw", name="University of Washington: the Quad cherry blossoms",
         at=(47.6565, -122.3080), ic="cherry", scale=0.55,
         label=("hover", 12, 4, "start", None, ["UW cherry blossoms"])),
    dict(key="lake_union", name="Lake Union: the sailboats and the seaplanes",
         at=(47.6395, -122.3330), ic="santana", scale=0.8,
         label=("hover", 12, 4, "start", None, ["Lake Union"])),
    dict(key="gasworks", name="Gas Works Park: the cracking towers on Lake Union's north shore",
         at=(47.6456, -122.3344), ic="gasworks",
         label=("hover", -6, -16, "end", None, ["Gas Works Park"])),
    dict(key="locks", name="Hiram M. Chittenden (Ballard) Locks: fish ladder &amp; the step up from the sea",
         at=(47.6656, -122.3974), ic="locks",
         label=("hover", 0, -13, "middle", None, ["Ballard Locks"])),
    dict(key="golden_gardens", name="Golden Gardens Park: barrel sauna &amp; cold plunge in the Sound",
         at=(47.6893, -122.4028), ic="sauna", scale=0.75,
         extra=[("driftwood", 13, 5, 0.5)],
         label=("hover", 20, 4, "start", None, ["Golden Gardens Park"])),
    dict(key="discovery", name="Discovery Park: West Point Lighthouse",
         at=(47.6621, -122.4359), ic="light", scale=0.8,
         label=("hover", -14, 4, "end", None, ["Discovery Park"])),
    dict(key="alki", name="Alki Beach · the Statue of Liberty replica &amp; the driftwood shore",
         at=(47.5860, -122.4110), ic="liberty", scale=0.92,
         extra=[("driftwood", 12, 5, 0.55)],
         label=("hover", -11, 8, "end", None, ["Alki Beach"])),
    dict(key="madison_park", name="Madison Park Beach: Lake Washington swim beach &amp; swim raft",
         at=(47.6363, -122.2765), ic="swimraft", scale=0.82,
         label=("hover", -11, -8, "end", None, ["Madison Park Beach"])),
    dict(key="madrona_park", name="Madrona Park: Lake Washington beach, bathhouse &amp; lakeside benches",
         at=(47.6110, -122.2851), ic="bench", scale=0.78,
         label=("hover", -13, 10, "end", None, ["Madrona Park"])),
    dict(key="waverly", name="Waverly Beach Park, Kirkland: Lake Washington swim beach &amp; pier",
         at=(47.6873, -122.2091), ic="pier", scale=0.75,
         label=("hover", -13, -8, "end", None, ["Waverly Beach Park"])),
    dict(key="meydenbauer", name="Meydenbauer Bay Park: Bellevue's swim beach, marina cove &amp; sailing",
         at=(47.6135, -122.2075), ic="santana", scale=-0.72,
         label=("hover", -12, 10, "end", None, ["Meydenbauer Bay Park"])),
    dict(key="bdp", name="Bellevue Downtown Park: crescent waterfall &amp; the circular canal promenade",
         at=(47.6122, -122.2021), ic="bdp", scale=0.9,
         label=("hover", 15, 4, "start", None, ["Bellevue Downtown Park"])),
    dict(key="chateau", name="Chateau Ste. Michelle Winery · Woodinville",
         at=(47.7106, -122.1613), ic="winery",
         label=("text", 0, -28, "middle", "rt-label", ["Woodinville"]),
         sub=("text", 0, -16, "middle", "rt-sub", ["Chateau Ste. Michelle"])),
    dict(key="elliott_bay_park", name="Elliott Bay Park: Smith Cove waterfront path",
         at=(47.6280, -122.3790), ic=None,
         label=("hover", 10, 4, "start", None, ["Elliott Bay Park"])),
    dict(key="waterfront_park", name="Waterfront Park: Pier 58", at=(47.6062, -122.3416),
         ic=None, off=(-15, -7),
         label=("hover", -10, -4, "end", None, ["Waterfront Park"])),
    dict(key="lumen", name="Lumen Field: Seattle Seahawks · FIFA World Cup 26",
         at=(47.5952, -122.3316), ic="stadium", scale=0.8, off=(8, 15),
         label=("hover", 19, 4, "start", None, ["Lumen Field"])),
    dict(key="colman", name="Seattle Ferry Terminal: Colman Dock (WSF)", at=DOCKS["colman"],
         ic="anchor",
         label=("text", -13, 16, "end", "rt-sub", ["Colman Dock (WSF)"])),
    dict(key="fauntleroy", name="Fauntleroy Ferry Terminal (WSF) · West Seattle",
         at=DOCKS["fauntleroy"], ic="anchor", quiet_on=("overview",),
         label=("text", -14, 4, "end", "rt-label", ["Fauntleroy"])),
    dict(key="vashon_hts", name="Vashon Heights Ferry Terminal (WSF)", at=DOCKS["vashon_hts"],
         ic="anchor", quiet_on=("overview",),
         label=("text", 0, 22, "middle", "rt-sub", ["Vashon Hts."])),
    dict(key="southworth", name="Southworth Ferry Terminal (WSF) · Kitsap Peninsula",
         at=DOCKS["southworth"], ic="anchor", quiet_on=("overview",),
         label=("text", -14, -8, "end", "rt-label", ["Southworth"])),

    # ---- Vashon and Maury: the day the ferry stopped being the whole of it ----
    # Nashi is in the middle of Vashon and the other two are 220 m apart on the
    # far east tip of Maury, which is 10 km away and the reason this sheet is
    # worth its scale: at 10.8 units/km the troll and the light are 2.4 units
    # apart, so one of them is nudged onto its own leader.
    dict(key="nashi", name="Nashi Orchards Tasting Room: perry and cider off the "
                          "Asian pears grown on the place",
         at=(47.4535, -122.4703), ic="pear", scale=0.9,
         label=("text", 0, -20, "middle", "rt-sub", ["Nashi Orchards"])),
    dict(key="oscar", name="Oscar, the Bird King: Thomas Dambo's troll in the grove "
                          "above the beach, crowned with birdhouses",
         at=(47.3893, -122.3772), ic="troll", scale=0.85,
         label=("text", 0, 26, "middle", "rt-sub", ["Oscar, the Bird King"])),
    dict(key="pt_robinson", name="Point Robinson Lighthouse: the light on the east "
                                "tip of Maury, in the middle of East Passage",
         at=(47.3881, -122.3744), ic="light", scale=0.95,
         label=("text", 13, 4, "start", "rt-sub", ["Pt. Robinson Light"])),

    # ---- Canada: the Vancouver sheet ----
    dict(key="vancouver", name="Vancouver, BC: YVR and the seawall", at=(49.2827, -123.1207),
         ic="city", scale=0.9,
         label=("text", 0, -14, "middle", "rt-label big", ["Vancouver"])),
    dict(key="yvr", name="YVR: Vancouver International", at=(49.1967, -123.1815),
         ic="plane", scale=0.8,
         label=("text", 0, 20, "middle", "rt-sub", ["YVR"])),
    dict(key="ubc", name="UBC: the Point Grey campus and the plaza fountain",
         at=(49.2606, -123.2460), ic="fountain", scale=0.5,
         label=("text", -12, 4, "end", "rt-sub", ["UBC"])),
    dict(key="whistler", name="Whistler: the Sea to Sky highway ends here",
         at=(50.1163, -122.9574), ic="mtns", scale=0.8,
         label=("text", 0, 26, "middle", "rt-label", ["Whistler"])),
    dict(key="tsawwassen", name="Tsawwassen Ferry Terminal (BC Ferries)",
         at=DOCKS["tsawwassen"], ic="anchor", scale=0.9,
         label=("text", 0, 18, "middle", "rt-sub", ["Tsawwassen"])),
    dict(key="swartz_bay", name="Swartz Bay Ferry Terminal (BC Ferries)",
         at=DOCKS["swartz_bay"], ic="anchor", scale=0.9,
         label=("text", -12, 4, "end", "rt-sub", ["Swartz Bay"])),

    # ---- the Rockies: Banff, Yoho, Jasper, Calgary ----
    dict(key="calgary", name="Calgary, Alberta", at=(51.0447, -114.0719),
         ic="city", scale=1.0,
         label=("text", 0, -14, "middle", "rt-label big", ["Calgary"])),
    dict(key="banff", name="Banff National Park: the Bow valley and Lake Minnewanka",
         at=(51.1784, -115.5708), ic="mtns", scale=0.9,
         sub=("text", 0, 0, "middle", "rt-sub", ["National Park"]),
         label=("text", 0, 26, "middle", "rt-label", ["Banff"])),
    dict(key="lake_louise", name="Lake Louise and Moraine Lake",
         at=(51.4254, -116.1773), ic=None,
         label=("text", 14, 4, "start", "rt-sub", ["Lake Louise"])),
    dict(key="yoho", name="Yoho National Park: Takakkaw Falls and Emerald Lake",
         at=(51.4000, -116.5000), ic="falls", scale=0.9,
         label=("text", -14, 4, "end", "rt-label", ["Yoho"])),
    dict(key="jasper", name="Jasper National Park: the Icefields Parkway and Maligne Lake",
         at=(52.8737, -118.0814), ic="mtns", scale=0.9,
         sub=("text", 0, 0, "middle", "rt-sub", ["National Park"]),
         label=("text", 0, 26, "middle", "rt-label", ["Jasper"])),

    # ---- the Cascades ----
    dict(key="snoqualmie_falls", name="Snoqualmie Falls", at=(47.5417, -121.8377),
         ic="falls",
         label=("text", 0, 28, "middle", "rt-sub", ["Snoqualmie Falls"])),
    dict(key="north_cascades", name="North Cascades National Park", at=(48.7300, -121.2200),
         ic="mtns",
         label=("text", 0, 30, "middle", "rt-sub", ["North Cascades NP"])),
    dict(key="diablo", name="Diablo Lake: its milky turquoise comes from glacial rock flour",
         at=(48.7150, -121.1050), ic="diablo",
         label=("text", 0, 22, "middle", "rt-sub", ["Diablo L."])),
]

# ------------------------------------------------------- unclimbed summits etc.
SUMMITS = [
    dict(key="baker", at=(48.7767, -121.8144), glyph="baker",
         label=("Mt. Baker · 10,781 ft", 0, 40, "middle")),
    dict(key="shuksan", at=(48.8314, -121.6019), glyph="shuksan",
         label=(None, 0, 0, "middle")),
    dict(key="glacier_peak", at=(48.1118, -121.1132), glyph="glacier_peak",
         label=("Glacier Peak · 10,541 ft", -4, 40, "end")),
    dict(key="olympus", at=(47.7986, -123.7062), glyph="mtns", scale=1.25,
         label=("Mt. Olympus · 7,980 ft", 0, 26, "middle")),
    dict(key="si", at=(47.4877, -121.7233), glyph="mtns", scale=1.05,
         label=("Mt. Si · 4,167 ft", 18, 32, "end")),
    dict(key="rainier", at=(46.8523, -121.7603), glyph="rainier", visited=True,
         label=("Mt. Rainier · 14,411 ft", 0, -34, "middle")),
]

# ------------------------------------------------------------- ferry & road legs
# Ferry tracks: real courses, drawn through the water they run in.
FERRY_LEGS = [
    # Through Thatcher Pass and up San Juan Channel. A straight line from
    # Anacortes to Friday Harbor crosses Decatur, Lopez and Shaw: 111 of 273
    # sample points were on dry land.
    [(48.5023, -122.6790), (48.4975, -122.7250), (48.4840, -122.7930),
     (48.4960, -122.8560), (48.5230, -122.9080), (48.5330, -122.9640),
     (48.5352, -123.0139)],
    # Friday Harbor north up San Juan Channel, then east into Harney Channel.
    [(48.5352, -123.0139), (48.5470, -122.9960), (48.5720, -122.9840),
     (48.5900, -122.9620), (48.5975, -122.9440)],
    # Orcas back out through Harney Channel and Thatcher Pass.
    [(48.5975, -122.9440), (48.5830, -122.9150), (48.5450, -122.8760),
     (48.5060, -122.8300), (48.4840, -122.7930), (48.4975, -122.7250),
     (48.5023, -122.6790)],
    [(47.9483, -122.3040), (47.9600, -122.3300), (47.9750, -122.3505)],
    [(47.8114, -122.3855), (47.8040, -122.4400), (47.7967, -122.4960)],
    [(47.6026, -122.3387), (47.6080, -122.4000), (47.6180, -122.4600),
     (47.6229, -122.5108)],
    # Fauntleroy to Vashon Heights. The run continues to Southworth in real life
    # and I have never been on that leg, so the chart does not draw it.
    [DOCKS["fauntleroy"], DOCKS["vashon_hts"]],
    # BC Ferries. Not Washington State Ferries, but it is the crossing that put
    # me on Vancouver Island, so the chart owes it a line.
    [DOCKS["tsawwassen"], DOCKS["swartz_bay"]],

]


# Drive legs are routed through the real highway network: each is a list of
# checkpoints, and the build script walks the OSM graph between them along the
# refs given, so the line on the chart is the road.
DRIVE_LEGS = [
    dict(key="i5_sr20", refs=("I 5", "SR 20", "SR 526", "SR 525", "SR 536"),
         via=[(47.5990, -122.3300), (47.9560, -122.2020), (48.4180, -122.3350),
              (48.4560, -122.5220), (48.5000, -122.6120), (48.4950, -122.6350),
              (48.5060, -122.6620), DOCKS["anacortes"]],
         label=("I-5 · SR-20", 48.20, -122.28, -74)),
    dict(key="mukilteo_spur", refs=("SR 525", "SR 526", "I 5"),
         via=[(47.9560, -122.2020), (47.9530, -122.2900), DOCKS["mukilteo"]]),
    dict(key="whidbey", refs=("SR 525", "SR 20"),
         via=[DOCKS["clinton"], (48.0180, -122.3760), (48.1750, -122.6600),
              (48.2340, -122.6870), (48.3230, -122.6350), (48.4062, -122.6440)],
         label=("SR-525 · SR-20", 48.10, -122.55, -60)),
    dict(key="deception_north", refs=("SR 20",),
         via=[(48.4062, -122.6440), (48.4290, -122.6480), (48.4520, -122.6350),
              (48.4700, -122.6180), (48.4900, -122.6100)]),
    dict(key="bainbridge_poulsbo", refs=("SR 305",),
         via=[DOCKS["bainbridge"], (47.6800, -122.5450), (47.7359, -122.6465)]),
    dict(key="port_townsend", refs=("SR 305", "SR 3", "SR 104", "SR 19", "SR 20"),
         via=[DOCKS["bainbridge"], (47.7359, -122.6465), (47.8000, -122.6400),
              (47.8580, -122.6250), (48.0000, -122.7700), (48.1050, -122.7700),
              (48.1170, -122.7604)],
         label=("SR-104 · Hood Canal Bridge", 47.8600, -122.6300, -20),
         label2=("SR-19 · SR-20", 48.0400, -122.7850, -78)),
    dict(key="sr20_east", refs=("SR 20",),
         via=[(48.4560, -122.3350), (48.5300, -121.7400), (48.6800, -121.2600),
              (48.7150, -121.1200)],
         label=("SR-20 · North Cascades Highway", 48.62, -121.55, -8)),
]

# Island drives, on roads the highway layer does not carry (they are not
# numbered routes): the west side of San Juan Island, and Orcas.
ISLAND_DRIVES = [
    [DOCKS["friday_harbor"], (48.5390, -123.0290), (48.5480, -123.0700),
     (48.5420, -123.1200), (48.5380, -123.1430), (48.5347, -123.1489)],
    [DOCKS["orcas_landing"], (48.6120, -122.9490), (48.6420, -122.9560),
     (48.6720, -122.9560), (48.6930, -122.9200), (48.6968, -122.9064)],
    [(48.6968, -122.9064), (48.6900, -122.8830), (48.6700, -122.8720),
     (48.6560, -122.8620), (48.6612, -122.8562)],
    [(48.6612, -122.8562), (48.6600, -122.8480), (48.6660, -122.8380),
     (48.6786, -122.8322)],
    [(48.6930, -122.9200), (48.6800, -122.9560), (48.6700, -122.9700),
     (48.6656, -122.9803)],
]

TRAILS = [
    # Cascade Falls trail, off the Mount Constitution road
    [(48.6560, -122.8395), (48.6550, -122.8410), (48.6543, -122.8425)],
    # Ebey's Landing bluff trail
    [(48.1948, -122.7085), (48.2010, -122.7145), (48.2080, -122.7130)],
    # Hurricane Hill, off the ridge
    [(47.9694, -123.4986), (47.9750, -123.5150), (47.9790, -123.5230)],
]

# The 1846 boundary: down the middle of Juan de Fuca, up Haro Strait, through
# Boundary Pass, then the 49th parallel across the mainland.
# The 1846 treaty line: along the 49th parallel to the middle of the Strait of
# Georgia, then "southerly through the middle of that gulf and of Haro Strait"
# to the Strait of Juan de Fuca, then west through the middle of that strait.
# The point is mid-channel. The hand-typed line this replaces ran at -123.17
# through Haro Strait, which is San Juan Island's own west shore: it put the
# international boundary on the beach instead of in the water.
BORDER = [
    (48.2977, -124.8800),   # Juan de Fuca, mid-channel, west of the frame
    (48.2977, -124.4000),
    (48.2950, -124.0000),
    (48.2940, -123.5500),
    (48.2990, -123.3300),   # the turn north into Haro Strait
    (48.3300, -123.2750),
    (48.3900, -123.2850),
    (48.4500, -123.2600),   # Haro Strait: San Juan I. is at -123.15, Vancouver
    (48.5000, -123.2500),   # Island at -123.35, so mid-channel is -123.25
    (48.5600, -123.2450),
    (48.6100, -123.2400),
    (48.6600, -123.2200),
    (48.7000, -123.1700),   # into Boundary Pass
    (48.7350, -123.1000),
    (48.7650, -123.0300),
    (48.7850, -122.9750),   # the northeast end of the pass
    (48.8400, -123.0500),   # out into the Strait of Georgia, north-west
    (48.9300, -123.1900),
    (49.0000, -123.2700),   # meets the 49th parallel mid-strait
]

# From mid-strait east along the parallel. It crosses open water as far as Point
# Roberts (-123.08), whose northern edge the parallel then becomes, which is why
# that US exclave hangs below the line.
BORDER_49 = [
    (49.0000, -123.2700),
    (49.0000, -120.5200),
]


def in_usa(lat: float, lon: float) -> bool:
    """Is this position on the United States side of the boundary?

    Built by closing the treaty line into a polygon around the south and east of
    the region. Used to keep the doodles out of Canada: the geography and the
    place names cross the line, the drawings do not.
    """
    poly = [(la, lo) for la, lo in BORDER]
    poly.append((49.0000, -120.5200))
    poly += [(46.4000, -120.5200), (46.4000, -125.4000), (48.2977, -125.4000)]
    inside = False
    for (la1, lo1), (la2, lo2) in zip(poly, poly[1:] + poly[:1]):
        if (la1 > lat) != (la2 > lat) and lon < lo1 + (lat - la1) / (la2 - la1) * (lo2 - lo1):
            inside = not inside
    return inside

# The divide, through the real passes and volcanoes. West of this line every
# river on the chart runs to the sound; east of it they run to the Columbia.
CREST = [
    (49.0000, -121.1300), (48.8300, -121.0800), (48.6600, -120.9000),
    (48.5250, -120.6540), (48.5140, -120.7340), (48.3300, -120.8500),
    (48.1118, -121.1132), (47.9000, -121.1400), (47.7462, -121.0859),
    (47.5900, -121.2100), (47.4265, -121.4132), (47.3000, -121.3800),
    (47.1500, -121.3900), (46.9000, -121.5000), (46.8296, -121.5200),
]

PASSES = [
    ("Washington Pass · SR-20", (48.5250, -120.6540), -16, -10, "end"),
    ("Stevens Pass · US-2", (47.7462, -121.0859), -14, -6, "end"),
    ("Snoqualmie Pass · I-90", (47.4265, -121.4132), -14, 14, "end"),
]

# ------------------------------------------------------------------ map labels
# (text, lat, lon, class, anchor, rotation)
LABELS = [
    ("· Salish Sea ·", 48.9800, -123.6600, "rt-flavor", "middle", 0),
    ("· Strait of Georgia ·", 49.0450, -123.2600, "rt-flavor", "middle", -32),
    ("· Strait of Juan de Fuca ·", 48.2300, -123.8300, "rt-flavor", "middle", -3),
    ("Haro Strait", 48.5100, -123.2150, "rt-flavor", "middle", -68),
    ("Boundary Pass", 48.7550, -123.1500, "rt-flavor", "middle", -38),
    ("Rosario Strait", 48.5400, -122.7550, "rt-flavor", "middle", -78),
    ("Admiralty Inlet", 48.1200, -122.7150, "rt-flavor", "middle", -52),
    ("Puget Sound", 47.8100, -122.4400, "rt-label water", "middle", -78),
    ("Hood Canal", 47.5700, -122.9250, "rt-flavor", "middle", -56),
    ("Colvos Passage", 47.4750, -122.5250, "rt-flavor", "middle", -74),
    ("East Passage", 47.3900, -122.3800, "rt-flavor", "middle", -68),
    ("Case Inlet", 47.3050, -122.7900, "rt-flavor", "middle", -80),
    ("Carr Inlet", 47.3550, -122.7050, "rt-flavor", "middle", -84),
    ("Budd Inlet", 47.1000, -122.9150, "rt-flavor", "middle", -86),
    ("Bellingham Bay", 48.6900, -122.5400, "rt-flavor", "middle", -46),
    ("Saanich", 48.5750, -123.5100, "rt-sub", "middle", -76),
    ("Grays Harbor", 46.9900, -124.0300, "rt-flavor", "middle", -14),
    ("Vancouver Island", 48.8600, -123.9200, "rt-sub", "middle", -52),
    ("Gulf Islands · BC", 48.8500, -123.4600, "rt-sub", "middle", -40),
    # The island's own name sits in its middle, not on its west coast: at
    # 16 units/km the rotated label is 55 units long, and on the coast it lay
    # across San Juan County Park's name 2 km away.
    ("San Juan I.", 48.5235, -123.0760, "rt-sub", "middle", -50),
    ("Orcas I.", 48.6560, -122.9200, "rt-sub", "middle", 0),
    ("Lopez", 48.4800, -122.8900, "rt-sub", "middle", 0),
    ("Sucia I.", 48.7580, -122.9060, "rt-sub", "start", 0),
    ("Lummi I.", 48.6900, -122.6700, "rt-sub", "middle", -60),
    ("Fidalgo Island", 48.4750, -122.6200, "rt-sub", "middle", 0),
    ("Whidbey Island", 48.1450, -122.5450, "rt-sub", "middle", -58),
    ("Vashon Island", 47.4150, -122.4560, "rt-sub", "middle", -84),
    ("Maury I.", 47.3830, -122.4300, "rt-sub", "middle", 20),
    ("Blake I.", 47.5390, -122.4930, "rt-sub", "start", 0),
    ("Olympic Peninsula", 47.6100, -123.3300, "rt-sub", "middle", 0),
    ("Hoh Rain Forest", 47.8900, -123.9000, "rt-sub", "middle", 0),
    ("Quinault Rain Forest", 47.4800, -123.8100, "rt-sub", "middle", 0),
    ("L. Crescent", 48.0750, -123.8000, "rt-sub", "middle", 0),
    ("L. Cushman", 47.4550, -123.2350, "rt-sub", "start", 0),
    ("Dungeness Spit", 48.1817, -123.1064, "rt-sub", "end", 0),
    ("Sequim", 48.0795, -123.1021, "rt-label", "middle", 0),
    ("Bellingham", 48.7519, -122.4787, "rt-label", "start", 0),
    ("Mount Vernon", 48.4201, -122.3341, "rt-label", "start", 0),
    ("Sidney", 48.6500, -123.3990, "rt-label", "start", 0),
    ("Kingston", 47.7967, -122.4960, "rt-sub", "end", 0),
    ("Bremerton", 47.5673, -122.6329, "rt-label", "middle", 0),
    ("Shelton", 47.2151, -123.1007, "rt-label", "middle", 0),
    ("Gig Harbor", 47.3294, -122.5804, "rt-label", "start", 0),
    ("Tacoma", 47.2529, -122.4443, "rt-label", "start", 0),
    ("Aberdeen", 46.9754, -123.8157, "rt-label", "middle", 0),
    ("Renton", 47.4829, -122.2171, "rt-label", "start", 0),
    ("Kent", 47.3809, -122.2348, "rt-label", "start", 0),
    ("Auburn", 47.3073, -122.2285, "rt-label", "start", 0),
    ("Issaquah", 47.5301, -122.0326, "rt-label", "start", 0),
    ("Kirkland", 47.6769, -122.2060, "rt-label", "start", 0),
    ("Mercer I.", 47.5800, -122.2300, "rt-sub", "middle", 0),
    ("L. Wash.", 47.5750, -122.2380, "rt-sub", "middle", -86),
    ("L. Sammamish", 47.5550, -122.0850, "rt-sub", "middle", -84),
    ("Ross L.", 48.8300, -121.0650, "rt-sub", "middle", -84),
    ("Rattlesnake L.", 47.4330, -121.7770, "rt-sub", "end", 0),
    ("· Cascade Crest ·", 47.9500, -121.0200, "rt-sub", "middle", -84),
]

RIVER_LABELS = [
    ("Nooksack R.", 48.8000, -122.3000, 14),
    ("Skagit R.", 48.4700, -122.1500, 8),
    ("Skykomish R.", 47.8600, -121.5200, -12),
    ("Snoqualmie R.", 47.7050, -121.9500, -50),
    ("Green R.", 47.2600, -121.9500, 30),
    ("Elwha R.", 47.9800, -123.5700, -78),
    ("Dosewallips R.", 47.7300, -123.1300, 12),
    ("Skokomish R.", 47.3300, -123.2600, 26),
    ("Chehalis R.", 46.9600, -123.4000, -12),
    ("Sammamish R.", 47.7200, -122.1500, -40),
]

# -------------------------------------------------------------------- doodles
# The same glyphs as panel 2, at real positions: trees where the forest is,
# elk in the Hoh, orcas where the whale-watching boats go.
DOODLES = [
    ("pine", 47.9200, -123.2000, 1.15), ("pine", 47.7000, -123.5500, 0.9),
    ("pine", 47.5500, -123.4500, 0.8), ("pine", 47.3000, -123.5000, 0.9),
    ("pine", 47.2000, -123.3000, 0.8), ("pine", 47.6100, -122.8400, 0.9),
    ("pine", 47.9000, -122.8500, 0.85), ("pine", 48.2500, -123.9000, 0.75),
    ("pine", 47.6000, -121.6000, 1.0), ("pine", 47.8500, -121.5000, 0.85),
    ("pine", 48.2000, -121.5000, 0.9), ("pine", 48.5500, -121.5000, 0.9),
    ("pine", 47.1000, -121.8000, 0.85), ("pine", 48.9000, -121.9000, 0.8),
    ("rainforest", 47.8606, -123.9500, 0.9), ("rainforest", 47.4800, -123.8300, 0.72),
    ("rainforest", 47.6500, -124.0000, 0.62),
    ("elk", 47.8300, -123.8500, 0.95),
    ("deer", 47.9600, -123.4400, 0.85), ("deer", 48.5500, -123.0600, 0.85),
    ("deer", 47.4000, -123.6000, 0.85),
    ("marmot", 47.9780, -123.5300, 0.9), ("marmot", 47.8500, -123.6500, 0.9),
    ("salmon", 47.3500, -123.3500, 0.7), ("salmon", 46.9700, -123.6000, 0.85),
    ("hen", 48.6618, -122.9742, 0.8),
    # the Rockies sheet
    ("pine", 51.90, -117.30, 1.3),
    ("pine", 52.40, -117.80, 1.2),
    ("pine", 51.05, -116.10, 1.2),
    ("pine", 52.90, -116.60, 1.2),
    ("pine", 50.90, -117.60, 1.1),
    # A grizzly on the shore of Bow Lake, on the Icefields Parkway. This is the
    # one animal on the Rockies sheet that is a specific memory rather than
    # decoration, which is why it is at a lake and not in open country: two elk
    # used to stand here instead, in the middle of nowhere in particular.
    ("bear", 51.6725, -116.4630, 1.15),
    ("deer", 51.25, -114.90, 1.1),
    ("marmot", 52.05, -117.30, 1.1),   # north of the bear, not beside it
    ("salmon", 51.10, -115.10, 0.9),
    ("duck", 48.5320, -123.1540, 0.95), ("duck", 48.5300, -123.1560, 0.8),
    ("duck", 48.5310, -123.1510, 0.7),
    ("ship", 48.5250, -122.7300, 1.0), ("ship", 47.7000, -122.4600, 0.8),
    ("ship", 48.1400, -122.6900, 0.75),
    ("winery", None, None, None),  # placeholder removed at build time
]
DOODLES = [d for d in DOODLES if d[1] is not None]

# Two glyphs that are not decoration but not places with a hover either: the
# anchor at Sidney, the Canadian end of the international ferry, and the light
# at the end of Dungeness Spit. Panel 2 draws both the same way.
MARKS = [
    ("anchor", 48.6500, -123.3990, 0.85),
    ("light", 48.1817, -123.1064, 0.5),
]

# The residents. Panel 2 has a pod off Orcas, a straggler in East Sound, a
# humpback blowing in Haro Strait and a "here be orcas" over the middle of the
# chart; on a true map they go where the whale-watching boats actually find
# them, which is the west side of San Juan Island and Boundary Pass.
WHALES = [
    # Only US waters carry drawings. The J pod and the humpback used to sit at
    # -123.16 and -123.33, which the real treaty line puts in British Columbia.
    ("orca", 48.4380, -123.1560, 1.0, "· here be orcas ·"),
    ("orca-pod", 48.7450, -122.9600, 1.0, "· J pod passing ·"),   # Boundary Pass, US side
    ("orca-fin", 48.6450, -122.8850, 1.0, None),
    ("humpback", 48.5265, -123.1760, 1.1, None),   # seen from the campsite                  # south of San Juan I.
    ("gulls", 48.9100, -122.7400, 1.0, None),
    ("gulls", 47.9300, -122.4200, 0.9, None),
]

# Open water is not blank on a chart: it carries the ripple marks.
WATER_DECO = [
    (48.9600, -123.0500), (48.8000, -122.8000), (48.3000, -123.6000),
    (48.2000, -124.3000), (47.9000, -122.5500), (47.6000, -122.9500),
    (47.2000, -122.8500), (47.0500, -124.3000), (46.9000, -124.5000),
    (48.6000, -124.5000), (48.4000, -124.0000), (47.4500, -124.4000),
]
