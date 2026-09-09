"""Splice payload.json into template.html and finish the page for GitHub Pages.

The last two steps are not optional: an Artifact-authored fragment has no
doctype and no charset, and served from Pages it lands in quirks mode with every
en dash turned to mojibake.  Regenerating the page without them silently undoes
both, which is why they live here rather than in a checklist.

    python inject.py        # -> ../index.html
"""
import io, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
TOOLS = os.path.join(os.path.dirname(os.path.dirname(PROJ)), "catalog", "tools")
TEMPLATE = os.path.join(HERE, "template.html")
PAYLOAD = os.path.join(HERE, "data", "payload.json")
OUT = os.path.join(PROJ, "index.html")


def main():
    tpl = io.open(TEMPLATE, encoding="utf-8").read()
    payload = io.open(PAYLOAD, encoding="utf-8").read().strip()
    if "__PAYLOAD__" not in tpl:
        sys.exit("template has no __PAYLOAD__ placeholder")
    # </script> anywhere inside a JSON string would close the block early
    payload = payload.replace("</", "<\\/")
    html = tpl.replace("__PAYLOAD__", payload)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    print("wrote %s (%.2f MB)" % (OUT, os.path.getsize(OUT) / 1e6))

    for tool in ("wrap_for_pages.py", "add_catalog_link.py"):
        path = os.path.join(TOOLS, tool)
        if not os.path.exists(path):
            print("  ! %s not found, skipping" % tool)
            continue
        subprocess.check_call([sys.executable, path, OUT])
        print("  ran %s" % tool)
    print("final %.2f MB" % (os.path.getsize(OUT) / 1e6))


if __name__ == "__main__":
    main()
