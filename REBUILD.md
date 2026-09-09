# Rebuilding Narrow Year

Enough to reproduce the project from an empty directory, a shell and no other context.

---

## 1. What is being built

A single self-contained HTML page over the **International Tree-Ring Data Bank**. It does three
things:

1. **Draws real chronologies.** A site's standardised ring-width index rendered as a cross-section
   (concentric annuli at true relative widths, latewood band on the outer edge of each ring) and as a
   magnified linear core strip.
2. **Gives you crossdating.** Two sites as skeleton plots; drag one and a correlation-versus-offset
   curve spikes at the true alignment. This is the actual method by which wood is dated, and the
   spike is the argument.
3. **Pools all 2,474 sites into one series** — the share of sites recording an unusually narrow ring
   each year, 925–2006 — and tests it against the largest documented volcanic eruptions.

**The finding it exists to show is a null and its explanation.** Across the 42 eruptions of VEI 5 or
greater whose dates come from contemporary written record, the narrow share lifts from a baseline of
8.9% to 10.1% at lag +1 — 1.3 percentage points. 1816, the year without a summer, is *below* average
narrow worldwide (5.7% narrow, 22.9% wide).

The reason is sampling, not biology: **1,167 of 2,474 sites are in western North America**, where
1816 was an excellent growing season (1.4% narrow, 32.7% wide, n=1006), because the circulation that
froze New England arrived over the interior west as cloud and rain. Eastern North America — where the
year earned its name — is the only region that goes narrow (13.9% narrow, 4.5% wide, n=330), and it
is outvoted three to one. Samalas (1257) is the counter-example that shows the method works at all:
36.6% narrow against 2.4% wide in western North America the following year.

---

## 2. Data

### ITRDB chronologies

Eight regional zips, ~18 MB total, far kinder than the 8,000-file directory listing:

```
https://www.ncei.noaa.gov/pub/data/paleo/treering/chronologies/itrdb-v713-<region>-crn.zip
  region in {africa, asia, australia, canada, europe, mexico, southamerica, usa}
```

Unpacks to **8,293 `.crn` files** in the Tucson chronology format. Values are dimensionless indices
scaled so the site's own mean year is 1000, each paired with the number of contributing cores.

### Site coordinates

**Do not read coordinates out of the `.crn` headers.** See the traps below. Page the NOAA
Paleoclimatology study API instead, which publishes signed decimal coordinates and names the exact
chronology files each site produced, so it joins on filename:

```
https://www.ncei.noaa.gov/access/paleo-search/study/search.json
  ?dataPublisher=NOAA&dataTypeId=18&limit=100&skip=<n>
```

9,022 studies, ~90 requests, yields 14,363 chronology filenames with coordinates. 6,452 of the 8,293
local files join; the shortfall is almost entirely parameter variants that get dropped anyway.

### Eruptions

Smithsonian Global Volcanism Program, WFS:

```
https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows
  ?service=WFS&version=2.0.0&request=GetFeature
  &typeName=GVP-VOTW:Smithsonian_VOTW_Holocene_Eruptions&outputFormat=application/json
  &CQL_FILTER=ExplosivityIndexMax >= 4 AND StartDateYear >= 0 AND Activity_Type = 'Confirmed Eruption'
```

399 eruptions VEI 4+ since year 0. **`StartEvidenceMethod` is the field that matters.** Only
`Observations: Reported` — a date somebody wrote down at the time — is used for the test.

Note GVP records the *onset* of an eruptive episode: Tambora is filed under 1812, not the 1815
climax. Test a window of lags rather than a single year, and say which year you are quoting.

### Coastline

`https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-110m.json`, Natural Earth 110m as TopoJSON.
Arcs are delta-encoded and must be cumulatively summed before the affine transform is applied.

---

## 3. Traps

Every one of these fails **silently**. None raises.

### The decade-floor rule

The ten values on a data line are aligned to the **decade floor of the line's year label**, not to
the label. A first line labelled 1422 carries 1420-1429, with 1420 and 1421 present as `9990`/depth-0
padding. Read them as 1422-1431 and every series shifts by up to nine years.

*Verification:* on a first data line, `label - 10*floor(label/10)` must equal the number of leading
no-data slots. **Holds for 8,166 of 8,201 files (99.6%).**

### Coordinates: the hyphen is ambiguous

Degrees and minutes run together with no separator and no consistent width — `6026` is 60d26',
`05445` is 54d45', `535` is 5d35'. Worse, the separating hyphen means different things in different
dialects:

| header | correct reading |
|---|---|
| `275M 06026-14745` (Alaska) | 60.43 N, **-147.75** — hyphen is a minus sign |
| `Norway spruce 1370  4636-804` (Switzerland) | 46.60 N, **+8.07** — hyphen is a separator |

Nothing in the line distinguishes them. Treat it as a sign and every European site flips into the
Atlantic; treat it as a separator and every American site flips into the Pacific. About a third of
the corpus is wrong either way. **This is why the coordinates come from the API.** A header parser
that scores candidate pairs by separator width reaches 95% but is not worth trusting.

There is a second, subtler version of this. A regex with two capture groups never sees the correct
pair in `White Spruce 750  6340-14935`, because `finditer` has already consumed `6340` inside the
match `750  6340`; it returns the *elevation* as a latitude and puts Denali in the Gulf of Guinea.
Enumerate numeric tokens and consider every adjacent pair. And a "not preceded by a digit" guard
must apply only to the unsigned branch, or it rejects `-14745`, rematches it as `14745`, and flips
every western longitude east.

*Verification:* the filename prefix encodes a US state or country independently of the header.
API coordinates fall inside the expected box for **4,902 of 4,902** checkable files.

### Four chronologies stacked in one file

3,205 files contain **four** chronologies end to end, each introduced by its own header line 1: raw
mean ring width, then standard, residual and ARSTAN indices. Read the file as one series and every
year appears four times. Take the first block and you get raw widths in hundredths of a millimetre,
age trend still in them, where an index was wanted.

*The rule that works:* take the first block whose values average 900-1100. An index averages 1000 by
construction; a raw block does not (median site mean 761, IQR 311-2091, only 5% inside 900-1100).

### Decade labels 10, 20, 30 read as header tags

Header lines are tagged `1`, `2`, `3` in columns 7-9. A chronology reaching back before year 40
writes decade labels `10`, `20`, `30`, which right-align into *exactly* those columns. Classify lines
by the tag and those three decades are discarded — and, because the block splitter uses the same
test, the series is also cut in two at year 10. Eight bristlecone chronologies, the oldest records in
the bank, all claimed to start in year 40. Sheep Mountain (`ca534`) reported 1,950 rings from year 40
instead of 1,991 from year 0.

*The rule that works:* a data line is a year in columns 7-10 followed by nothing but digits, spaces
and minus signs **in the 70-character value field only** — one dialect ends every data line with a
trailing `  RAW`, so a no-letters test over the whole line rejects all 3,205 Schweingruber files
instead.

### Suffixes are a convention, not a spec

`e` earlywood width, `l` latewood width, `n` minimum density, `x` maximum density, `i` earlywood
density, `t` latewood density, `p` latewood percent. But **two sites have their `w` and `x` files
swapped**, and for the `_crns` family it is `w`, not the bare name, that carries ring width. Header
line 1 states the parameter as a word (`WIDTH_RING`, `DENSITY_MAXIMUM`, ...). Read that. Files with
no parameter word are ring width, but only for the standard/residual/ARSTAN variants; an unlabelled
file with an `e` or `l` suffix is earlywood or latewood.

### CR-only line endings

36% of the corpus (2,973 files) uses classic Mac `\r` line endings. Python's text mode handles it;
splitting raw bytes on `\n` does not, and yields one 16 KB "line" that parses to a plausible-looking
span rather than an error.

### Non-positive index values

519 year-values across 25 sites are zero or negative (`nm580` has -19 at year 1005, written as
` -19 13` in the file). An index is a ratio to the site's own mean growth and cannot be either. Drop
them. **This one was caught by the JS/Python cross-check, not by inspection** — the browser stored
the payload unsigned and so excluded them, while the Python included them in window statistics, and
the two composites disagreed on 32 of 155 sampled years.

### Circularity in the eruption comparison

Ice-core volcanic chronologies were themselves synchronised against tree-ring marker years, and GVP
dates two St Helens eruptions (1480, 1482) by `Sidereal: Dendrochronology` outright. Testing tree
rings against those is marking your own homework. Use documentary dates only for the statistic; show
the rest labelled with how they were dated.

---

## 4. Method

Site chronologies already have the age trend divided out but still drift on decadal scales, so an
absolute threshold would flag whole cool centuries rather than shock years. Apply the **pointer-year
(Cropper) transform**: rescale each ring against a 13-year window centred on it,

```
C_t = (x_t - mean(window)) / sd(window)      ddof = 1, at least 11 valid values required
```

`C <= -1.28` (the 10th percentile of a normal) counts the year narrow for that site; `C >= +1.28`
counts it wide. A site-year needs **at least 5 cores**; a year is reported only where **at least 50
sites** are available.

Use **two-pass** variance. The one-pass form `sum(x^2) - n*mean^2` subtracts two quantities of order
n*10^6 to leave one of order n*10^4, and the precision lost is enough to move a ring across the
threshold.

The **wide share is a control**, the identical pipeline with one sign flipped. Anything that inflates
the narrow count by accident should inflate both. Across the record they sit at 8.9% and 8.5%,
against the 10% each the threshold implies — that near-symmetry is the main evidence the arithmetic
is doing what it claims.

Selection: one series per site, preferring standard, then `w_crns`, then residual, then ARSTAN.
Reject floating chronologies (`y1 > 2026`, descending years, or "floating" in the site name),
repeated years, and files stacking more than four blocks — those are individual timbers from one
excavation, not a site chronology.

---

## 5. Verification table

Rebuild is correct if these come out:

| quantity | value |
|---|---|
| `.crn` files unpacked | 8,293 |
| parsed with no error | 8,203 |
| span matches header years | 95.5% |
| decade-floor rule holds | 8,166 / 8,201 (99.6%) |
| API coordinates inside filename-implied box | 4,902 / 4,902 (100%) |
| sites kept (ring width, dated, with coordinates) | 2,474 |
| site-years in payload | 973,881 |
| composite window | 925-2006 (1,082 years) |
| mean narrow share / mean wide share | 8.88% / 8.49% |
| median narrow share | 7.43% |
| Sheep Mountain `ca534` span | 0-1990, 1,991 rings |
| longest chronology `nm615` El Malpais | 1,964 years |

Named years — narrow share, wide share, sites available:

| year | narrow | wide | sites | note |
|---|---|---|---|---|
| 1217 | 39.5% | 2.8% | 109 | narrowest year in the record |
| 1258 | 27.7% | 7.6% | 119 | year after Samalas (Rinjani), VEI 7 |
| 1601 | 15.3% | 4.0% | 577 | year after Huaynaputina, VEI 6 |
| 1816 | **5.7%** | **22.9%** | 1,810 | the year without a summer |
| 1912 | 6.9% | 6.2% | 2,225 | Novarupta, VEI 6 |

Regional split, share narrow / share wide:

| region | sites | 1258 | 1601 | 1816 |
|---|---|---|---|---|
| western North America | 1,167 | 36.6 / 2.4 (n=82) | 17.8 / 3.0 (n=398) | 1.4 / 32.7 (n=1006) |
| eastern North America | 429 | 0.0 / 21.1 (n=19) | 4.0 / 4.0 (n=50) | 13.9 / 4.5 (n=330) |
| Europe | 391 | too few sites | 28.2 / 7.7 (n=39) | 8.1 / 10.5 (n=210) |
| northern Asia | 49 | too few sites | too few sites | 11.9 / 9.5 (n=42) |
| southern hemisphere | 181 | too few sites | 0.0 / 11.5 (n=52) | 10.6 / 17.9 (n=151) |

Eruption test, documentary VEI 5+, n=42 in window: lag 0 **9.15%**, lag +1 **10.14%**, lag +2
**8.77%**, against an 8.88% baseline.

A useful sanity check that catches normalisation bugs: mean index relative to each site's own
long-run mean, averaged over 1700-1900, comes out at 0.99 for every region.

---

## 6. The page

Warm cut-stump palette (cream paper, heartwood brown ink, rust for narrow years, sea-green for wide,
gold for eruptions), full light and dark support. Fraunces for display, Newsreader for running text,
IBM Plex Sans Condensed and Mono for interface and figures. Six sections: the ring, crossdating, the
composite, one year on a world map, the regional split, method and limits.

Payload is base64 typed arrays — Int16 values, Uint8 depths, on a contiguous year grid per site with
0 marking a year the chronology does not cover (an index is never 0, so the sentinel is
unambiguous). About 4.3 MB built.

Two rendering details worth keeping. On the cross-section, draw each ring as an arc *stroke* of
width `dr` rather than filling nested circles — 2,000 filled discs is far slower for the same
picture — and only draw the latewood band when `dr` exceeds about 1.6 px, below which it is noise.
On the map, break the coastline polyline wherever consecutive longitudes differ by more than 180
degrees: seven arcs in Natural Earth 110m cross the antimeridian, and on an equirectangular
projection each is otherwise drawn as a straight line back across the entire map.

Pointer values are recomputed in the browser rather than shipped. **Cross-check them against the
Python** — `node src/smoke.js index.html` runs every script block under a stub DOM and recounts the
composite from the JS pointer array. It must report 0 disagreements. That check is what found the
negative-index bug. Note that top-level `const` in a `vm` context lives in the context's global
lexical scope and is not reachable as a property of the sandbox object; pull the bindings out by
evaluating an expression inside the context.

---

## 7. What the page must say about itself

- The bank is **not a sample of the world's trees**: overwhelmingly Northern Hemisphere, half of it
  western North American, collected mostly in the 1980s and 1990s. Replication collapses after about
  1990 — around 2,400 sites in 1950, 503 by 2000, one by 2015. Any trend at the right-hand edge is a
  collecting artefact until proven otherwise.
- Chronologies were built by hundreds of investigators using different standardisation choices.
  Pooling them assumes those choices do not bias the sign of a single-year departure. That is a
  reasonable assumption and not a tested one.
- A narrow ring is **not a thermometer**. It records a poor season for that tree — which may be cold,
  or drought, or insects, or fire, or a neighbour falling over.
- The early part of the composite rests on 50 to 120 sites. The top of the "narrowest years" table is
  drawn disproportionately from those thin years, and that is a property of the sample size as much
  as of the climate.
