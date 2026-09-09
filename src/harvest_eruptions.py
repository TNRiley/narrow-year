"""Fetch large historical eruptions from the Smithsonian Global Volcanism Program.

The comparison the page makes needs eruption dates that were established
*independently of tree rings*, otherwise it is marking its own homework: the
ice-core volcanic chronologies of the last two millennia were themselves
synchronised against tree-ring marker years, so testing tree rings against them
is partly circular.  GVP records how each date was arrived at, in
StartEvidenceMethod -- 'Historical Observations' is a documentary date from a
witness, and those are the ones the page treats as an independent test.

    python harvest_eruptions.py      # -> data/eruptions.json
"""
import io, json, os, sys, time, urllib.parse, urllib.request

WFS = "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows"
LAYER = "GVP-VOTW:Smithsonian_VOTW_Holocene_Eruptions"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "eruptions.json")
MIN_VEI = 4
MIN_YEAR = 0


def fetch(cql, tries=4):
    q = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeName": LAYER, "outputFormat": "application/json",
        "CQL_FILTER": cql,
    }
    url = WFS + "?" + urllib.parse.urlencode(q)
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "narrow-year/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if a == tries - 1:
                raise
            sys.stderr.write("  retry %d (%s)\n" % (a + 1, e))
            time.sleep(3 * (a + 1))


def main():
    cql = ("ExplosivityIndexMax >= %d AND StartDateYear >= %d "
           "AND Activity_Type = 'Confirmed Eruption'" % (MIN_VEI, MIN_YEAR))
    d = fetch(cql)
    out = []
    for f in d.get("features", []):
        p = f["properties"]
        geo = (f.get("geometry") or {}).get("coordinates") or [None, None]
        out.append({
            "volcano": p.get("Volcano_Name"),
            "year": p.get("StartDateYear"),
            "month": p.get("StartDateMonth") or 0,
            "vei": p.get("ExplosivityIndexMax"),
            "evidence": p.get("StartEvidenceMethod") or "",
            "uncertain": bool(p.get("StartDateYearModifier")),
            "lat": geo[1], "lon": geo[0],
        })
    out.sort(key=lambda r: (r["year"], -(r["vei"] or 0)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=0)

    hist = [r for r in out if r["evidence"].startswith("Observations")]
    print("eruptions VEI>=%d since %d : %d" % (MIN_VEI, MIN_YEAR, len(out)))
    print("  with a documentary date  : %d" % len(hist))
    from collections import Counter
    print("  VEI mix:", dict(Counter(r["vei"] for r in out)))
    print("  evidence:", Counter(r["evidence"] for r in out).most_common(5))
    print("\n  VEI>=6 with documentary dates:")
    for r in out:
        if (r["vei"] or 0) >= 6 and r["evidence"].startswith("Observations"):
            print("    %5d  VEI %d  %s" % (r["year"], r["vei"], r["volcano"]))
    print("\n->", OUT)


if __name__ == "__main__":
    main()
