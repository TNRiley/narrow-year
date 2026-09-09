"""Select the total-ring-width chronologies, attach coordinates, write corpus.json.

Selection is made on what each file says it measures, not on its filename.  The
ITRDB encodes the measured parameter in a suffix -- e earlywood width, l
latewood width, n minimum density, x maximum density, i earlywood density, t
latewood density, p latewood percent -- but the suffix is only a convention and
two sites in the bank have their w and x files swapped.  Header line 1 carries
the parameter as a word (WIDTH_RING, DENSITY_MAXIMUM, ...), so read that.  Older
canonical files carry no parameter word at all; those are ring width by default,
but only for the standard, residual and ARSTAN variants -- an unlabelled file
with an e or l suffix is earlywood or latewood and is dropped.

One series per site: standard chronology first, then residual, then ARSTAN.
"""
import glob, io, json, os, re, sys, collections
from parse_crn import parse_crn

HERE = os.path.dirname(os.path.abspath(__file__))
CRNDIR = os.path.join(HERE, "data", "crn")
SITES = os.path.join(HERE, "data", "sites.json")
OUT = os.path.join(HERE, "data", "corpus.json")

PARAM = re.compile(r"\b(WIDTH_RING|WIDTH_EARLY|WIDTH_LATE|DENSITY_EARLY|"
                   r"DENSITY_LATE|DENSITY_MINIMUM|DENSITY_MAXIMUM|LATEWOOD_PERCENT)\b")
# preference order among ring-width variants of one site
RANK = {"": 0, "w_crns": 1, "r": 2, "a": 3}


def variant(fn):
    return re.sub(r"^[a-z]+\d+", "", os.path.basename(fn).lower()).replace(".crn", "")


def sitecode(fn):
    m = re.match(r"^([a-z]+\d+)", os.path.basename(fn).lower())
    return m.group(1) if m else None


def is_ring_width(path):
    head = io.open(path, encoding="latin-1").read(400).split("\n")[0]
    m = PARAM.search(head)
    if m:
        return m.group(1) == "WIDTH_RING"
    return variant(path) in ("", "r", "a")     # unlabelled canonical file


def main():
    sites = json.load(io.open(SITES, encoding="utf-8"))
    best = {}
    stats = collections.Counter()
    for path in sorted(glob.glob(os.path.join(CRNDIR, "*.crn"))):
        stats["files"] += 1
        if not is_ring_width(path):
            stats["not ring width"] += 1
            continue
        code = sitecode(path)
        if code is None:
            stats["no site code"] += 1
            continue
        v = variant(path)
        rank = RANK.get(v, 9)
        if code in best and best[code][0] <= rank:
            stats["duplicate variant"] += 1
            continue
        best[code] = (rank, path)

    out = {}
    for code, (rank, path) in sorted(best.items()):
        r = parse_crn(path)
        if not r:
            stats["unparseable"] += 1
            continue
        meta, years, values, depths = r
        if not years:
            stats["empty"] += 1
            continue
        # A handful of files stack two chronologies without the header line 1
        # that marks a block boundary, so they cannot be split and arrive with
        # every year twice.  Refuse them rather than silently averaging.
        if any(b <= a for a, b in zip(years, years[1:])):
            stats["repeated years"] += 1
            continue
        # 519 year-values across 25 sites are zero or negative.  An index is a
        # ratio to the site's own mean growth and cannot be either, so these are
        # standardisation artefacts, not narrow rings.  Drop them here so that
        # both the Python composite and the page's JavaScript -- which stores
        # the payload unsigned and so excludes them anyway -- see the same data.
        keep = [i for i, x in enumerate(values) if x > 0]
        if len(keep) != len(values):
            stats["non-positive values"] += len(values) - len(keep)
            years = [years[i] for i in keep]
            values = [values[i] for i in keep]
            depths = [depths[i] for i in keep]
        if not years:
            stats["empty after filter"] += 1
            continue
        key = os.path.basename(path).lower()
        geo = sites.get(key)
        if geo is None:
            stats["no coordinates"] += 1
            continue
        out[code] = {
            "file": key,
            "site": geo["site"] or meta["site_name"],
            "lat": geo["lat"],
            "lon": geo["lon"],
            "species": geo["species"] or meta["species"],
            "common": meta["common_name"],
            "region": meta["region"],
            "investigator": meta["investigator"],
            "elev": meta["elev_m"],
            "y0": years[0],
            "y1": years[-1],
            "years": years,
            "values": values,
            "depths": depths,
        }
        stats["kept"] += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, separators=(",", ":"))
    for k, v in stats.most_common():
        print("  %-18s %6d" % (k, v))
    spans = [(v["y0"], v["y1"]) for v in out.values()]
    print("\nsites kept    %d" % len(out))
    print("earliest year %d" % min(s[0] for s in spans))
    print("latest year   %d" % max(s[1] for s in spans))
    print("-> %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))


if __name__ == "__main__":
    main()
