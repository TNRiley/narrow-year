"""Download the ITRDB site chronologies and unpack them.

NOAA publishes the whole bank as eight regional zips, ~18 MB in total, which is
far kinder than walking the 8,000-file directory listing.

    python fetch_chronologies.py        # -> data/crn/*.crn
"""
import io, os, sys, time, urllib.request, zipfile

BASE = "https://www.ncei.noaa.gov/pub/data/paleo/treering/chronologies/"
VERSION = "itrdb-v713"
REGIONS = ("africa", "asia", "australia", "canada", "europe",
           "mexico", "southamerica", "usa")
HERE = os.path.dirname(os.path.abspath(__file__))
ZIPDIR = os.path.join(HERE, "data", "zips")
CRNDIR = os.path.join(HERE, "data", "crn")


def fetch(url, path, tries=4):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "narrow-year/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r, open(path, "wb") as fh:
                fh.write(r.read())
            return
        except Exception as e:
            if a == tries - 1:
                raise
            sys.stderr.write("  retry %d (%s)\n" % (a + 1, e))
            time.sleep(3 * (a + 1))


def main():
    os.makedirs(ZIPDIR, exist_ok=True)
    os.makedirs(CRNDIR, exist_ok=True)
    total = 0
    for r in REGIONS:
        name = "%s-%s-crn.zip" % (VERSION, r)
        path = os.path.join(ZIPDIR, name)
        if not os.path.exists(path):
            print("fetching", name)
            fetch(BASE + name, path)
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".crn")]
            z.extractall(CRNDIR)
            total += len(names)
        print("  %-14s %5d chronologies" % (r, len(names)))
    print("total %d files in %s" % (total, CRNDIR))


if __name__ == "__main__":
    main()
