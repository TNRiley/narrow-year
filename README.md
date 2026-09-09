# 🪵 Narrow Year

**2,474 tree-ring chronologies asked which years the world's trees all had a bad time at once — and whether those were the years the history books would predict.**

→ **[Open it](https://tnriley.github.io/narrow-year/)**

A tree ring is a date, because trees hundreds of miles apart put down the same pattern of fat and starved years. This draws real chronologies from the International Tree-Ring Data Bank as cross-sections you can read ring by ring, gives you the crossdating instrument itself — slide one site against another and watch the correlation lock at the true offset — and then pools all 2,474 sites into one series: the share of the world's trees that recorded an unusually narrow ring each year from 925 to 2006, with the wide-year share carried underneath as a control. The result is a null. Across the 42 largest eruptions whose dates come from someone writing them down at the time, the narrow share lifts by 1.3 points, from 8.9% to 10.1%; 1816, the year without a summer, comes in below average narrow worldwide. The explanation is about the archive rather than about trees: 1,167 of the 2,474 sites stand in western North America, where 1816 was a superb growing season — 1.4% of sites narrow against 32.7% wide — so the one region that did record it, eastern North America at 13.9% narrow, is averaged into silence. Samalas in 1257 is the counter-example that proves the method works, reaching 36.6% narrow against 2.4% wide in the western sites the year after it erupted.

## Running it

One self-contained HTML file. No build step, no server, no network access at runtime — open `index.html` in a browser, or serve the directory with any static host.

```bash
python3 -m http.server 8000   # then visit http://localhost:8000
```

## Rebuilding it from scratch

[REBUILD.md](REBUILD.md) is written for an LLM with a shell and nothing else: the data sources and their quirks, the processing decisions, the page's structure and interactions, and a table of expected values to check the result against.

## Source

The full build pipeline is in [`src/`](src/), with a README describing how to regenerate the page from scratch.

## Data

- **[International Tree-Ring Data Bank site chronologies (ITRDB v7.13), NOAA Paleoclimatology](https://www.ncei.noaa.gov/pub/data/paleo/treering/chronologies/)** — US Government public domain; cite the original contributor of each chronology
- **[NOAA Paleoclimatology study metadata (site coordinates and species)](https://www.ncei.noaa.gov/access/paleo-search/study/search.json)** — US Government public domain
- **[Global Volcanism Program, Holocene eruption catalogue, Smithsonian Institution](https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows)** — cited, not redistributed in bulk
- **[Natural Earth 110m land outline (via world-atlas)](https://www.naturalearthdata.com)** — public domain

Every figure on the page is computed from the data shipped with it. Check the page's own methods panel for how each number is derived and where it should not be pushed.

## Built with

vanilla JS, canvas, typed-array payload, numpy.

## Licence

Code is MIT (see [LICENSE](LICENSE)). Data keeps the licence of its source, listed above.

---

Part of [Quick Projects](https://github.com/TNRiley/quick-projects) — one self-contained thing, built in one session. First published 2026-09-08.
