"""Pack the corpus, the composites and the eruption list into one payload.

Series are written onto a contiguous year grid from each site's first year to
its last, with 0 marking a year the chronology does not cover -- an ITRDB index
is never 0, so the sentinel is unambiguous and the page can index a year by
subtraction instead of searching.
"""
import base64, io, json, os, sys, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
OUT = os.path.join(D, "payload.json")

# taken from composite.py so the two cannot drift apart
import importlib
GROUP_ORDER = tuple(k for k, _l, _t in importlib.import_module("composite").GROUPS)


def b64(arr):
    return base64.b64encode(arr.tobytes()).decode("ascii")


def main():
    corpus = json.load(io.open(os.path.join(D, "corpus.json"), encoding="utf-8"))
    comp = json.load(io.open(os.path.join(D, "composite.json"), encoding="utf-8"))
    erup = json.load(io.open(os.path.join(D, "eruptions.json"), encoding="utf-8"))
    sys.path.insert(0, HERE)
    from composite import dated, group_of

    sites = {k: v for k, v in corpus.items() if dated(v)}
    codes = sorted(sites, key=lambda k: (-(sites[k]["y1"] - sites[k]["y0"]), k))

    vals, deps = [], []
    rec = {"code": [], "name": [], "lat": [], "lon": [], "elev": [],
           "species": [], "region": [], "group": [], "y0": [], "off": [], "len": []}
    off = 0
    for code in codes:
        v = sites[code]
        y0, y1 = v["y0"], v["y1"]
        n = y1 - y0 + 1
        g = np.zeros(n, dtype=np.int16)
        d = np.zeros(n, dtype=np.uint8)
        idx = np.asarray(v["years"], dtype=np.int64) - y0
        ok = (idx >= 0) & (idx < n)
        g[idx[ok]] = np.clip(np.asarray(v["values"])[ok], 0, 32767)
        d[idx[ok]] = np.clip(np.asarray(v["depths"])[ok], 0, 255)
        vals.append(g)
        deps.append(d)
        rec["code"].append(code)
        rec["name"].append(v["site"][:60])
        rec["lat"].append(v["lat"])
        rec["lon"].append(v["lon"])
        rec["elev"].append(v["elev"] if v["elev"] is not None else -1)
        rec["species"].append(v["species"] or "")
        rec["region"].append(v["region"][:28])
        rec["group"].append(GROUP_ORDER.index(group_of(v)))
        rec["y0"].append(y0)
        rec["off"].append(off)
        rec["len"].append(n)
        off += n

    values = np.concatenate(vals).astype(np.int16)
    depths = np.concatenate(deps).astype(np.uint8)

    common = {}
    for code in codes:
        v = sites[code]
        if v["species"] and v["species"] not in common and v["common"]:
            common[v["species"]] = v["common"].title()

    # Two lists, kept apart on purpose.  Only eruptions with a date somebody
    # wrote down at the time are used for the test, because the ice-core
    # volcanic chronologies were themselves tuned to tree-ring marker years and
    # a few GVP dates are literally *derived* from dendrochronology -- St Helens
    # 1480 and 1482 are dated "Sidereal: Dendrochronology".  Testing tree rings
    # against those would be marking its own homework.  The rest are still worth
    # showing next to a year, labelled with how they were dated.
    er = [r for r in erup
          if (r["vei"] or 0) >= 5 and r["evidence"].startswith("Observations")
          and r["year"] >= 900]
    er_other = [r for r in erup
                if (r["vei"] or 0) >= 5 and not r["evidence"].startswith("Observations")
                and r["year"] >= 900]

    from coastline import arcs as land_arcs
    la = land_arcs()
    coast_pts, coast_len = [], []
    for arc in la:
        coast_len.append(len(arc))
        for lo, lat in arc:
            coast_pts.append(int(round(lo * 100)))
            coast_pts.append(int(round(lat * 100)))

    payload = {
        "built": "2026-09-08",
        "coast": b64(np.asarray(coast_pts, dtype=np.int16)),
        "coast_len": b64(np.asarray(coast_len, dtype=np.uint16)),
        "method": {k: comp[k] for k in ("window", "min_depth", "min_sites", "threshold")},
        "n_sites": len(codes),
        "n_values": int(len(values)),
        "sites": {
            "code": rec["code"], "name": rec["name"], "species": rec["species"],
            "region": rec["region"],
            "lat": b64(np.asarray(rec["lat"], dtype=np.float32)),
            "lon": b64(np.asarray(rec["lon"], dtype=np.float32)),
            "elev": b64(np.asarray(rec["elev"], dtype=np.int16)),
            "group": b64(np.asarray(rec["group"], dtype=np.uint8)),
            "y0": b64(np.asarray(rec["y0"], dtype=np.int16)),
            "off": b64(np.asarray(rec["off"], dtype=np.uint32)),
            "len": b64(np.asarray(rec["len"], dtype=np.uint16)),
        },
        "values": b64(values),
        "depths": b64(depths),
        "composite": comp,
        "eruptions": er,
        "eruptions_other": er_other,
        "common_names": common,
        "group_order": list(GROUP_ORDER),
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    print("sites      %d" % len(codes))
    print("values     %d  (%.1f MB int16)" % (len(values), values.nbytes / 1e6))
    print("eruptions  %d documentary + %d otherwise dated (VEI>=5, >=900 CE)"
          % (len(er), len(er_other)))
    print("coastline  %d arcs, %d points" % (len(la), sum(coast_len)))
    print("payload    %.2f MB" % (os.path.getsize(OUT) / 1e6))
    print("->", OUT)


if __name__ == "__main__":
    main()
