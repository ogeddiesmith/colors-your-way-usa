#!/usr/bin/env python3
"""
Colors Your Way USA: Pexels image fetcher.

Downloads a fixed, curated set of Pexels photographs into images/, then writes
images/manifest.json (which build.py reads) and images/CREDITS.md (attribution).

    python3 fetch_images.py

Run this ONCE. It is separate from build.py on purpose: rebuilding the HTML
should never hit a third-party API or re-download 25 files. If manifest.json
already exists and every file is present, this script is a no-op unless you
pass --force.

THE PHOTO IDS BELOW ARE PINNED. They are not a live search. A live search would
return different photos on every run and silently change the site. Each ID was
reviewed for relevance to a painting and remodeling contractor before pinning.

EVERY IMAGE HERE IS STOCK. None of it is Mike Walsh's work. See the warning in
CREDITS.md and the PREVIEW banner that build.py renders on every page.

Requires PEXELS_API_KEY in /Users/macminimain/Desktop/simply-digital-mcp/.env
(Unsplash is dead. Do not add it back.)
"""
import io, json, os, re, sys, urllib.request, urllib.parse

ENV_PATH = "/Users/macminimain/Desktop/simply-digital-mcp/.env"
HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, "images")

# Pexels rejects the default urllib User-Agent with HTTP 403. This is not
# optional and it is not a key problem. Do not remove it.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# key, pexels photo id, size ("large2x" ~1880w for heroes, "large" ~940w for the rest),
# our own alt text (written for screen readers, not copied from Pexels)
PHOTOS = [
    # ---- page heroes -------------------------------------------------------
    ("hero-home",         36153946, "large2x", "Two painters in work clothes rolling fresh paint onto the walls of a room being redecorated"),
    ("hero-interior",      4981809, "large2x", "A painter in protective coveralls rolling paint onto an interior wall"),
    ("hero-exterior",      1917849, "large2x", "A painter on a ladder rolling paint onto the outside wall of a house"),
    ("hero-cabinets",     15124970, "large2x", "A kitchen mid renovation with the cabinet doors off, tools and materials on the floor"),
    ("hero-drywall",      11427055, "large2x", "A gloved hand smoothing joint compound onto a wall with a taping knife"),
    ("hero-remodeling",   29181494, "large2x", "A tradesman kneeling to set floor tile on a renovation job"),
    ("hero-service-area",  5353883, "large2x", "A two story suburban house with a driveway and front lawn"),
    ("hero-contact",       5292188, "large2x", "A person comparing paint color cards side by side to choose a shade"),
    ("hero-blog",          5641407, "large2x", "Brushes, rollers and paint cans laid out on a bench before a job starts"),

    # ---- before and after pairs (STOCK PLACEHOLDERS, see CREDITS.md) -------
    ("ba1-before",         3616762, "large",   "An interior wall stripped back to patched plaster before any finish coat"),
    ("ba1-after",         35493905, "large",   "An empty room with clean painted walls and hardwood floor lit by a window"),
    ("ba2-before",         6156592, "large",   "Aged wood siding on a house with white paint peeling away from the boards"),
    ("ba2-after",          6422929, "large",   "A two story house with clean painted siding, a front porch and an attached garage"),
    ("ba3-before",        36035073, "large",   "A kitchen under renovation with a stepladder and tools where the cabinets are being worked on"),
    ("ba3-after",          7535073, "large",   "A finished kitchen with white cabinet doors and countertops back in place"),
    ("ba4-before",        36035072, "large",   "A bathroom stripped for renovation with tile, tools and materials on the floor"),
    ("ba4-after",          7168080, "large",   "A finished bathroom with white and blue wall tile and new fixtures"),

    # ---- supporting images -------------------------------------------------
    ("prep-tape",          7217961, "large",   "Painter's tape and drop cloths going down to mask a room before painting starts"),
    ("roller-closeup",     5583116, "large",   "A close view of a roller laying an even coat of paint across a wall"),
    ("swatches",              5933, "large",   "A fan of paint color swatches spread out to compare shades"),
    ("tools-floor",        3615716, "large",   "Hand tools laid out on a tiled floor at the start of a renovation"),
    ("exterior-trim",      8071917, "large",   "House trim, window casing and shutters picked out in a contrasting color"),
    ("living-room",        8146336, "large",   "An empty living room with freshly finished walls and large windows"),
    ("spray-finish",       6474305, "large",   "A painter spraying an even finish coat onto an interior surface"),
    ("deck",              10450058, "large",   "A wooden deck behind a house with the boards showing their grain"),
]


def load_key():
    """Read PEXELS_API_KEY. Line-based, not `cut -d= -f2`, so trailing = in a
    base64-ish value survives."""
    txt = io.open(ENV_PATH, encoding="utf-8").read()
    m = re.search(r"^PEXELS_API_KEY=(.*)$", txt, re.M)
    if not m:
        sys.exit("PEXELS_API_KEY not found in " + ENV_PATH)
    return m.group(1).strip().strip('"').strip("'")


def api(url, key):
    req = urllib.request.Request(url, headers={
        "Authorization": key, "User-Agent": UA, "Accept": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=45))


def jpeg_size(path):
    """Read width and height straight out of the JPEG SOF marker.

    Explicit width and height on every <img> is what stops the page reflowing as
    photos load. Doing it from the real file means the numbers cannot drift from
    the bytes. Avoids a Pillow dependency for twenty lines of work.
    """
    with io.open(path, "rb") as f:
        data = f.read()
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seglen = (data[i + 2] << 8) + data[i + 3]
        # SOF0..SOF15, skipping the non-frame markers DHT/JPG/DAC
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h = (data[i + 5] << 8) + data[i + 6]
            w = (data[i + 7] << 8) + data[i + 8]
            return w, h
        i += 2 + seglen
    return 0, 0


def main():
    force = "--force" in sys.argv
    key = load_key()
    if not os.path.isdir(IMG_DIR):
        os.makedirs(IMG_DIR)

    manifest = {}
    for name, pid, size, alt in PHOTOS:
        fn = name + ".jpg"
        dest = os.path.join(IMG_DIR, fn)
        meta = api("https://api.pexels.com/v1/photos/%d" % pid, key)
        src = meta["src"].get(size) or meta["src"]["large"]
        if force or not os.path.exists(dest):
            req = urllib.request.Request(src, headers={"User-Agent": UA})
            blob = urllib.request.urlopen(req, timeout=60).read()
            io.open(dest, "wb").write(blob)
            print("  downloaded %-20s %7d bytes" % (fn, len(blob)))
        else:
            print("  kept       %-20s" % fn)
        w, h = jpeg_size(dest)
        manifest[name] = {
            "file": fn, "alt": alt, "w": w, "h": h,
            "pexels_id": pid,
            "pexels_url": meta.get("url", ""),
            "photographer": meta.get("photographer", ""),
            "photographer_url": meta.get("photographer_url", ""),
            "bytes": os.path.getsize(dest),
            "stock": True,
        }

    io.open(os.path.join(IMG_DIR, "manifest.json"), "w", encoding="utf-8").write(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n")

    lines = [
        "# Photo credits and the swap-out list",
        "",
        "Generated by `fetch_images.py`. Do not hand-edit.",
        "",
        "## Read this first",
        "",
        "**Every photograph in this folder is stock. None of it is Mike Walsh's work, none of it is a",
        "Colors Your Way USA job, and none of the before and after pairs are the same room.** They are",
        "placeholders that let the layout be finished and reviewed. The site marks them as placeholders",
        "on the page while it is in preview.",
        "",
        "**Replacing these with Mike's own job photos is the single biggest quality lever on this site.**",
        "Both the SEO research and the competitor research reached that conclusion independently. Real",
        "before and after pairs from Bridgeview, Oak Lawn and Burbank jobs will convert better than any",
        "wording change we could make, and they are also what the Google Business Profile needs.",
        "",
        "What to ask Mike for, in priority order:",
        "",
        "1. Before and after pairs of the SAME room or the SAME elevation, shot from the same spot.",
        "2. Kitchen cabinet jobs. Highest margin work and the most persuasive single photo in the trade.",
        "3. Exteriors, whole house, taken from the street.",
        "4. Prep and repair shots: patched drywall, stripped trim, replaced subfloor. These prove the work",
        "   nobody else photographs.",
        "5. One clear photo of the van, and one of Mike. The owner-does-the-work claim is his strongest",
        "   and no franchise can copy it.",
        "",
        "## License",
        "",
        "All images below are from Pexels and used under the Pexels License",
        "(https://www.pexels.com/license/), which permits free commercial use without attribution.",
        "Attribution is recorded here anyway so the source of every file on this site is traceable.",
        "",
        "## Files",
        "",
        "| File | Photographer | Pexels page | Size |",
        "|---|---|---|---|",
    ]
    for name in sorted(manifest):
        m = manifest[name]
        lines.append("| `%s` | %s | %s | %d x %d |" % (
            m["file"], m["photographer"], m["pexels_url"], m["w"], m["h"]))
    lines += ["", "## Where each one is used", "",
              "| File | Role |", "|---|---|"]
    roles = {
        "hero-": "Page hero.",
        "ba1-": "Before and after pair 1 (interior room). PLACEHOLDER, not one room.",
        "ba2-": "Before and after pair 2 (exterior siding). PLACEHOLDER, not one house.",
        "ba3-": "Before and after pair 3 (kitchen cabinets). PLACEHOLDER, not one kitchen.",
        "ba4-": "Before and after pair 4 (bathroom and tile). PLACEHOLDER, not one bathroom.",
    }
    for name in sorted(manifest):
        role = "Supporting image."
        for pref, txt in roles.items():
            if name.startswith(pref):
                role = txt
                if pref == "hero-":
                    role = "Hero image for the " + name[5:].replace("-", " ") + " page."
                break
        lines.append("| `%s` | %s |" % (manifest[name]["file"], role))

    # The blog posts carry their own hero and in-body photos in blog/images/,
    # downloaded by the content side with their own manifest. Fold them into this
    # file so there is ONE place that accounts for every photograph on the site.
    blogc = os.path.join(HERE, "blog", "images", "_credits.json")
    if os.path.exists(blogc):
        try:
            rows = json.load(io.open(blogc, encoding="utf-8"))
        except Exception as e:
            rows = []
            print("  WARNING: could not read blog/images/_credits.json: %s" % e)
        if rows:
            lines += ["", "## Blog post photos (`blog/images/`)", "",
                      "Downloaded by the content side, credited here so this file covers every",
                      "photograph on the site. Same Pexels License, same stock caveat: none of",
                      "these are " + "Mike Walsh" + "'s jobs.", "",
                      "| File | Photographer | Pexels page |", "|---|---|---|"]
            for r in rows:
                lines.append("| `blog/images/%s` | %s | %s |" % (
                    r.get("file", ""), r.get("photographer", ""), r.get("pexels_page", "")))
    else:
        lines += ["", "## Blog post photos", "",
                  "`blog/images/_credits.json` was not present when this file was generated, so",
                  "no blog photos are listed. Re-run `python3 fetch_images.py` after the blog",
                  "images land to pick them up."]

    lines.append("")
    io.open(os.path.join(IMG_DIR, "CREDITS.md"), "w", encoding="utf-8").write("\n".join(lines))

    total = sum(m["bytes"] for m in manifest.values())
    print("\n%d images, %.1f MB total" % (len(manifest), total / 1048576.0))
    print("wrote images/manifest.json and images/CREDITS.md")


if __name__ == "__main__":
    main()
