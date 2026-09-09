"""Parse ITRDB Tucson-format chronology (.crn) files.

The format is fixed-width, predates most of the software that reads it, and is
not obeyed by every contributor.  So this reads the canonical columns first,
falls back to tokenising when a contributor ignored them, and then *checks
itself*: every series is validated against the first/last year the file's own
header claims, and every coordinate against the geography its filename encodes.

Four things about the layout are not guessable, and each costs an afternoon:

  * The ten values on a data line are aligned to the **decade floor** of the
    line's year label, not to the label itself.  A first line labelled 1422
    carries 1420..1429, with 1420 and 1421 present as 9990/0 padding.  Read it
    as 1422..1431 and every series is silently shifted by up to nine years --
    which, in a project about dating wood to the exact year, is the ballgame.
  * 9990 is the no-data value, not a ring width.  It always arrives with a
    sample depth of 0, which is the reliable test; a few files use 9999.
  * Coordinates are degrees-and-minutes run together, with no separator and no
    consistent width: 6026 is 60d26', 05445 is 54d45', 535 is 5d35'.  Read ddmm
    as a decimal and Alaska lands in the Gulf of Guinea.
  * 36% of the corpus uses classic Mac CR-only line endings.  Python's text
    mode handles it; splitting raw bytes on \n does not, and yields one 16 KB
    line that still parses to a plausible-looking span rather than an error.
  * 3,205 files hold **four chronologies stacked in one file**, each introduced
    by its own header line 1: raw mean ring width, then the standard, residual
    and ARSTAN indices.  Read the file as a single series and every year appears
    four times over; take the first block and you get raw widths in hundredths
    of a millimetre, age trend still in them, where an index was wanted.
    Neither mistake raises anything.

Values are dimensionless ring-width indices scaled by 1000 (1000 = the site's
own average year), each paired with the number of cores contributing to it.
"""
import io, os, re, sys

NODATA = (9990, 9999)
MAX_BLOCKS = 4     # beyond this, a file is separate timbers, not one site
# A signed token may sit flush against the previous one ("06026-14745"), so the
# "not preceded by a digit" guard has to apply to the unsigned branch only --
# applied to both, it rejects "-14745", rematches it as "14745", and every
# western longitude in the corpus silently flips to the eastern hemisphere.
_NUM = re.compile(r"([+-]\d{3,5}|(?<![.\d])\d{3,5})(?![.\d])")


def _degmin(tok, lim):
    """'6026' -> 60.433.  Trailing two digits are arc minutes, the rest degrees."""
    neg = tok.startswith("-")
    tok = tok.lstrip("+-")
    if len(tok) < 3:
        return None
    deg, mins = int(tok[:-2]), int(tok[-2:])
    if mins > 59 or deg > lim:
        return None
    v = deg + mins / 60.0
    return round(-v if neg else v, 4)


def _latlon(line):
    """Find the ddmm/dddmm pair and convert it.

    Scoring matters, and so does *overlap*.  'White Spruce 750  6340-14935'
    offers two candidate pairs -- (750, 6340) and (6340, -14935) -- and a single
    two-group regex never sees the second, because finditer has already consumed
    6340 inside the first match; it returns the elevation as a latitude and puts
    Denali in the Gulf of Guinea.  So enumerate the numeric tokens and consider
    every adjacent pair.

    The tell for a real pair is the separator: coordinates are written joined,
    or split only by the longitude's own minus sign, while a pair that has
    swallowed the elevation has whitespace (or a stray 'M') between its halves.
    Rank by separator width, then by proximity to the canonical column 48.
    """
    toks = list(_NUM.finditer(line))
    best = None
    for a, b in zip(toks, toks[1:]):
        lat = _degmin(a.group(1), 90)
        lon = _degmin(b.group(1), 180)
        if lat is None or lon is None or (lat == 0 and lon == 0):
            continue
        sep = line[a.end():b.start()]
        cost = (0 if sep.strip() == "" else 1, len(sep), abs(a.start() - 47))
        if best is None or cost < best[0]:
            best = (cost, lat, lon, b.end())
    if best is None:
        return None, None, None
    return best[1], best[2], best[3]


def _hdr_years(line, after):
    """First/last year as the contributor recorded it -- a check on the parse,
    not a source of truth: it is stale by a year or two across ~5% of the
    corpus.  The pair follows the coordinates in every dialect seen here, so
    anchor to them rather than to a column."""
    if after is None:
        return None
    m = re.search(r"(?<![-.\d])(-?\d{3,4})\s+(\d{3,4})(?![.\d])", line[after:])
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    return (a, b) if a <= b <= 2030 else None


def _headers(lines):
    """The three header lines.  Normally tagged 1/2/3 in columns 7-9, but a site
    code longer than six characters pushes the tag out of its column and the
    tags vanish, so fall back to the first three lines positionally."""
    hdr = {}
    for ln in lines[:3]:
        tag = ln[6:9].strip()
        if tag in ("1", "2", "3") and tag not in hdr:
            hdr[tag] = ln
    if "2" not in hdr:
        for i, key in enumerate(("1", "2", "3")):
            if i < len(lines):
                hdr.setdefault(key, lines[i])
    return hdr.get("1", ""), hdr.get("2", ""), hdr.get("3", "")


def _text_fields(h2, lat):
    """Region and common name.  The fixed columns hold only for the canonical
    layout; the loose one runs '<id> 2 United States of America   White Spruce
    750  6340-14935 ...' and slicing it yields 'of America   Whit'."""
    fixed_region = h2[9:22].strip()
    fixed_name = h2[22:40].strip()
    # If the first whitespace-delimited field runs past the 13 columns the
    # canonical layout allots it, the contributor ignored the columns and the
    # slices are cutting words in half ('of America   Whit').
    parts = [t for t in re.split(r"\s{2,}", h2[9:].strip()) if t]
    loose = bool(parts) and len(parts[0]) > 13
    if loose:
        region = parts[0]
        name = parts[1] if len(parts) > 1 else ""
        # the loose dialect trails the name with elevation and coordinates
        name = re.split(r"\s+\d{2,5}\s*$", name)[0].strip()
        return region, name
    return fixed_region, fixed_name


def _elevation(h2):
    m = re.search(r"(\d+)\s*M\b", h2[36:52])
    if m:
        return int(m.group(1))
    m = re.search(r"(?<![-.\d])(\d{1,4})\s{1,2}(?=[+-]?\d{3,5}[ ]*[+-]?\d{3,5})", h2)
    return int(m.group(1)) if m else None


def parse_crn(path):
    text = io.open(path, encoding="latin-1").read()   # text mode == universal newlines
    lines = [ln for ln in (l.rstrip("\r\n") for l in text.split("\n")) if len(ln) > 9]
    if not lines:
        return None

    h1, h2, h3 = _headers(lines)
    lat, lon, after = _latlon(h2)
    region, common = _text_fields(h2, lat)

    meta = {
        "file": os.path.basename(path),
        "id": (h1 or lines[0])[:6].strip(),
        "site_name": h1[9:61].strip(),
        "region": region,
        "common_name": common,
        # species code: four capitals standing alone late in header line 1
        "species": (re.findall(r"\b([A-Z]{4})\b", h1[40:]) or [""])[-1],
        "elev_m": _elevation(h2),
        "lat": lat,
        "lon": lon,
        "hdr_years": _hdr_years(h2, after),
        "investigator": h3[9:61].strip(),
    }
    years, values, depths = _data(lines, meta["id"])
    meta["n"] = len(years)
    return meta, years, values, depths


def _is_data(body):
    """A data line is a year in columns 7-10 followed by nothing but digits,
    spaces and minus signs.

    Classifying by the header tag in columns 7-9 instead looks equivalent and is
    not: a chronology starting before year 40 writes its decade labels as 10, 20
    and 30, which right-align into exactly those columns and read back as header
    tags 1, 2 and 3.  Those three decades are then dropped, and the series
    silently begins at year 40 -- which is why eight bristlecone chronologies,
    the oldest records in the bank, all claimed to start in the same year.
    """
    field = body[4:4 + 10 * 7]     # ten values of four digits plus three of depth
    if "." in field:               # '.' marks the ARSTAN statistics footer
        return False
    # Only the value field may be inspected: one dialect labels every data line
    # with a trailing '  RAW', so a no-letters test over the whole line rejects
    # the entire Schweingruber network -- 3,205 files, without an error.
    return field.strip() != "" and not any(ch.isalpha() for ch in field)


def _blocks(lines):
    """Split a file into its stacked chronologies at each header line 1.

    The 'is it a data line' test is needed here too, for the same reason: a
    chronology reaching back before year 40 has a decade line labelled 10, whose
    digits land in the header-tag columns.  Split on that and the bristlecone
    records are cut in two, with everything after year 10 discarded as a second
    block.
    """
    starts = [i for i, ln in enumerate(lines)
              if ln[6:9].strip() == "1" and not _is_data(ln[6:])]
    if not starts:
        return [lines]
    starts.append(len(lines))
    return [lines[starts[i]:starts[i + 1]] for i in range(len(starts) - 1)]


def _index_like(values):
    """An ITRDB index is scaled so the site's own mean year is 1000.  A raw
    ring-width block is an absolute measurement in hundredths of a millimetre
    and lands anywhere from 100 to 3000."""
    if not values:
        return False
    m = sum(values) / float(len(values))
    return 900.0 <= m <= 1100.0


def _read_block(block):
    years, values, depths = [], [], []
    for ln in block:
        body = ln[6:]
        if not _is_data(body):
            continue
        try:
            label = int(body[:4])
        except ValueError:
            continue
        rest = body[4:]
        decade = (label // 10) * 10
        for k in range(10):
            chunk = rest[k * 7:(k + 1) * 7]
            if len(chunk) < 7:
                break
            try:
                val, dep = int(chunk[:4]), int(chunk[4:])
            except ValueError:
                continue
            if val in NODATA and dep == 0:
                continue
            years.append(decade + k)
            values.append(val)
            depths.append(dep)
    return years, values, depths


def _data(lines, sid):
    """The first block that carries an index rather than raw widths.

    That one rule covers every stacking seen in the bank: a plain ITRDB file
    (one block, already an index); standard/residual/ARSTAN stacked (three
    blocks, all indices, take the standard); and the Schweingruber layout (four
    blocks, where block 0 is raw mean ring width and the standard chronology is
    block 1).  Files stacking more than MAX_BLOCKS blocks are collections of
    individual timbers from one excavation rather than a site chronology, and
    are refused.
    """
    blocks = _blocks(lines)
    if len(blocks) > MAX_BLOCKS:
        return [], [], []
    parsed = [_read_block(b) for b in blocks]
    for years, values, depths in parsed:
        if years and _index_like(values):
            return years, values, depths
    return parsed[0] if parsed else ([], [], [])


if __name__ == "__main__":
    for p in sys.argv[1:]:
        meta, y, v, d = parse_crn(p)
        print(meta)
        print("  span", (y[0], y[-1]) if y else None, "n", len(y))
