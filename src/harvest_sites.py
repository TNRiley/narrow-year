"""Harvest ITRDB site metadata from NOAA's paleoclimatology study API.

Why this exists rather than reading the coordinates out of the .crn headers:
the headers write degrees-and-minutes run together and separated by a hyphen --
'6340-14935' for Denali, '4636-804' for a site in the Swiss Alps.  In the first
the hyphen is a minus sign (149 degrees *west*); in the second it is a field
separator (8 degrees *east*).  Nothing in the line distinguishes them, so a
parser that treats the hyphen as a sign flips every eastern-hemisphere site into
the Atlantic, and one that treats it as a separator flips every American site
into the Pacific.  About a third of the corpus is affected either way.

The study API publishes the same sites with signed decimal coordinates, and
names the exact chronology files each site produced, so it joins on filename
with no guessing.  Header coordinates are kept only as a cross-check.

    python harvest_sites.py            # -> data/sites.json
"""
import io, json, os, sys, time, urllib.request

API = ("https://www.ncei.noaa.gov/access/paleo-search/study/search.json"
       "?dataPublisher=NOAA&dataTypeId=18&limit={limit}&skip={skip}")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "sites.json")
LIMIT = 100


def get(url, tries=5):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "narrow-year/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if a == tries - 1:
                raise
            time.sleep(3 * (a + 1))
            sys.stderr.write("  retry %d after %s\n" % (a + 1, e))


def num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if -180 <= f <= 180 else None


def main():
    sites = {}
    skip = 0
    studies = 0
    while True:
        d = get(API.format(limit=LIMIT, skip=skip))
        batch = d.get("study") or []
        if not batch:
            break
        studies += len(batch)
        for s in batch:
            for site in s.get("site", []):
                props = (site.get("geo") or {}).get("properties") or {}
                lat = num(props.get("southernmostLatitude"))
                lat2 = num(props.get("northernmostLatitude"))
                lon = num(props.get("westernmostLongitude"))
                lon2 = num(props.get("easternmostLongitude"))
                if lat is None or lon is None:
                    continue
                # point sites repeat the same value in both corners
                if lat2 is not None:
                    lat = (lat + lat2) / 2.0
                if lon2 is not None and abs(lon2 - lon) < 180:
                    lon = (lon + lon2) / 2.0
                rec = {
                    "site": site.get("siteName") or "",
                    "lat": round(lat, 4),
                    "lon": round(lon, 4),
                    "study": s.get("studyName") or "",
                    "doi": s.get("doi") or "",
                    "elev": props.get("minElevationMeters"),
                    "species": "",
                }
                for pd in site.get("paleoData", []):
                    sp = pd.get("species") or []
                    if sp and not rec["species"]:
                        code = sp[0].get("speciesCode") or ""
                        rec["species"] = code
                    for f in pd.get("dataFile", []):
                        url = f.get("fileUrl") or ""
                        if url.lower().endswith(".crn"):
                            sites[os.path.basename(url).lower()] = rec
        sys.stderr.write("skip=%d  studies=%d  crn files mapped=%d\n"
                         % (skip, studies, len(sites)))
        skip += LIMIT
        if len(batch) < LIMIT:
            break
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(sites, fh, indent=0, sort_keys=True)
    print("studies %d   chronology files with coordinates %d" % (studies, len(sites)))
    print("->", OUT)


if __name__ == "__main__":
    main()
