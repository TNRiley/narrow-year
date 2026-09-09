"""Decode Natural Earth 110m land (TopoJSON) into plain lon/lat polylines.

TopoJSON stores each arc as quantised integer deltas plus a shared affine
transform, so the arcs have to be cumulatively summed before the transform is
applied -- decode them as absolute coordinates and the whole world collapses
into a smear near the antimeridian.
"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "land-110m.json")


def arcs(path=SRC, keep=6):
    topo = json.load(io.open(path, encoding="utf-8"))
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    out = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((round(x * sx + tx, 3), round(y * sy + ty, 3)))
        if len(pts) >= 2:
            out.append(pts)
    return out


if __name__ == "__main__":
    a = arcs()
    n = sum(len(p) for p in a)
    xs = [p[0] for arc in a for p in arc]
    ys = [p[1] for arc in a for p in arc]
    print("arcs %d  points %d" % (len(a), n))
    print("lon %.2f..%.2f   lat %.2f..%.2f" % (min(xs), max(xs), min(ys), max(ys)))
