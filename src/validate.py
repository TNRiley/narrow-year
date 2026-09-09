"""Two independent checks on the parse, neither using the header years.

1. Geography.  An ITRDB filename begins with a code for where the site is --
   two letters for a US state, four for most countries.  That is recorded
   entirely separately from the coordinates in the header, so agreement between
   them is real evidence the degrees-and-minutes conversion is right.

2. The decade-floor rule.  If data lines are aligned to the decade rather than
   to their own year label, then on a first data line the offset of the label
   from its decade floor must equal the number of leading no-data slots.  This
   is a structural prediction that does not depend on any header field.
"""
import glob, os, sys, collections
from parse_crn import parse_crn, NODATA

# generous state boxes -- the test is "not in the wrong place", not "precise"
BOX = {
    "ak": (51, 72, -173, -129), "az": (31, 37.5, -115, -108.5),
    "ca": (32, 42.5, -125, -114), "co": (36.5, 41.5, -109.5, -101.5),
    "id": (41.5, 49.5, -117.5, -110.5), "mt": (44.0, 49.5, -116.5, -103.5),
    "nm": (31, 37.5, -109.5, -102.5), "nv": (34.5, 42.5, -120.5, -113.5),
    "or": (41.5, 46.5, -125, -116), "ut": (36.5, 42.5, -114.5, -108.5),
    "wa": (45.0, 49.5, -125, -116.5), "wy": (40.5, 45.5, -111.5, -103.5),
    "mi": (41.5, 48.5, -90.5, -82), "mn": (43, 49.5, -97.5, -89),
    "nc": (33.5, 37, -84.5, -75), "ny": (40.3, 45.2, -80, -71.7),
    "tx": (25.5, 36.8, -107, -93), "sd": (42.5, 46.2, -104.5, -96),
    "germ": (47, 55.5, 5, 16), "fran": (41, 51.5, -5.5, 9.8),
    "spai": (35.5, 44, -9.5, 4.5), "swit": (45.7, 47.9, 5.8, 10.6),
    "finl": (59.5, 70.5, 19, 32), "swed": (55, 69.5, 10.5, 24.5),
    "norw": (57.5, 71.5, 4, 31.5), "ital": (36.5, 47.2, 6.5, 18.6),
    "turk": (35.8, 42.2, 25.6, 45), "russ": (41, 82, 19, 190),
    "cana": (41.5, 84, -141, -52), "mexi": (14, 33, -118, -86),
    "arge": (-56, -21, -74, -53), "chil": (-56, -17, -76, -66),
    "japa": (24, 46, 122, 154), "nepa": (26, 30.5, 80, 88.5),
    "mong": (41.5, 52.2, 87, 120), "chin": (18, 54, 73, 135),
    "newz": (-47.5, -34, 166, 179), "autr": (46.3, 49.1, 9.5, 17.2),
}


def code(fn):
    base = os.path.basename(fn).lower()
    for n in (4, 2):
        if base[:n] in BOX and (base[n:n + 1].isdigit() or n == 4):
            return base[:n]
    return None


def main(ex):
    hits = collections.Counter()
    miss = collections.Counter()
    examples = collections.defaultdict(list)
    nolat = 0
    floor_ok = floor_bad = 0
    floor_ex = []

    for p in sorted(glob.glob(os.path.join(ex, "*.crn"))):
        r = parse_crn(p)
        if not r:
            continue
        meta, y, v, d = r
        if not y:
            continue
        c = code(p)
        if c:
            if meta["lat"] is None:
                nolat += 1
            else:
                lo_a, hi_a, lo_o, hi_o = BOX[c]
                if lo_a <= meta["lat"] <= hi_a and lo_o <= meta["lon"] <= hi_o:
                    hits[c] += 1
                else:
                    miss[c] += 1
                    if len(examples[c]) < 2:
                        examples[c].append((meta["file"], meta["lat"], meta["lon"]))
        ok, off = _floor_check(p, meta["id"])
        if ok is True:
            floor_ok += 1
        elif ok is False:
            floor_bad += 1
            if len(floor_ex) < 8:
                floor_ex.append((meta["file"], off))

    th, tm = sum(hits.values()), sum(miss.values())
    print("GEOGRAPHY  (filename code vs parsed coordinates)")
    print("  inside expected box : %5d" % th)
    print("  outside             : %5d" % tm)
    print("  no coordinates      : %5d" % nolat)
    print("  agreement           : %.2f%%" % (100.0 * th / max(1, th + tm)))
    if tm:
        print("  worst codes:")
        for c, n in miss.most_common(6):
            print("    %-5s %4d outside / %4d inside   e.g. %s"
                  % (c, n, hits[c], examples[c][:1]))
    print()
    print("DECADE-FLOOR RULE  (label offset == leading no-data slots)")
    print("  holds     : %5d" % floor_ok)
    print("  violated  : %5d" % floor_bad)
    print("  agreement : %.2f%%" % (100.0 * floor_ok / max(1, floor_ok + floor_bad)))
    for e in floor_ex:
        print("    ", e)


def _floor_check(path, sid):
    import io
    text = io.open(path, encoding="latin-1").read()
    for ln in (l.rstrip("\r\n") for l in text.split("\n")):
        if len(ln) <= 9 or (ln[6:9].strip() in ("1", "2", "3") and ln[:6].strip() == sid):
            continue
        body = ln[6:]
        if "." in body:
            continue
        try:
            label = int(body[:4])
        except ValueError:
            continue
        rest = body[4:]
        lead = 0
        for k in range(10):
            ch = rest[k * 7:(k + 1) * 7]
            if len(ch) < 7:
                return None, None
            try:
                val, dep = int(ch[:4]), int(ch[4:])
            except ValueError:
                return None, None
            if val in NODATA and dep == 0:
                lead += 1
            else:
                break
        off = label - (label // 10) * 10
        return (lead == off), (label, lead, off)
    return None, None


if __name__ == "__main__":
    main(sys.argv[1])
