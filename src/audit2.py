import glob, os, sys, io
from parse_crn import parse_crn
EX = sys.argv[1]
startok = startbad = 0; endoff=[]
nolat = []
noyr = []
for p in sorted(glob.glob(os.path.join(EX, "*.crn"))):
    r = parse_crn(p)
    if not r: continue
    meta, y, v, d = r
    if not y: continue
    hy = meta["hdr_years"]
    if hy:
        if y[0]==hy[0]: startok+=1
        else: startbad+=1
        endoff.append(y[-1]-hy[1])
    else:
        noyr.append(p)
    if meta["lat"] is None: nolat.append(p)
print("start year matches header: %d   differs: %d" % (startok, startbad))
import collections
print("end-year offsets:", collections.Counter(endoff).most_common(8))
print("\n--- 6 headers missing lat/lon")
for p in nolat[:6]:
    L=io.open(p,encoding='latin-1').read().split("\n")
    print(repr(L[1][:90]))
print("\n--- 6 headers missing year field")
for p in noyr[:6]:
    L=io.open(p,encoding='latin-1').read().split("\n")
    print(repr(L[1][:90]))
