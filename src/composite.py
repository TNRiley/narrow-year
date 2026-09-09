"""Turn 2,474 site chronologies into one series: how many trees had a bad year.

The measure is the pointer-year (Cropper) transform.  A site chronology already
has the tree's own age trend divided out, but it still drifts on decadal scales,
so an absolute threshold would flag whole stretches of a cool century rather than
single shock years.  Cropper rescales each year against its own neighbourhood:

    C_t = (x_t - mean(window)) / sd(window)

with a 13-year window centred on t.  C is then a count of standard deviations
against what that site was doing either side of that year, and abrupt events
survive while slow trend cancels.  A year with C <= -1.28 -- the 10th percentile
of a normal -- is recorded as a narrow event for that site.

Two guards:
  * a site-year needs at least MIN_DEPTH cores behind it, because a chronology
    running on one core is one tree's biography, not a climate signal;
  * a year is only reported when at least MIN_SITES sites are available, and the
    page shows that count, because the bank thins to nothing before ~600 CE and
    again after 1990.

The wide-event share (C >= +1.28) is carried through the identical pipeline as a
control.  It is the same arithmetic with the sign flipped, so anything that
inflates one should inflate the other; a spike that appears only in the narrow
series is a real shock, and one that appears in both is an artefact of thin
replication.
"""
import io, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "data", "corpus.json")
OUT = os.path.join(HERE, "data", "composite.json")

WINDOW = 13
MIN_VALID = 11          # values required inside a window
MIN_DEPTH = 5           # cores behind a site-year
MIN_SITES = 50          # sites required before a year is reported
THRESH = 1.28           # ~10th/90th percentile of a standard normal
YMIN, YMAX = -500, 2026


def dated(v):
    if v["y1"] > YMAX or v["y0"] >= v["y1"] or v["y0"] < -3000:
        return False
    return "floating" not in v["site"].lower()


def cropper(years, values, depths):
    """Return {year: C} for years passing the depth guard."""
    y = np.asarray(years, dtype=np.int32)
    x = np.asarray(values, dtype=np.float64)
    d = np.asarray(depths, dtype=np.int32)

    # place the series on a contiguous year axis; internal gaps become NaN
    lo, hi = int(y[0]), int(y[-1])
    n = hi - lo + 1
    if n < WINDOW:
        return {}
    grid = np.full(n, np.nan)
    gd = np.zeros(n, dtype=np.int32)
    idx = y - lo
    ok = (idx >= 0) & (idx < n)
    grid[idx[ok]] = x[ok]
    gd[idx[ok]] = d[ok]

    half = WINDOW // 2
    pad = np.full(half, np.nan)
    g = np.concatenate([pad, grid, pad])
    win = np.lib.stride_tricks.sliding_window_view(g, WINDOW)   # (len(grid), WINDOW)

    cnt = np.sum(~np.isnan(win), axis=1)
    mean = np.nanmean(np.where(np.isnan(win), np.nan, win), axis=1)
    sd = np.nanstd(np.where(np.isnan(win), np.nan, win), axis=1, ddof=1)

    good = (cnt >= MIN_VALID) & (sd > 0) & ~np.isnan(grid) & (gd >= MIN_DEPTH)
    c = np.full(len(grid), np.nan)
    c[good] = (grid[good] - mean[good]) / sd[good]
    yrs = np.arange(lo, hi + 1)
    return {int(a): float(b) for a, b in zip(yrs[good], c[good])}


GROUPS = (
    # Region, not latitude band.  The bank is not a sample of the world: half of
    # it is western North America, so a "global" composite is mostly a western
    # North American one, and the only way to see that is to cut it up.
    ("wna", "western North America",
     lambda v: -170 <= v["lon"] <= -100 and 25 <= v["lat"] <= 72),
    ("ena", "eastern North America",
     lambda v: -100 < v["lon"] <= -52 and 25 <= v["lat"] <= 72),
    ("eur", "Europe",
     lambda v: -12 <= v["lon"] <= 42 and 35 <= v["lat"] <= 72),
    ("asia", "northern Asia",
     lambda v: 42 < v["lon"] <= 190 and 35 <= v["lat"] <= 75),
    ("shem", "southern hemisphere",
     lambda v: v["lat"] < 0),
    ("other", "elsewhere",
     lambda v: True),
)


def group_of(v):
    for key, _label, test in GROUPS:
        if test(v):
            return key
    return "temperate"


def tally(per_site, sites, keys=None):
    """Narrow / wide / available counts per year over a subset of sites."""
    span = YMAX - YMIN + 1
    avail = np.zeros(span, dtype=np.int32)
    narrow = np.zeros(span, dtype=np.int32)
    wide = np.zeros(span, dtype=np.int32)
    for code, c in per_site.items():
        if keys is not None and code not in keys:
            continue
        for yr, cv in c.items():
            if YMIN <= yr <= YMAX:
                i = yr - YMIN
                avail[i] += 1
                if cv <= -THRESH:
                    narrow[i] += 1
                elif cv >= THRESH:
                    wide[i] += 1
    return avail, narrow, wide


def pack(years, avail, narrow, wide, min_sites):
    ok = avail >= min_sites
    return {
        "years": years[ok].tolist(),
        "avail": avail[ok].tolist(),
        "narrow": narrow[ok].tolist(),
        "wide": wide[ok].tolist(),
        "frac": [round(float(x), 5) for x in narrow[ok] / avail[ok]],
        "wfrac": [round(float(x), 5) for x in wide[ok] / avail[ok]],
    }


def main():
    corpus = json.load(io.open(CORPUS, encoding="utf-8"))
    sites = {k: v for k, v in corpus.items() if dated(v)}
    print("sites: %d dated of %d" % (len(sites), len(corpus)))

    per_site = {}
    for code, v in sites.items():
        c = cropper(v["years"], v["values"], v["depths"])
        if c:
            per_site[code] = c
    print("sites with pointer values: %d" % len(per_site))

    years = np.arange(YMIN, YMAX + 1)
    avail, narrow, wide = tally(per_site, sites)
    out = {
        "window": WINDOW, "min_depth": MIN_DEPTH, "min_sites": MIN_SITES,
        "threshold": THRESH, "n_sites": len(per_site),
        "all": pack(years, avail, narrow, wide, MIN_SITES),
        "groups": {},
        "group_labels": {k: lab for k, lab, _ in GROUPS},
    }

    members = {}
    for code in per_site:
        members.setdefault(group_of(sites[code]), set()).add(code)
    for key, label, _ in GROUPS:
        keys = members.get(key, set())
        a, n, w = tally(per_site, sites, keys)
        out["groups"][key] = pack(years, a, n, w, 15)
        out["groups"][key]["n_sites"] = len(keys)

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, separators=(",", ":"))
    with io.open(os.path.join(HERE, "data", "persite.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump(per_site, fh, separators=(",", ":"))

    yy = np.array(out["all"]["years"])
    frac = np.array(out["all"]["frac"])
    wfrac = np.array(out["all"]["wfrac"])
    print("reported years: %d  (%d..%d)" % (len(yy), yy[0], yy[-1]))
    print("mean narrow share %.3f   mean wide share %.3f" % (frac.mean(), wfrac.mean()))
    print("\ngroup sizes:")
    for key, label, _ in GROUPS:
        g = out["groups"][key]
        print("  %-10s %4d sites   %d years reported" % (key, g["n_sites"], len(g["years"])))
    order = np.argsort(-frac)
    print("\nTop 20 narrow years worldwide")
    print("  year   share   narrow/avail   wide share")
    av = np.array(out["all"]["avail"]); nr = np.array(out["all"]["narrow"])
    for i in order[:20]:
        print("  %5d  %5.1f%%   %4d/%4d      %5.1f%%"
              % (yy[i], 100 * frac[i], nr[i], av[i], 100 * wfrac[i]))
    print("\n-> %s" % OUT)


if __name__ == "__main__":
    main()
