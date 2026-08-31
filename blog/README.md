# Blog contract for `build.py`

Six posts plus an index, written as plain markdown with YAML front matter. Nothing here is
hand-edited HTML. This file tells the site generator exactly what it is being handed.

---

## READ FIRST: one open integration gap

`build.py` as it stands on 2026-08-31 **discovers `blog/*.html`, not `blog/*.md`.** Its
`discover_posts()` lists the folder, skips anything that is not `.html`, and scrapes `<title>`,
`<meta name="description">` and a date out of each file to build the index. It has no markdown
parser and no front matter parser.

These six posts are markdown, because that is what they were commissioned as. **So today they are
invisible to the build.** Nothing is broken and nothing was overwritten. There is simply one step
missing between the two halves.

**The fix, and it belongs in `build.py`, not in these files.** Add a `render_markdown_posts()` step
that runs before `discover_posts()`:

1. Read each `blog/*.md`, split the YAML front matter from the body.
2. Convert the body with a markdown library configured for `tables` and raw HTML pass-through. With
   `python-markdown`, `markdown.markdown(body, extensions=["tables"])` is enough. Do not enable safe
   mode. Every post contains inline `<svg>` and `<figure>` blocks that must pass through untouched.
   A local render was verified: 3 to 6 `<table>` elements per post, 1 `<svg>` per post, 0 escaped.
3. Wrap the result in the site's own `head()`, `header()` and `footer()` with `up="../"`, so posts
   inherit the existing chrome, nav, phone bar and noindex meta rather than carrying their own.
   Use the front matter `title` for the `<title>` (the pattern `{title} | Colors Your Way USA` is
   what `discover_posts()` already strips), `description` for the meta description, and emit
   `<time datetime="{date}">` so the index sorts.
4. Write `blog/{slug}.html`. `discover_posts()` then picks them up with no further change.

Sort the index on the front matter `order` key (1 to 6), not on `date`. All six share the date
`2026-08-31` because they were written in one batch, so a date sort produces an arbitrary order.

Everything below describes what the markdown guarantees, so that step can be written against a
stable contract.

---

## Files

```
site/blog/
  index.md                                              blog index page
  interior-painting-cost-southwest-chicago-suburbs.md   order 1
  how-to-tell-good-prep-from-a-fast-cheap-job.md        order 2
  best-time-to-paint-house-exterior-chicago.md          order 3
  cabinet-refinishing-vs-replacing.md                   order 4
  choosing-paint-colors-older-southwest-suburb-homes.md order 5
  rental-turnover-painting-southwest-suburbs.md         order 6
  images/                                               14 Pexels JPGs, 1600px wide, 2.5 MB total
  images/CREDITS.md                                     human-readable photo credits
  images/_credits.json                                  machine-readable, same data
```

## Front matter schema

Every post carries these keys. All strings, except `keywords`, `related` and the `hero` map.

| Key | Type | Notes |
|---|---|---|
| `title` | string | Page `<h1>` and the `<title>` stem |
| `slug` | string | URL segment. Renders at `/blog/{slug}/` |
| `description` | string | `<meta name="description">`. Under 160 characters where possible. Phone number included on posts where it fits, per the SEO spec |
| `date` | string | ISO date. All six are `2026-08-31`, the date they were written |
| `order` | int | Display order on the index, 1 to 6. Use this, not `date`, for sorting |
| `category` | string | Interior painting, Exterior painting, Cabinets, Color, Rental and maintenance |
| `keywords` | list | Target queries. Not for a meta keywords tag, which is dead. Use for internal reference and for the index page grouping |
| `service_page` | string | Relative path to the pillar page this post supports, e.g. `../interior-painting.html`. Emit a link to it in any related-content block |
| `related` | list | Sibling post filenames, e.g. `cabinet-refinishing-vs-replacing.html`, relative to `blog/`. Already linked inline in the body as well |
| `hero` | map | `src`, `alt`, `width`, `height`, `credit`, `credit_url` |
| `stock_photos` | bool | `true` on all six today. Flip to `false` per post when Mike's real photos replace the stock |
| `noindex` | bool | `true` on all six. See below |

The index page uses the same schema plus `type: "index"` and a `posts:` list of slugs in display
order.

## Title tag pattern

Per `launch/08-SEO-AND-KEYWORD-RESEARCH.md`, always pair the brand with a location, because the brand
name alone is not distinctive. Suggested pattern for blog posts:

```
{title} | Colors Your Way USA, Bridgeview IL
```

Truncate the title stem, not the brand and location.

## Rendering requirements

**Markdown extensions needed:** tables, and raw HTML pass-through. Every post contains one inline
`<svg>` chart or diagram inside a `<figure class="chart">`, and one or two `<figure><img></figure>`
blocks. If the markdown renderer escapes raw HTML, these posts render as visible source code. With
python-markdown, enable `tables` and do not enable `safe_mode`. With `markdown-it-py`, set
`html=True`.

**Charts.** All charts are hand-written inline SVG. They are self-contained, use `viewBox` with
`style="width:100%;max-width:720px;height:auto"` so they scale, and use `fill="currentColor"` for
text so they work on a light or dark background. Each one carries `role="img"` plus `<title>` and
`<desc>` referenced by `aria-labelledby`, and every chart is duplicated as a markdown table nearby so
the data survives even if the SVG is stripped. No chart library, no external requests.

**Chart palette** (matches the van: blue, green, red):

| Use | Hex |
|---|---|
| Primary series | `#1f5fa9` blue |
| Positive or "good window" | `#2e7d4f` green |
| Warning, reference line, failure | `#c0392b` red |
| Neutral or inactive | `#9aa3ad` |
| Substrate in the prep diagram | `#b9a789` |

Red and green are never used to encode two categories in the same chart, because that pairing fails
for red-green color blindness. Where two series appear together they are blue and red, and every bar
is directly labeled with its value.

**Images.** All 14 are in `images/`, 1600px wide, already compressed, 2.5 MB total. Emit explicit
`width` and `height` (they are in the front matter and in the inline `<img>` tags) and
`loading="lazy"` on everything below the fold. The hero should not be lazy loaded. Note this is a
second, separate image folder from `site/images/`, which `build.py` owns. Neither touches the other.

**Encoding.** Read and write these files as UTF-8. One photographer credits under the name
`DΛVΞ GΛRCIΛ`, which uses Greek capitals. That is the correct spelling of their Pexels name, so it is
kept as-is. Everything else in every file is plain ASCII, verified: no em dashes, no en dashes, no
smart quotes, no non-breaking spaces.

**Internal links are relative, and that is deliberate.** The site is served from a GitHub Pages
subpath (`https://ogeddiesmith.github.io/colors-your-way-usa/`), so a root-absolute link like
`/interior-painting.html` resolves to the wrong host root and 404s. Every link in these posts is
written relative to `blog/`:

- Sibling posts: `cabinet-refinishing-vs-replacing.html` (same folder)
- Service pages: `../interior-painting.html` (parent folder), matching the `up="../"` convention
  `build.py` already uses in `header()` and `head()`
- Images: `images/interior-cost-hero.jpg` (resolves to `blog/images/`)

If the site later moves to its own domain at the root, or switches to directory-style URLs, change it
in one place in `build.py`, not by editing seven markdown files.

## Pages these posts link to

Checked against `sitemap.xml` as emitted by `build.py` on 2026-08-31. Every link in every post now
resolves to a page that exists.

| Canonical path in the SEO plan | Page `build.py` emits | Linked from | Status |
|---|---|---|---|
| `/interior-painting/` (B1) | `interior-painting.html` | posts 1, 2, 4, 5, 6 | Live |
| `/exterior-painting/` (B2) | `exterior-painting.html` | posts 3, 5 | Live |
| `/cabinet-painting/` (B3) | `cabinet-refinishing.html` | post 4 | Live, different filename |
| `/drywall-repair-and-painting/` (B4) | `drywall-and-repair.html` | posts 1, 2, 6 | Live, different filename |
| `/deck-and-fence-staining/` (B5) | not built | none, see below | **Missing** |
| `/painting-cost-southwest-suburbs/` (B14) | not built | none, see below | **Missing** |
| `/rental-turnover-painting/` (B7) | not built | none, see below | **Missing** |

**Three pages the SEO plan calls for are not in the build, and each one is a real gap, not a
nitpick.** The posts were rewritten to route around them so nothing ships dead, but the routing is a
workaround:

1. **`/painting-cost-southwest-suburbs/` (B14)** is described in the SEO research as "the single
   highest-leverage page on the site." A pricing question appeared in People Also Ask on nine of the
   ten queries tested, and none of the twelve competitors reviewed publishes prices. Post 1 is the
   cluster content for that page and currently has no pillar to point at. Build it, then add the link
   back into post 1.
2. **`/rental-turnover-painting/` (B7)** is the pillar for post 6. The SEO research grades that
   cluster OPEN, with roughly 19,900 renter-occupied units in the near ring and zero competitors
   marketing to landlords. Post 6 is a 2,400 word asset with unique Census rent data in it, pointing
   at nothing. This is the highest-value missing page of the three.
3. **`/deck-and-fence-staining/` (B5)** is a launch-phase page in the plan. Post 3 mentions decks in
   passing and no longer links out.

When any of those three ship, re-add the link. The three sentences that were reworded are at the foot
of posts 1, 3 and 6, in the "More on this" paragraph.

**One naming note.** `cabinet-refinishing.html` and `drywall-and-repair.html` do not match the
canonical slugs in `launch/08-SEO-AND-KEYWORD-RESEARCH.md` (`/cabinet-painting/` and
`/drywall-repair-and-painting/`). That is a live decision, not an error to fix blindly: the SEO slugs
carry the target query wording, the shipped slugs read better. Whichever wins, decide before launch,
because changing a URL after it is indexed costs the ranking it earned.

**Deliberately not linked:** `/popcorn-ceiling-removal/` and anything roofing. Posts 1 and 6 discuss
popcorn ceilings only as a cost driver and an asbestos test-first caution, and never offer the
service, because flag 4 in the SEO research holds that page until Mike confirms how he handles
pre-1980 ceilings. Roofing appears nowhere at all, because it is state-licensed in Illinois under 225
ILCS 335 and no license number has been supplied.

## Noindex

Every post carries `noindex: true` and the site-wide `<meta name="robots" content="noindex, nofollow">`
applies. That is temporary, per the house standard, while this is a preview build.

**Go-live checklist item: remove the noindex.** A site left noindexed by accident is the most common
way a launch like this quietly produces nothing for six months. Flip the `NOINDEX` constant in
`build.py`, delete or update `robots.txt`, and confirm with a live fetch of a rendered post before
declaring launch.

## House rules these posts were written under, so edits do not break them

1. **No invented testimonials, reviews, star ratings or customer quotes.** There are none in these
   posts and there is no review markup.
2. **No invented license, insurance, bond, certification, award, association membership, "since 19xx"
   or job count.** Posts 1, 2 and 6 tell the reader to *ask any contractor* for their EPA lead-safe
   firm certification number. They never claim Colors Your Way USA holds one, because that has not
   been supplied. **If Mike supplies his EPA RRP firm certification number, those passages become far
   stronger and should be revisited.**
3. **No price is stated as Mike's price.** Every dollar figure is a published market range from a
   named, linked source, and each post says so in the body and again in a closing note.
4. **US English. No em dashes anywhere.** Verified across all files.
5. **Nothing claimed that the owner transcript does not support.** The one business-specific claim in
   the whole set is in post 6: "Our van has said Maintenance Service on it for years." That is from
   the verified van copy in `CLIENT-BRIEF.md`.

## Sourcing

Every factual claim traces to a References section at the foot of its post. All source URLs were
checked live on 2026-08-31 and returned HTTP 200. Sources used across the set:

- Thumbtack cost pages: interior painting, cost to paint a room, kitchen cabinets, cabinet refacing,
  cabinet installation, kitchen remodel, drywall repair, wallpaper removal, popcorn ceiling removal,
  deck staining, fence staining
- This Old House: interior painting cost, cost to paint house exterior
- National Park Service, Preservation Brief 10, Exterior Paint Problems on Historic Woodwork
- U.S. EPA, Lead Renovation Repair and Painting Program; Protect Your Family from Sources of Lead
- NOAA NCEI, U.S. Climate Normals 1991 to 2020, Chicago Midway station USW00014819, pulled from the
  NCEI data access service
- U.S. Census Bureau, ACS 5-year estimates 2023, tables B25003, B25035, B25064, B25077, pulled from
  the Census Data API
- Cook County Residential Tenant and Landlord Ordinance
- Illinois Security Deposit Return Act, 765 ILCS 710
- NOAA Global Monitoring Laboratory solar calculator

Two datasets in these posts were pulled directly rather than quoted from a publisher, which means
they are not available anywhere else in this market and are worth protecting as a differentiator:
the NOAA Chicago Midway monthly normals in post 3, and the Census median gross rent and tenure table
in post 6.

## Photos

See `images/CREDITS.md`. All 14 are Pexels stock. Every caption in every post says so. Replacing them
with Mike's own before-and-after job photos is the single biggest quality lever on this site, and it
is also the blocker on blog topic C20 in the SEO research.
