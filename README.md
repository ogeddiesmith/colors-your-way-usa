# Colors Your Way USA: website

Static site for Colors Your Way USA (Mike Walsh, painting and remodeling, Bridgeview IL).
No framework, no build toolchain, no database. Two Python scripts and a folder of files.

**Currently a PREVIEW build.** Every page carries `noindex, nofollow`, `robots.txt` disallows
everything, and an amber banner on every page explains what is placeholder. See
[Go-live checklist](#go-live-checklist) before any of that comes off.

---

## BLOCKED: we do not have Mike's email address

The contact form is fully built and cannot deliver a single lead, because nobody has told us
where the leads should go.

**The one question that unblocks it:** *Mike, which email address do you want new job inquiries
sent to?*

Everything else is done and waiting: the relay account, the redirect, the thank-you page, the
spam trap and the phone-readable subject line. All of it is inert until `FORM_ACCESS_KEY` in
`build.py` has a value, and getting that value takes about four minutes once we have the
address. See [Setting up the form](#setting-up-the-form).

Until then the site does not pretend. Every page shows a visible *"This form is not connected
yet, call or text 708-935-4289"* notice where the form's submit path would be, and `app.js`
blocks the submit outright. A visitor never posts into a void. That is deliberate: a form that
silently swallows a lead is worse than no form at all, because the customer thinks they have
made contact and Mike never knows they existed.

---

## Quick start

```bash
cd clients/colors-your-way-usa/site
python3 build.py          # regenerates every HTML page, style.css, app.js, sitemap.xml, robots.txt
```

That is the whole workflow. No dependencies, no virtualenv, Python 3 standard library only
(tested on the system Python 3.9 that ships with macOS).

To preview it locally:

```bash
python3 -m http.server 8000     # then open http://localhost:8000
```

---

## The one rule

**Never hand-edit the generated HTML.** Edit `build.py` and re-run.

Fifteen pages share one header, one footer, one phone number and one address. Editing a generated
`.html` file works exactly once, and then the next build silently reverts it. Every generated file
carries a comment saying so.

If you want to change:

| Thing | Where |
|---|---|
| Phone number, address, business name | The CONSTANTS block at the top of `build.py` |
| Navigation | `NAV` and `FOOT_NAV` |
| Any page's copy | The `SERVICES` list, or the relevant `build_*()` function |
| Service area towns and the write-up for each | `TOWNS` |
| License, insurance, warranty, hours | `TRUST` |
| Colors, type, layout | `CRITICAL_CSS` and `REST_CSS` |
| Behavior (mobile nav, form guard) | `APP_JS` |
| Blog posts | Drop a `.md` file in `blog/` and re-run. Nothing to register. |

---

## What gets generated

```
index.html                  Home
interior-painting.html      \
exterior-painting.html       |
cabinet-refinishing.html     |  Five service pages, painting first
drywall-and-repair.html      |
remodeling.html             /   (deliberately last: it dilutes painting relevance)
areas/index.html            Service area hub. Every place grouped by distance band
areas/<place>.html          One page per town or Chicago neighborhood. 76 of them
service-area.html           Signpost only. The old service area URL, permanently
                            noindex and out of the sitemap, kept so links that were
                            already shared still land somewhere. It links to the hub
contact.html                Phone, address, form, paperwork status
thank-you.html              Where the form lands after a successful submission.
                            PERMANENTLY noindex and kept out of the sitemap: that
                            one does NOT come off at go-live. An indexed thank-you
                            page collects direct entrances from people who never
                            filled the form in, which ruins the conversion count it
                            exists to produce.
blog/index.html             Auto-generated index of the posts
blog/<slug>.html            One page per Markdown post in blog/
style.css  app.js  logo.svg  sitemap.xml  robots.txt  .nojekyll
```

`build.py` also prints an audit result and, while in preview, a sign-off checklist.

---

## The city pages, and the rule that lets them exist

`areas/` holds 76 pages, one per town or Chicago community area, plus the hub at `areas/index.html`.
They are generated from `PLACE_TOWNS` and `PLACE_NBHD` in `build.py`, which hold the published
housing data for 110 researched places. The research file behind them is
`launch/12-CITY-PAGE-DATA.md`.

**Programmatic location pages are the easiest way there is to get a small site penalized.** Google's
spam policy names doorway pages directly: pages generated for many cities that differ only by the
place name. The action is taken against the whole domain, not the folder. So this section is allowed
to exist on exactly one condition, and `build.py` enforces it rather than trusting it:

- **Jaccard similarity** over 8-word shingles of the town-specific prose. Two city pages sharing
  more than `SIM_JACCARD_MAX` of their body text fail the build.
- **Containment**, the share of one page's shingles that also appear on another. Catches a short
  page that is entirely a subset of a long one, which Jaccard scores low and Google does not.
- **The unique-sentence floor.** Every city page must contain at least one full sentence that
  appears on no other city page. A page with nothing of its own does not need to be its own URL.

The measured region is marked in the HTML by `<!-- city-body -->` comments. The header, the quote
form, the CTA and the footer are identical on every page of the site by design, and measuring them
would hide the duplication the check exists to find.

What makes the pages genuinely different is real data, not synonyms: median build year, share built
before 1980 (before 1970 for Chicago neighborhoods, whose source does not publish a 1978 bucket),
tenure split, the detached / attached / multi-unit mix, median rooms, median home value and
straight-line distance from the shop. Rankings and comparisons are computed from the table, never
typed, so they cannot go stale when a place is added or removed.

**What the data does not contain, and must never be invented:** exterior wall material. There is no
brick-versus-frame variable in the Census and none in the regional data either. Every sentence
describing construction type is inference from era and structure mix, is labeled as inference on the
page, and carries no percentage. Do not "improve" that by attaching a number to it.

---

## The two scripts

### `build.py`

Generates the site. Also runs a small audit on its own output every time and **exits non-zero if
it fails**, so a bad build cannot be deployed by accident. The audit refuses:

- em dashes and en dashes (house rule: periods, commas, colons, parentheses)
- UK spelling
- unsupported credential phrases ("licensed and insured", "years in business", "jobs completed")
- `aggregateRating` or star-rating markup, since there are no reviews
- dollar figures anywhere that could read as this business's price

Two audited exceptions, both checked rather than assumed:

- `areas/*.html` carry Census median home values. Those are facts about towns, not prices for
  work. The exemption is NOT a blanket one: the page has to carry the `CENSUS_MARK` sentence
  saying in so many words that the figure is a home value and not a price. Strip that sentence
  and the build fails.
- `blog/*.html` carry published market ranges. `build_post()` automatically injects a "none of it
  is a Colors Your Way USA price" block into any post that quotes money, and the audit fails the
  build if that block or the sources are missing.

The build also **fails on a dead internal link** from a blog post. See `LINK_MAP`.

### `fetch_images.py`

Downloads a pinned set of 25 Pexels photographs into `images/`, then writes `images/manifest.json`
(which `build.py` reads for alt text and real pixel dimensions) and `images/CREDITS.md`.

```bash
python3 fetch_images.py            # no-op if the files are already there
python3 fetch_images.py --force    # re-download
```

Run it once. It is separate from `build.py` on purpose: rebuilding HTML should never hit a
third-party API. It needs `PEXELS_API_KEY` in the repo root `.env`. Unsplash is dead, do not add
it back.

The photo IDs are pinned, not searched. A live search would return different photos on every run
and silently change the site.

---

## Blog

Posts are Markdown with YAML front matter in `blog/`. `build.py` renders each one into a real page
using the same shell as the rest of the site, so every post automatically gets the header, the
phone number, the sticky mobile call bar, the footer, the schema and the noindex.

**To publish a post: put the `.md` in `blog/` and run `python3 build.py`.** The index page,
`sitemap.xml` and the internal links all update themselves. `blog/index.md` and `blog/README.md`
are skipped (they are the content side's own notes, not posts).

Front matter the renderer uses:

```yaml
title:        required. Becomes the h1 and the title tag.
slug:         required in practice. Becomes <slug>.html. Defaults to the filename.
description:  meta description and the summary on the index page.
date:         YYYY-MM-DD. Renders as a <time> and feeds datePublished.
category:     groups the post on the index page.
order:        sort order within the category.
service_page: renders a "See our X page" button. X is named after the page it LANDS ON.
related:      list of slugs. Renders as pills at the end of the post.
hero:         src / alt / width / height / credit / credit_url
stock_photos: true renders the "these photographs are stock" note.
```

The Markdown renderer covers exactly what these posts use: `##` and `###` headings, paragraphs,
bold, italic, links, pipe tables, ordered and unordered lists, blockquotes, horizontal rules, and
raw HTML blocks (the posts embed hand-built inline SVG figures, which pass through untouched). It
is not a general-purpose Markdown engine and it fails loudly rather than mangling something it
does not understand.

### `LINK_MAP`

Posts sometimes link to service URLs in a directory style this site does not use, and to pages
that do not exist yet. Every internal target has to be in `LINK_MAP` in `build.py`. **An unmapped
one fails the build**, because a dead internal link on a fifteen page site is exactly the kind of
thing nobody notices for a year.

Two entries currently point somewhere other than their own page, because those pages are on the
month 2 to 3 queue in `launch/08-SEO-AND-KEYWORD-RESEARCH.md` section 7:

| Post link | Currently lands on | Fix |
|---|---|---|
| `/rental-turnover-painting/` | `areas/index.html` | Build the rental turnover page, then re-point |
| `/deck-and-fence-staining/` | `exterior-painting.html` | Build the deck and fence page, then re-point |

---

## Deploying to GitHub Pages

Target: repo **`colors-your-way-usa`** under the **`ogeddiesmith`** account, serving at
`https://ogeddiesmith.github.io/colors-your-way-usa/`. That URL is already what `SITE` in
`build.py` is set to, and it is what every canonical tag, Open Graph URL and sitemap entry points
at. If the URL changes, change `SITE` and rebuild, or every canonical on the site will be wrong.

The site folder IS the repo root. `.nojekyll` is generated so GitHub Pages serves the files as-is
instead of running Jekyll over them.

### First time

```bash
cd clients/colors-your-way-usa/site
python3 build.py

gh repo create ogeddiesmith/colors-your-way-usa --public --disable-issues --disable-wiki
git init
git branch -M main
git add .
git commit -m "Colors Your Way USA site, preview build"
git remote add origin https://github.com/ogeddiesmith/colors-your-way-usa.git
git push -u origin main

gh api -X POST repos/ogeddiesmith/colors-your-way-usa/pages \
  -f 'source[branch]=main' -f 'source[path]=/'
```

Give it a minute, then check `https://ogeddiesmith.github.io/colors-your-way-usa/`.

### Every time after that

```bash
python3 build.py && git add -A && git commit -m "site update" && git push
```

### Custom domain

`colorsyourwayusa.com` already exists. It was registered 2026-04-22 at GoDaddy and currently
serves a GoDaddy Website Builder "Launching Soon" page. Getting access to that GoDaddy account is
the number one blocker on this project, per
`launch/08-SEO-AND-KEYWORD-RESEARCH.md` finding 1.1.

When that access exists and the site is ready to go live:

1. Set `SITE = "https://colorsyourwayusa.com"` in `build.py` and rebuild, so canonicals, Open
   Graph URLs and the sitemap point at the real domain.
2. Add a `CNAME` file to this folder containing exactly `colorsyourwayusa.com`.
3. At GoDaddy, point the apex A records at GitHub Pages
   (`185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`) and add a `www`
   CNAME to `ogeddiesmith.github.io`.
4. In the repo's Pages settings, set the custom domain and turn on Enforce HTTPS once the
   certificate is issued.

Note that `CNAME` is not generated by `build.py`, so it will survive rebuilds. That is deliberate.

---

## Setting up the form

GitHub Pages serves files. It cannot send email, so the contact form has to hand the submission
to a third-party relay that emails it on. This site uses **Web3Forms**.

**Before you start you need one thing: the email address Mike wants leads sent to.** Without it
none of the steps below can be completed. See the blocker at the top of this file.

### The steps

1. **Go to <https://web3forms.com>.** In the box on their home page, type Mike's email address
   and press the button. There is no account to create, no password to choose and no card to
   enter.
2. **Open Mike's inbox.** Web3Forms sends an email containing an **Access Key**. It looks like
   `a1b2c3d4-e5f6-7890-abcd-ef1234567890`. Copy it.
3. **Open `build.py`** and find this line near the top (around line 121):

   ```python
   FORM_ACCESS_KEY = ""
   ```

   Paste the key between the quote marks:

   ```python
   FORM_ACCESS_KEY = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
   ```

   The key is safe in a public repo. Web3Forms state this plainly: *"You do not need to hide the
   access key. Access key is public."* It only permits sending an email to the address it was
   issued to. It cannot be used to read anything.
4. **Re-run the build** and confirm it finishes without errors:

   ```bash
   python3 build.py
   ```

   The large `BLOCKED` banner at the end of the output disappears once the key is in place. If
   it is still there, the key did not save.
5. **Test it, from a phone.** Open the live contact page on a mobile, fill the form in properly
   and submit it. Then check all four of these:
   - The email arrives in Mike's inbox. **Check the spam folder on the first one** and mark it
     "not spam" if it landed there, or every later lead lands there too.
   - The subject line reads like `New lead: Interior painting in Palos Hills`.
   - The body lists name, phone, email, service, town, details and the page it came from.
   - The browser lands on the thank-you page, not on a Web3Forms page.

   A key that has never been tested is not a working form. Do not skip this step.

### Changing the address later

Repeat steps 1 to 4 with the new address. The old key stops being used the moment the new one
is built in. Nothing else in the site needs to change.

### Why Web3Forms and not the others

All four options below are free and work on GitHub Pages. The requirement that decided it was
the redirect to our own thank-you page, plus keeping Mike's email out of the page source.

| | Free redirect to our own page | Recipient email hidden | Free tier | Setup for a non-technical owner |
|---|---|---|---|---|
| **Web3Forms** | **Yes**, same domain, which ours is | **Yes** | Server-side spam filtering, honeypot | **Email address in, key out. No account.** |
| Formspree | **No, paid feature** | Yes | 50 submissions a month | Account signup |
| FormSubmit | Yes | **No, it is in the HTML** | Not stated | Email confirmation click |
| Getform (now Forminit) | Yes | Yes | 100 a month, 1 form | Account signup |

- **Formspree is disqualified on the redirect alone.** Their help center lists the "Thank You"
  redirect as *"Available on: Personal, Professional, Business plans"*. On free, Mike's customers
  would land on a Formspree-branded page after submitting. The free plan is also capped at 50
  submissions a month.
  <https://help.formspree.io/articles/form-and-project-settings/thank-you-redirect>
  <https://help.formspree.io/articles/account-management/account-limits>
- **FormSubmit puts the recipient address in the page source.** The form action is literally
  `https://formsubmit.co/<email>`. That publishes Mike's inbox on every page of the site for any
  scraper to harvest. It also defaults to reCAPTCHA, which we are not using because it costs
  conversions. <https://formsubmit.co/>
- **Getform was renamed Forminit in January 2026.** The feature set is fine: 100 submissions a
  month, one form, redirects on free. The problem is that a service which changed its name and
  its domain this year is a poor bet for something nobody will be watching.
  <https://forminit.com/pricing/>
- **Web3Forms** supports the redirect on free as long as it points at the same domain, which ours
  does, and never puts the recipient address in the HTML.
  <https://docs.web3forms.com/getting-started/customizations/redirection.md>
  <https://docs.web3forms.com/getting-started/faq.md>

**One number we could not verify:** Web3Forms' pricing page blocks automated fetching and their
docs do not state the free monthly submission cap. Read it off <https://web3forms.com> during
step 1 and write it in here. Do not quote a cap to Mike that nobody has actually read. For scale,
a one-man painting business is nowhere near any of these limits, and the phone remains the
primary channel regardless.

### If the form ever stops working

Symptoms are: submissions stop arriving, or the visitor sees a Web3Forms error page.

1. Check Mike's spam folder first. This is the cause most of the time.
2. Check the monthly cap has not been hit (see above).
3. Re-run step 5 to reproduce it.
4. Worst case, set `FORM_ACCESS_KEY = ""` and re-run. That puts the site back into the honest
   degraded state: a visible "call or text" notice instead of a form that fails. Leads keep
   coming by phone while it is sorted out.

---

## Go-live checklist

`build.py` prints this list on every preview build. Nothing here is optional.

- [ ] **Get Mike to confirm the outer ring of the service area.** There are now 76 places with a
      page each, from Bridgeview at 0.0 miles to Park Forest at 18.9. He confirmed the shape of the
      area, Chicago plus south and southwest, on 2026-08-31. He has never confirmed the individual
      towns at the edge. Do not list a town he will not drive to: a site claiming Frankfort while he
      actually works Bridgeview to Oak Lawn dilutes relevance everywhere. Cutting a place is one
      line in `PLACE_TOWNS` and a rebuild.
- [ ] **Ask him about the west suburbs.** Berwyn, Cicero, Riverside, Brookfield, La Grange, Oak Park
      and 27 others are already researched and sitting in the place table with status `GATE-WEST`.
      `INCLUDE_WEST_SUBURBS = False`, so not one of them generates. They are close, old, and the
      strongest lead-safe angle on the whole researched list. If he works them, flip the flag and 33
      more pages build. If he does not, leave it alone: a page claiming coverage of a town is a
      promise, and no promise goes on this site before he makes it.
- [ ] **Get his job photos.** Every photograph on this site is Pexels stock, including the before
      and after pairs, whose two halves are not the same room. This is the single biggest quality
      lever on the site and both the SEO and the competitor research reached that conclusion
      independently. Priority order is in `images/CREDITS.md`.
- [ ] **Fill `TRUST` in `build.py`.** Insurance carrier and limit, any local registration, the
      workmanship guarantee **in Mike's own words**, EPA RRP certification number if he holds one,
      and business hours. Until then each renders as a visible "To supply" slot. Never type a
      plausible-looking value into an empty one.
- [ ] **Get Mike's email address and set `FORM_ACCESS_KEY`.** This is the current blocker on the
      whole contact form and it is one question to Mike. Full instructions in
      [Setting up the form](#setting-up-the-form). Then **test it with a real submission from a
      phone**: confirm the email arrives, confirm the subject names the service and the town, and
      confirm the browser lands on `thank-you.html`. While the key is empty, every page shows a
      visible "call or text" notice and `app.js` blocks the submit, which is correct behavior but
      is not a working form.
- [ ] **Confirm the process copy** on the service pages matches how Mike actually works. Masking,
      prep, cleanup and the cabinet door removal sequence are written as standard trade practice,
      not from his description.
- [ ] **Confirm the "owner quotes it, owner works on it" claim** still holds. It is used at
      headline level because it is true and no franchise can copy it. It stops being true the day
      he puts on a crew.
- [ ] **Do not add roofing** without a license number. Roofing contractors are state-licensed in
      Illinois under 225 ILCS 335 and IDFPR lists it as regulated; painting and general contracting
      are not. It is excluded from this build on purpose and `INCLUDE_ROOFING` documents why. This
      is the one place on the site where an unverified claim carries regulatory exposure rather
      than just a credibility problem.
- [ ] **Do not add popcorn ceiling removal** until Mike confirms how he handles pre-1980 ceilings.
      Median build year across the near ring is 1955 to 1977 and that texture carries a real
      asbestos question. `INCLUDE_POPCORN_REMOVAL` documents it.
- [ ] **Set up measurement before launch, not after.** Google Search Console (domain property,
      verified by DNS at GoDaddy while access is open), GA4 with conversion events on the `tel:`
      click and the form submit, and Google Business Profile insights.
- [ ] **Create the Google Business Profile first.** There is no profile today. For a service-area
      contractor the profile is the SEO plan for the first six months and the website is secondary:
      nine of ten commercial queries tested returned a map pack. See
      `launch/08-SEO-AND-KEYWORD-RESEARCH.md` finding 1.2.
- [ ] **Then, last: set `NOINDEX = False` in `build.py` and rebuild.** That removes the
      `noindex, nofollow` tag from every page, removes the preview banner, and rewrites
      `robots.txt` to allow crawling and point at the sitemap. Then submit the sitemap in Search
      Console. **A site left noindexed by accident is the most common way a launch like this
      quietly produces nothing for six months.**

---

## What is deliberately NOT on this site

Every one of these is a decision, not an oversight, and each is documented in `build.py` next to
the constant that controls it.

**No prices.** `PRICING_RANGES = None`. A cost page is the single highest-value page on the
roadmap: zero of the twelve competitors reviewed publish a price, and a pricing question appeared
in People Also Ask on nine of the ten queries tested. It is not in this build because the inputs
are not ready. Every figure collected in `launch/02-MARKET-PRICING-RESEARCH.md` is a **national**
average, Cook County labor sits above the national mean, and two of the publishers disagree by
roughly 2x on whole-interior work. Publishing national midpoints labeled as local ranges would be
inaccurate, and inaccurate is the one thing a "we publish our ranges" differentiator cannot be.
Run the local quote protocol in section 5 of that document (8 to 10 real quotes on one defined
reference job), then set `PRICING_RANGES` and build the page.

**No reviews, ratings or testimonials.** There are none to show. The home page carries an empty,
clearly labeled slot instead, and the JSON-LD emits no `aggregateRating` or `Review`, which is
both a house rule and a Google structured-data policy requirement. Worth showing Mike: one
competitor in this market is currently running three five-star testimonial cards with the
placeholder body text still in them.

**No roofing page.** See the checklist above.

**No popcorn ceiling removal page.** See the checklist above. It is genuinely attractive work
(roughly two to three times the per-square-foot rate of painting the same ceiling, and the map
pack for it is held by drywall specialists rather than painters), so revisit it once the asbestos
handling question is answered.

**No license or insurance claims.** `TRUST` is all `None` and every `None` renders as a visible
"To supply" slot. The home page explains plainly that Illinois does not license painters or
general contractors at state level, with sources, which is more useful to a homeowner than a badge
and is a differentiator rather than a weakness.

---

## Design and technical notes

**Palette** is blue, green and red, taken from the paint splatters already on Mike's van. Every
text pairing was checked against WCAG 2.2 AA (4.5:1 body, 3:1 large text and UI).

**`logo.svg` is a placeholder.** The real logo is multicolor paint splatters on white and is on
the van. Get the artwork, or a clean photo of the van, and replace it. It is a stand-in for
layout, not a rebrand.

**Performance.** System font stack, so no webfont request. Critical CSS is inlined in every page
head and the rest is preloaded. Every image carries real `width` and `height` read from the actual
file bytes, which is what stops the page reflowing while photos load. Everything below the fold is
lazy loaded. No frameworks and no third-party scripts at all.

**Accessibility.** Skip link, semantic landmarks, one `h1` per page, `aria-current` on the active
nav item, every form field labeled, visible focus rings, `prefers-reduced-motion` respected, real
alt text on every image, and wide tables scroll inside their own container so the page body never
scrolls sideways.

**The quote form appears once per page**, in the hero, so it is above the fold. Once, not twice,
because two copies would mean duplicate element IDs and a broken experience for screen readers. On
a phone it moves above the hero photo, since the form outranks the picture.

**Every page routes to the phone.** Tap-to-call in the header on every page and at every width, a
sticky call bar pinned to the bottom on mobile, and a phone-first closing section. Mike is a phone
person with one number and no CRM, so that is the conversion this site is built for.

---

## Source documents

The content decisions on this site come from research in `../launch/` and `../CLIENT-BRIEF.md`.
Read those before making substantive copy changes.

| File | What it decides here |
|---|---|
| `../CLIENT-BRIEF.md` | The verified facts. Nothing on this site may contradict it or go beyond it. |
| `../launch/02-MARKET-PRICING-RESEARCH.md` | Why there are no prices, and the "what moves the number" section on every service page |
| `../launch/08-SEO-AND-KEYWORD-RESEARCH.md` | The page set, the town list, title tag patterns, the schema rules, and the regulatory flags |
| `../launch/09-COMPETITOR-RESEARCH.md` | Positioning: painting first, multi-trade second, honest credentials, tight radius |
