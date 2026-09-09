import glob, os, sys, collections
from parse_crn import parse_crn
EX = sys.argv[1]
files = sorted(glob.glob(os.path.join(EX, "*.crn")))
ok = bad = nodata = 0
noyear = nolatlon = 0
fails = []
spanmatch = 0
for p in files:
    try:
        r = parse_crn(p)
    except Exception as e:
        fails.append((os.path.basename(p), repr(e))); bad += 1; continue
    if r is None:
        bad += 1; continue
    meta, y, v, d = r
    if not y:
        nodata += 1; continue
    ok += 1
    hy = meta["hdr_years"]
    if hy is None: noyear += 1
    elif (y[0], y[-1]) == hy: spanmatch += 1
    else: fails.append((meta["file"], "span %s vs hdr %s" % ((y[0], y[-1]), hy)))
    if meta["lat"] is None: nolatlon += 1
print("files      %6d" % len(files))
print("parsed     %6d" % ok)
print("empty      %6d" % nodata)
print("errored    %6d" % bad)
print("no hdr yrs %6d" % noyear)
print("span match %6d  (%.1f%% of those with header years)" % (spanmatch, 100*spanmatch/max(1,ok-noyear)))
print("no lat/lon %6d  (%.1f%%)" % (nolatlon, 100*nolatlon/max(1,ok)))
print("\nfirst 15 mismatches:")
for f in fails[:15]: print("  ", f)
