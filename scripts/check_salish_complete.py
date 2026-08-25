#!/usr/bin/env python3
"""Is the generated to-scale section complete and honest?

The collision checker in check_salish_sheet.py asks whether the sheets are
*legible*. This one asks whether they are *complete and true*, which is the
question that kept being answered by eye and kept being answered wrong:

  1. every glyph the data intends is drawn on at least one sheet
  2. every place with a glyph has that glyph somewhere
  3. no drawing sits in Canada
  4. no drawing sits on the index sheet
  5. every drawing is on the correct side of the shore
  6. the visited/not-visited rule is applied, and to the right islands

Run after scripts/build_salish_geo_panel.py.

Usage:
    python3 scripts/check_salish_complete.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import salish_places as P  # noqa: E402
from salish_geo import in_ring, island_rings, is_dry  # noqa: E402

import build_salish_geo_panel as B  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps.html"


def sheets_markup(html: str) -> dict[str, str]:
    sec = re.search(r"<!-- BEGIN generated: salish sea to scale.*?"
                    r"<!-- END generated: salish sea to scale -->", html, re.S)
    if not sec:
        raise SystemExit("generated section not found in maps.html")
    out = {}
    for m in re.finditer(r'<svg class="sg-sheet" id="sg-sheet-([a-z]+)".*?</svg>',
                         sec.group(0), re.S):
        svg = m.group(0)
        body = svg[svg.index("</defs>"):]
        # The apron is not the map. Its legend draws an anchor and a dashed box
        # on purpose, and counting those as chart drawings makes the index sheet
        # look like it still carries doodles.
        cut = body.find('<g class="sg-apron-layer">')
        out[m.group(1)] = body[:cut] if cut > 0 else body
    return out


def main() -> int:
    html = MAPS.read_text()
    bodies = sheets_markup(html)
    keys = [s["key"] for s in P.SHEETS]
    fails: list[str] = []

    print(f"sheets: {len(bodies)}  ({', '.join(bodies)})")
    if list(bodies) != keys:
        fails.append(f"sheet order {list(bodies)} != data order {keys}")

    drawn: dict[str, list[str]] = {k: re.findall(r'href="#sg-([a-z0-9_-]+)"', v)
                                  for k, v in bodies.items()}

    # ---- 1 & 2: every intended glyph reaches a sheet -----------------------
    print("\n1. glyph instances intended by the data, and where they land")
    want: dict[str, int] = {}
    for p in P.POIS:
        if not P.in_usa(*p["at"]):
            continue          # Canada keeps its names, not its drawings
        if p.get("ic"):
            want[p["ic"]] = want.get(p["ic"], 0) + 1
        for e in p.get("extra", []):
            want[e[0]] = want.get(e[0], 0) + 1
    for ic, la, lo, sc in P.DOODLES + P.MARKS:
        if P.in_usa(la, lo):
            want[ic] = want.get(ic, 0) + 1
    for s in P.SUMMITS:
        if P.in_usa(*s["at"]):
            want[s["glyph"]] = want.get(s["glyph"], 0) + 1
    for w in P.WHALES:
        if P.in_usa(w[1], w[2]):
            want[w[0]] = want.get(w[0], 0) + 1
    never = [g for g in sorted(want) if not any(g in d for d in drawn.values())]
    print(f"   distinct glyphs intended: {len(want)}   never drawn: {len(never)}")
    if never:
        fails.append(f"glyphs never drawn anywhere: {never}")
        for g in never:
            print(f"     MISSING {g}")

    print("\n2. every place with a glyph has its drawing on some sheet")
    sizes = B.glyph_extents(B.panel2_defs(html))
    homes: dict[str, list[str]] = {}
    for sheet in P.SHEETS:
        if not sheet.get("doodles", True):
            continue
        frame = sheet["frame"]
        mx, mw, mh = B.sheet_geometry(frame)
        from salish_geo import Proj
        proj = Proj(frame[0], frame[1], frame[2], frame[3], mx, 0, mw, mh)
        inside = [p for p in B.unique_places() if B.on_frame(*p["at"], frame)]
        anchors, displaced, dots, _ = B.fit_places(inside, proj, sizes, sheet["key"])
        for p in anchors + [d[0] for d in displaced]:
            if P.in_usa(*p["at"]):
                homes.setdefault(p["key"], []).append(sheet["key"])
    need = [p for p in B.unique_places() if p.get("ic") and P.in_usa(*p["at"])]
    orphan = [p["key"] for p in need if p["key"] not in homes]
    print(f"   US places with a glyph: {len(need)}   without a home: {len(orphan)}")
    if orphan:
        fails.append(f"places whose glyph is drawn nowhere: {orphan}")

    # ---- 3: nothing drawn in Canada ---------------------------------------
    print("\n3. no drawing in Canada, except on the sheets that are Canada")
    # The Vancouver and Rockies sheets set usa_only=False and are allowed their own
    # drawings; the rule is that Canada gets no drawings on the *US* sheets.
    ca_ok = set()
    for sh in P.SHEETS:
        if not sh.get("usa_only", True):
            ca_ok |= set(sh.get("only") or ())
    ca = [(p["key"], p["ic"]) for p in P.POIS
          if p.get("ic") and not P.in_usa(*p["at"]) and p["key"] not in ca_ok]
    ca += [(f"deco {ic}", ic) for ic, la, lo, sc in P.DOODLES + P.MARKS
           if not P.in_usa(la, lo)]
    ca += [(f"whale {w[0]}", w[0]) for w in P.WHALES if not P.in_usa(w[1], w[2])]
    print(f"   items on the Canadian side: {len(ca)} "
          f"({', '.join(k for k, _ in ca) or 'none'})")
    # The rule is about the US sheets, so the test has to be too. It used to ask
    # whether the glyph appeared on *any* sheet, which a glyph that exists only in
    # Canada can never pass: the bear at Bow Lake failed for being drawn on the
    # Canada sheet, which is the sheet it is for.
    us_sheets = {s["key"] for s in P.SHEETS if s.get("usa_only", True)}
    for key, ic in ca:
        # its glyph may legitimately appear elsewhere for a US place; only flag a
        # glyph that no US item uses at all
        us_uses = any(q.get("ic") == ic and P.in_usa(*q["at"]) for q in P.POIS)
        us_uses = us_uses or any(ic == d[0] and P.in_usa(d[1], d[2])
                                 for d in P.DOODLES + P.MARKS)
        us_uses = us_uses or any(ic == w[0] and P.in_usa(w[1], w[2])
                                 for w in P.WHALES)
        if not us_uses and any(ic in drawn[k] for k in us_sheets):
            fails.append(f"Canadian drawing still on a US sheet: {key} ({ic})")
            print(f"     DRAWN ON A US SHEET {key} ({ic})")

    # ---- 4: the index sheet draws nothing ---------------------------------
    print("\n4. the index sheet carries no drawings")
    idx = next(s["key"] for s in P.SHEETS if not s.get("doodles", True))
    art = {"anchor", "siren", "needle", "whale", "tent", "pot", "falls", "tower",
           "pine", "deer", "elk", "duck", "hen", "ship", "orca", "orca-pod",
           "humpback", "gulls", "rainforest", "mtns", "baker", "shuksan",
           "rainier", "glacier_peak", "saddle", "marmot", "salmon", "oyster",
           "swanboat", "croissant", "lakeshore", "seastack"}
    on_idx = sorted(set(drawn[idx]) & art)
    print(f"   drawings on '{idx}': {len(on_idx)} {on_idx}")
    if on_idx:
        fails.append(f"index sheet '{idx}' still draws: {on_idx}")

    # ---- 5: correct side of the shore -------------------------------------
    print("\n5. every drawing on the correct side of the shore")
    wrong = []
    for p in P.POIS:
        ic = p.get("ic")
        if not ic or not P.in_usa(*p["at"]):
            continue
        want_dry = B.glyph_side(ic)
        if want_dry is None:
            continue
        (lat, lon), moved = B.draw_at(p["at"][0], p["at"][1], ic)
        if is_dry((lon, lat)) != want_dry:
            wrong.append((p["key"], ic, "land" if want_dry else "water", moved))
    print(f"   glyphs with a side to respect, still on the wrong one: {len(wrong)}")
    for k, ic, side, moved in wrong:
        fails.append(f"{k} ({ic}) should be on {side}; snap reached {moved:.0f} m")
        print(f"     WRONG SIDE {k} ({ic}) wants {side}")

    # ---- 6: the visited rule -----------------------------------------------
    print("\n6. the visited / not-visited rule")
    for sheet in P.SHEETS:
        body = bodies[sheet["key"]]
        frame = sheet["frame"]
        theirs = [r for r in B._unvisited_islands()
                  if any(B.on_frame(la, lo, frame) for lo, la in r[::7])]
        has = 'class="rt-island unseen" d=' in body
        print(f"   {sheet['key']:9} islands not mine in frame: {len(theirs):4}"
              f"   lighter layer present: {has}")
        if theirs and not has:
            fails.append(f"{sheet['key']} has {len(theirs)} islands that are not "
                         f"mine but draws no lighter land")
    # The islands whose colour is the point of the rule. Asked of the island's own
    # coastline, so the answer must be the same however the sheet is framed.
    checks = [("San Juan Island", 48.5500, -123.1000, True),
              ("Orcas", 48.6786, -122.8322, True),
              ("Whidbey", 48.2201, -122.6857, True),
              ("Bainbridge", 47.6300, -122.5400, True),
              ("Vashon", 47.4400, -122.4600, True),
              ("Maury", 47.3830, -122.4300, True),
              ("Fidalgo", 48.4900, -122.6300, True),
              ("Lopez", 48.4800, -122.8800, False),
              ("Shaw", 48.5780, -122.9300, False),
              ("Camano", 48.2000, -122.5000, False),
              ("Lummi", 48.6900, -122.6700, False),
              ("Salt Spring, BC", 48.8300, -123.4830, False),
              ("Blake", 47.5390, -122.4930, False)]
    print("   named islands, by the rule:")
    for name, lat, lon, want in checks:
        holder = [r for r in island_rings() if in_ring((lon, lat), r)]
        if not holder:
            fails.append(f"{name} is inside no island ring")
            print(f"     {name}: IN NO RING")
            continue
        # The innermost ring holding the point is the island itself.
        ring = min(holder, key=B.ring_span_km)
        got = B.island_is_mine(ring)
        ok = got == want
        if not ok:
            fails.append(f"{name}: visited={got}, expected {want}")
        print(f"     {'ok ' if ok else 'BAD'} {name:16} visited={got} "
              f"expected={want}")

    # ---- 7: the one painted region ------------------------------------------
    print("\n7. the Kitsap region and the Poulsbo circle")
    for part in P.PARTLY_VISITED:
        ring = part["region"]["ring"]
        # What the polygon must and must not hold. The wash is clipped to the
        # shore, so its edges in the water are invisible and only this matters:
        # the peninsula inside it, every neighbouring landmass outside it.
        inside_want = [("Poulsbo", 47.7362, -122.6465), ("Bremerton", 47.5673, -122.6329),
                       ("Silverdale", 47.645, -122.694), ("Port Orchard", 47.540, -122.636),
                       ("Kingston", 47.796, -122.497), ("Port Gamble", 47.855, -122.583),
                       ("Seabeck", 47.641, -122.828), ("Belfair", 47.449, -122.827),
                       ("Gig Harbor", 47.345, -122.605), ("Key Peninsula", 47.30, -122.72)]
        outside_want = [("Seattle", 47.6062, -122.3321), ("Tacoma", 47.2529, -122.4443),
                        ("Shelton", 47.2151, -123.1007), ("Olympia", 47.0357, -122.9053),
                        ("Hoodsport, Olympic side", 47.404, -123.140),
                        ("Quilcene, Olympic side", 47.827, -122.877),
                        ("Port Townsend", 48.117, -122.760), ("Sequim", 48.078, -123.100)]
        for name, lat, lon in inside_want:
            if not P.in_ring_latlon(lat, lon, ring):
                fails.append(f"{name} should be inside the {part['region']['name']}")
                print(f"     BAD {name:24} outside, expected inside")
        for name, lat, lon in outside_want:
            if P.in_ring_latlon(lat, lon, ring):
                fails.append(f"{name} should be outside the {part['region']['name']}")
                print(f"     BAD {name:24} inside, expected outside")
        print(f"   {part['region']['name']}: {len(inside_want)} places in, "
              f"{len(outside_want)} places out, {len(ring)} vertices")
        # The circle has to sit on the region it is an exception to, and on land.
        for name, lat, lon, km_r in part["spots"]:
            if not P.in_ring_latlon(lat, lon, ring):
                fails.append(f"the {name} circle is not on {part['region']['name']}")
            if not is_dry((lon, lat)):
                fails.append(f"the {name} circle is centred on water")
            print(f"   {name}: {km_r:g} km, on the region and on land")

    print("\n" + "=" * 60)
    if fails:
        print(f"FAILURES: {len(fails)}")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("complete: every drawing has a home, none in Canada, none on the index,")
    print("all on the right side of the shore, and the visited rule holds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
