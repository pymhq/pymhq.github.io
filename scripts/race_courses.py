"""Every start line, one entry each, with the published course behind it.

Why this file exists
--------------------
The race chart on maps.html used to be one hand-drawn sheet of Puget Sound with
ten little squiggles on it at invented positions. A squiggle is not a course. A
course is a measured line down named streets, and every one of these events
publishes it: the Cherry Blossom Run hands out a GPX, the Kirkland 5K and the
Pumpkin Spice Run keep theirs as Strava routes, the Craft Classic uses
RideWithGPS, the Lake Union 10K and the Waterfront 5K use MapMyRun, the Hot
Chocolate Run keeps a Google My Map, and the B.A.A. prints a PDF.

So the courses here are the real ones. The geometry lives in
maps/data/races/*.json as [lat, lon, ele] triples, lifted from the source named
in `source` on each race and never redrawn by hand. Two exceptions are stated on
their own panels:

  * Boston is routed on the OpenStreetMap street network through the turns the
    B.A.A.'s own course map prints, because the B.A.A. publishes a picture and
    not a track.
  * Tough Mudder publishes no course at all - the venue is a working coal
    property and the course changes every year - so that panel draws the ground
    and says so.

Fields
------
    key        file stem in maps/data/races/ and the svg id
    name       the event, as the organiser writes it
    distance   the official distance string, and `metres` the measured one
    dates      every time I started it, newest last
    where      city, and `venue` the start/finish
    elev       published elevation gain in metres, or None if nobody publishes it
    shape      "loop", "out and back", "point to point"
    surface    what it is run on
    accent     the panel's colour: one race, one hue
    glyph      the small mark in the corner, from the maps.html race defs
    note       what is worth knowing, in the panel's own words
    source     where the geometry came from, printed on the panel
"""

from __future__ import annotations

# --------------------------------------------------------------------- the races
# In the order they were run. Panel 1 is 2018 and panel 9 is 2026, so paging
# right is paging forward in time.
RACES = [
    dict(
        key="tough_mudder",
        name="Tough Mudder Seattle",
        sub="Tougher Mudder World Championship",
        dates=["2018-09-22"],
        distance="10 miles · 22 obstacles",
        metres=16093,
        elev=None,
        laps=2,
        shape="two 5-mile circuits",
        surface="grass, forest singletrack, gravel pit",
        city="Black Diamond, WA",
        venue="Palmer Coking Coal Co.",
        accent="#d98b3a",
        glyph="rc-mudder",
        frame=(-122.045, 47.310, -121.995, 47.340),
        course=None,
        venue_at=(47.31885, -122.00869),
        route=dict(
            # Tough Mudder publishes a course map for the next event only, and
            # the Seattle event is off the calendar, so there is no Seattle map
            # to lift. What there is, is Tough Mudder's own recap of this exact
            # race: "a flat and wide start on fresh grass and paved roads",
            # then Mud Mile, "open fields gave way to dense forests", "snaking
            # through the gravel pits of the mine", and the second 5-mile
            # circuit beginning after Block Ness Monster. So one circuit is
            # routed on the venue's real track network - the forest roads and
            # pit-edge tracks of the Palmer property, from OpenStreetMap -
            # through the ground the recap describes, in that order. It comes
            # out at 7.3 km against a nominal five miles, which is what the
            # mapped network on the property will carry.
            classes=("track", "path", "unclassified", "service", "residential"),
            waypoints=[
                (47.32184, -122.01031),   # the festival field, by the entrance
                (47.33062, -122.01957),   # north into the forest
                (47.32398, -122.01612),   # back down the singletrack
                (47.32130, -122.02447),   # west, the gravel pits of the mine
                (47.31745, -122.01544),   # south field
                (47.32184, -122.01031),   # and round again
            ],
            marks=[
                ("START", 47.32184, -122.01031),
                ("Mud Mile 2.0", 47.32600, -122.01500),
                ("Berlin Walls", 47.32950, -122.01900),
                ("gravel pits · Tight Squeeze", 47.32130, -122.02447),
                ("Block Ness Monster · lap 2", 47.31745, -122.01544),
            ],
        ),
        source=("Course sequence: Tough Mudder's own race recap of 22 Sep 2018 "
                "(toughmudder.com/blog). Circuit routed on the venue's tracks, "
                "OpenStreetMap."),
    ),
    dict(
        key="cherry_blossom_5k",
        name="Seattle Cherry Blossom Run",
        sub="5K · Seward Park",
        dates=["2025-03-22", "2026-04-18"],
        distance="5K",
        metres=4981,
        elev=25,          # published: 82 ft ascent, 118 ft descent
        shape="out and back with a park loop",
        surface="road and park path",
        city="Seattle, WA",
        venue="Seward Park",
        accent="#e6738f",
        glyph="rc-blossom",
        course="cherry_blossom_5k",
        note=[
            "Out of Seward Park, north up Lake Washington Blvd with the water",
            "on the right, then back into the park and round the Bailey",
            "Peninsula loop to finish. Run twice: the 2025 edition in March",
            "and the 2026 edition in April.",
        ],
        source="Official GPX, seattlecherryblossomrun.com (2026 course).",
    ),
    dict(
        key="kirkland_5k",
        name="Kirkland Half Marathon & 5K",
        sub="5K · Juanita Beach Park",
        dates=["2025-05-04", "2026-05-03"],
        distance="5K",
        metres=5040,
        elev=None,
        shape="loop",
        surface="neighbourhood road",
        city="Kirkland, WA",
        venue="Juanita Beach Park",
        accent="#4fb3a5",
        glyph="rc-anchor",
        course="kirkland_5k",
        note=[
            "The half marathon takes the Cross Kirkland Corridor. The 5K stays",
            "on the roads round Juanita Beach Park and Juanita Bay, which is",
            "the hilliest three miles on this whole screen. One aid station,",
            "at about mile two. Run twice, 2025 and 2026.",
        ],
        source="Official Strava route 3194750544282169344, orcarunning.com.",
    ),
    dict(
        key="waterfront_5k",
        name="Meet Me at Waterfront Park 5K",
        sub="the inaugural one",
        dates=["2025-05-31"],
        distance="5K",
        metres=4983,
        elev=None,
        shape="out and back",
        surface="closed street and promenade",
        city="Seattle, WA",
        venue="Waterfront Park, Pier 62",
        accent="#3f9fd6",
        glyph="rc-flag",
        course="waterfront_5k",
        note=[
            "The first 5K ever run through the rebuilt Waterfront Park. South",
            "down a closed Alaskan Way to the turnaround at S Massachusetts St,",
            "back up the pedestrian path, finish on the new promenade. It",
            "crosses the Colman Dock ferry lanes both ways, so the start waves",
            "were sold by how much you minded being stopped for a ferry.",
        ],
        source="Official MapMyRun route 6525944452, waterfrontparkseattle.org.",
    ),
    dict(
        key="craft_classic_5k",
        name="Craft Classic 5K",
        sub="Redmond · Downtown Park",
        dates=["2025-07-27"],
        distance="5K",
        metres=4982,
        elev=13,          # published: 12.74 m
        shape="out and back",
        surface="paved trail",
        city="Redmond, WA",
        venue="Downtown Park",
        accent="#e0a53c",
        glyph="rc-mug",
        course="craft_classic_5k",
        note=[
            "The flattest course here: 13 m of climb in five kilometres. West",
            "out of Downtown Park on the old rail alignment, north up the",
            "Sammamish River Trail, turn at 2.5 km, come back the same way.",
            "There is beer at the end, which is the entire point.",
        ],
        source="Official RideWithGPS route 49860315, orcarunning.com.",
    ),
    dict(
        key="lake_union_10k",
        name="Lake Union 10K",
        sub="16th running · KEXP",
        dates=["2025-08-10"],
        distance="10K",
        metres=10003,
        elev=66,          # published: ~217 ft ascent
        shape="loop",
        surface="street, trail and two bridges",
        city="Seattle, WA",
        venue="Lake Union Park",
        accent="#7a6fd6",
        glyph="rc-gasworks",
        course="lake_union_10k",
        note=[
            "One clockwise lap of the Cheshiahud Loop: up the west side, over",
            "the Fremont Bridge, east along the ship canal past Gas Works",
            "Park, back over the University Bridge and down Eastlake. Two",
            "bridges, one lake, and the only 10K on this screen that closes",
            "on itself.",
        ],
        source="Official MapMyRun route 6159628981, runsignup.com/Race/LakeUnion10K.",
    ),
    dict(
        key="pumpkin_1mi",
        name="Pumpkin Spice Run",
        sub="1 mile · Seward Park",
        dates=["2025-10-12"],
        distance="1 mile",
        metres=1609,
        elev=None,
        shape="out and back",
        surface="lakeside path",
        city="Seattle, WA",
        venue="Seward Park",
        accent="#e08344",
        glyph="rc-pumpkin",
        course="pumpkin_1mi",
        note=[
            "The shortest start line here and the only one run with a pumpkin",
            "in both hands. Flat, out and back along the Lake Washington",
            "shore path inside Seward Park. The 5K and 10K climb the hill into",
            "the forest; the mile does not.",
        ],
        source="Official Strava route 3360686833850247672, orcarunning.com.",
    ),
    dict(
        key="hot_chocolate_5k",
        name="SKECHERS Hot Chocolate Run",
        sub="5K · Seattle Center",
        dates=["2026-02-28"],
        distance="5K",
        metres=5000,
        elev=None,
        shape="out and back",
        surface="closed downtown street",
        city="Seattle, WA",
        venue="Seattle Center",
        accent="#a5714f",
        glyph="rc-cocoa",
        course="hot_chocolate_5k",
        note=[
            "Out of Seattle Center onto a closed Mercer St, south down 5th",
            "Ave N and Cedar St onto 4th Ave, down through the middle of",
            "downtown to a turnaround near Seneca St, then back up 4th and in",
            "by Broad St. The finish hands out a bowl of melted chocolate,",
            "which is a reasonable thing to run three miles for in February.",
        ],
        source="Official course KML, Hot Chocolate Run Seattle Google map.",
    ),
    dict(
        key="boston_10k",
        name="B.A.A. 10K",
        sub="Boston · presented by Mass General Brigham",
        dates=["2026-06-21"],
        distance="10K",
        metres=10000,
        elev=None,
        shape="out and back over two bridges",
        surface="closed city street",
        city="Boston, MA",
        venue="Boston Common",
        accent="#f0c23c",
        glyph="rc-unicorn",
        course=None,
        route=dict(
            # The B.A.A. publishes a drawing, not a track, so this course is
            # routed on the real street network through the turns printed on the
            # official 2026 map. Each waypoint is a junction that map names.
            waypoints=[
                (42.35590, -71.06960),   # start: Charles St at Beacon St
                (42.36070, -71.07030),   # Charles St at Cambridge St
                (42.36145, -71.07640),   # Longfellow Bridge, mid-river
                (42.36185, -71.08090),   # Cambridge end, Memorial Dr
                (42.35870, -71.08640),   # Memorial Dr past MIT
                (42.35650, -71.09180),   # Memorial Dr at the Harvard Bridge
                (42.35300, -71.10520),   # Memorial Dr, the B.U. Bridge turnaround
                (42.35650, -71.09180),   # back east on Memorial Dr
                (42.34990, -71.09050),   # Harvard Bridge, Boston end
                (42.34870, -71.09540),   # Beacon St into Kenmore Square
                (42.34910, -71.10030),   # Kenmore Square at Silber Way
                (42.34880, -71.09120),   # Commonwealth Ave, heading east
                (42.34850, -71.08630),   # Hereford St
                (42.34810, -71.08560),   # Boylston St
                (42.34965, -71.07830),   # the Boston Marathon finish line
                (42.35180, -71.06990),   # Boylston at Arlington St
                (42.35400, -71.06980),   # Arlington at the Public Garden
                (42.35590, -71.06960),   # finish: Charles St, Boston Common
            ],
            marks=[
                ("START", 42.35590, -71.06960),
                ("Longfellow Bridge", 42.36145, -71.07640),
                ("turnaround", 42.35300, -71.10520),
                ("Harvard Bridge", 42.34990, -71.09050),
                ("Kenmore Sq", 42.34910, -71.10030),
                ("Marathon finish line", 42.34965, -71.07830),
                ("FINISH", 42.35590, -71.06960),
            ],
        ),
        note=[
            "The only one not in Puget Sound, and the only one that crosses",
            "another race's finish line. North over the Longfellow Bridge into",
            "Cambridge, west along Memorial Drive with the Charles on the left,",
            "turn just short of the B.U. Bridge, back over the Harvard Bridge,",
            "through Kenmore Square, then right on Hereford and left on",
            "Boylston, which is the last quarter mile of the Boston Marathon.",
        ],
        source="Official 2026 B.A.A. course map (baa.org), routed on OpenStreetMap streets.",
    ),
]

RACE_BY_KEY = {r["key"]: r for r in RACES}


def total_starts() -> int:
    return sum(len(r["dates"]) for r in RACES)
