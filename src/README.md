# Narrow Year — build pipeline

Run in this order from `src/`. On the PC the interpreter is `python`, not `python3`
(`python3` resolves to the Microsoft Store alias stub, which exists but does nothing).

```bash
python fetch_chronologies.py   # 8 regional zips -> data/crn/*.crn      (~18 MB, once)
python harvest_sites.py        # NOAA study API  -> data/sites.json     (~90 requests)
python harvest_eruptions.py    # Smithsonian GVP -> data/eruptions.json
python build_corpus.py         # select + join   -> data/corpus.json
python composite.py            # pointer years   -> data/composite.json, persite.json
python build_payload.py        # pack for the page -> data/payload.json
python inject.py               # splice into ../index.html, wrap, add catalog link
node smoke.js ../index.html    # verify the built page
```

Raw downloads are gitignored — the scripts refetch them. `data/land-110m.json` is small enough
to keep, but is refetched by hand if missing:

```bash
curl -o data/land-110m.json https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-110m.json
```

## What each file is for

| file | role |
|---|---|
| `parse_crn.py` | the Tucson `.crn` reader. Every silent trap in the format is documented in its docstring — read it before touching anything else. |
| `fetch_chronologies.py` | downloads and unpacks the eight ITRDB regional zips. |
| `harvest_sites.py` | pages the NOAA study API for signed decimal site coordinates, joined to chronology files by filename. Explains why the header coordinates are unusable. |
| `harvest_eruptions.py` | Smithsonian GVP eruptions, VEI 4+, with how each date was established. |
| `build_corpus.py` | picks one total-ring-width series per site, attaches coordinates, filters. |
| `composite.py` | the pointer-year (Cropper) transform and the worldwide and regional composites. |
| `build_payload.py` | packs everything into base64 typed arrays. |
| `coastline.py` | decodes Natural Earth TopoJSON into lon/lat polylines. |
| `inject.py` | splices the payload into `template.html`, then **wraps for Pages and adds the catalog breadcrumb** — those last two steps are not optional. |
| `template.html` | the page, with a `__PAYLOAD__` placeholder. Edit this, never `../index.html`. |

## The checks

Three, and they are the reason to trust the numbers.

```bash
python audit.py data/crn      # parse rate, span agreement against each file's own header
python validate.py data/crn   # decade-floor rule; geography from the filename prefix
node smoke.js ../index.html   # runs the page's JS and recounts the composite from it
```

`smoke.js` is the important one. The composite is computed twice by two independent
implementations — numpy in `composite.py`, hand-written JavaScript in the page — and the smoke test
recounts the published series from the browser's own pointer array. It must report **0 disagreements
across 155 sampled years**. It has already earned its keep once: 32 years disagreed, and the cause
was 519 zero-or-negative index values that Python was including in window statistics and the page,
storing the payload unsigned, was not.

`validate.py` checks the two things no header can confirm on its own — that data lines are aligned
to the decade floor (99.6% of files), and that the coordinates land in the country or US state the
filename says they should (4,902 of 4,902).

## Regenerating the page after an edit

`inject.py` runs `wrap_for_pages.py` and `add_catalog_link.py` as its last two steps. If you rebuild
`index.html` any other way you will silently drop the doctype, the charset and the breadcrumb, and
the page will land in quirks mode with mojibake for every dash.
