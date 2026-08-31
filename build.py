#!/usr/bin/env python3
"""
Colors Your Way USA static site generator.

    python3 build.py

Writes index.html, six service and area pages, contact.html, blog/index.html,
style.css, app.js, logo.svg, sitemap.xml and robots.txt.

DO NOT HAND-EDIT THE GENERATED HTML. Edit this file and re-run, or the next
build silently reverts your change. Nine pages share one header, one footer, one
phone number and one address. Changing the phone number is one edit here, not
nine find-and-replaces that drift apart.

--------------------------------------------------------------------------------
WHAT THIS FILE IS NOT ALLOWED TO CONTAIN
--------------------------------------------------------------------------------
This is a real business with a real owner and almost no verified paperwork. The
following are hard rules, not preferences. They are enforced by the constants in
the CONSTANTS block and re-checked by `python3 build.py --audit`.

  1. No testimonials, reviews, star ratings or review counts. There are none.
     No aggregateRating or Review markup in the JSON-LD either: that is both a
     house rule violation and a Google structured data policy violation.
  2. No license number, insurance carrier, bond, certification, award,
     association membership, "since 19xx", years in business, or job counts.
     Those live in TRUST below, every value is None, and None renders as a
     visible "To supply" slot.
  3. No price stated as Mike's price. PRICING_RANGES is None and there are no
     dollar figures anywhere in this file. See the note on PRICING_RANGES.
  4. US English. No em dashes anywhere, in any string.
  5. Nothing claimed that the owner transcript does not support. Ordinary
     process description that still needs his sign-off goes in CONFIRM, which
     renders into the page source as a comment and prints at build time.

Sources behind the content choices:
  launch/02-MARKET-PRICING-RESEARCH.md   what drives price, margin ranking
  launch/08-SEO-AND-KEYWORD-RESEARCH.md  page set, city set, title patterns, flags
  launch/09-COMPETITOR-RESEARCH.md       positioning gaps, what the other 12 do
  CLIENT-BRIEF.md                        the verified facts
"""
import hashlib, io, json, math, os, re, sys

# =============================================================================
# CONSTANTS
# =============================================================================

SITE = "https://ogeddiesmith.github.io/colors-your-way-usa"

# NAP. One source of truth so it can never drift from the Google Business
# Profile, the MapQuest listing or any directory. Byte-identical everywhere.
BRAND = "Colors Your Way USA"
OWNER = "Mike Walsh"
PHONE_DISPLAY = "708-935-4289"
PHONE_E164 = "+17089354289"
STREET = "7900 W. 83rd St."
CITY = "Bridgeview"
REGION = "IL"
POSTAL = "60455"

# KEYWORD SCOPE VS ADDRESS. These are two different things and the site kept
# confusing them.
#
#   The ADDRESS is Bridgeview. That is a fact, it is what goes in the footer,
#   the contact page and the LocalBusiness schema, and Google needs a real one
#   to rank anything locally. It never changes and it is a selling point:
#   locally based beats a franchise office in another county.
#
#   The SCOPE is the region. Bridgeview is a village of 16,721 people. Scoping
#   the home page and the five service pages to it caps the whole site at a
#   town almost nobody searches, while 76 city pages underneath it cover all of
#   Chicagoland. That is an inverted hierarchy: the head terms live on the home
#   and service pages, the town terms live on the pages under areas/.
#
# So: home and service pages are REGIONAL, areas/*.html are town level, and
# areas/bridgeview.html is a normal city page like the other 75. See
# launch/08-SEO-AND-KEYWORD-RESEARCH.md rule 13.2.1.
REGION_LONG = "Chicago and the south and southwest suburbs"
REGION_SHORT = "Chicago and the south suburbs"

# Preview switches. BOTH of these flip at go-live, together, and the go-live
# checklist in README.md is the gate.
NOINDEX = True        # emits robots noindex,nofollow + Disallow: / + the banner
PREVIEW_BANNER = True # the amber strip explaining what is placeholder

ASSET_V = "3"         # bump on any CSS or JS change to bust the browser cache

# -----------------------------------------------------------------------------
# FORM DELIVERY
# -----------------------------------------------------------------------------
# GitHub Pages is static. Static hosting cannot send email, so the contact form
# needs a third-party relay. This site uses Web3Forms.
#
# WHY WEB3FORMS AND NOT THE OBVIOUS ALTERNATIVES
#
#   Formspree      Custom redirect to our own thank-you page is a PAID feature.
#                  Their own help center lists the "Thank You" redirect as
#                  "Available on: Personal, Professional, Business plans", and
#                  the free plan is capped at 50 submissions a month.
#                  https://help.formspree.io/articles/form-and-project-settings/thank-you-redirect
#                  https://help.formspree.io/articles/account-management/account-limits
#                  A free Formspree form would dump Mike's leads on a Formspree
#                  branded page. Disqualified on the redirect alone.
#
#   FormSubmit     Puts the recipient address straight in the page source:
#                  the form action is literally https://formsubmit.co/<email>.
#                  Publishing Mike's inbox in the HTML of nine pages is handing
#                  it to every scraper on the internet. It also defaults to
#                  reCAPTCHA, which we are not using because it costs
#                  conversions.  https://formsubmit.co/
#
#   Getform        Renamed to Forminit in January 2026. Free tier is 100
#                  submissions a month across ONE form, 100 MB storage.
#                  Redirects are supported on free.
#                  https://forminit.com/pricing/
#                  The feature set is fine. The problem is the rebrand: a
#                  service that changed its name and domain this year is the
#                  wrong bet for something nobody will be watching.
#
#   Web3Forms      Redirect to our own thank-you page works on the free plan so
#                  long as it is the same domain, which ours is.
#                  https://docs.web3forms.com/getting-started/customizations/redirection.md
#                  The recipient email is never in the HTML. The page carries an
#                  access key, which their docs state plainly is public by
#                  design: "You do not need to hide the access key. Access key
#                  is public."
#                  https://docs.web3forms.com/getting-started/faq.md
#                  Free tier includes server-side spam filtering and a honeypot.
#                  https://docs.web3forms.com/getting-started/customizations/spam-protection/spam-protection.md
#                  Setup is: enter an email, get a key in that email, paste it
#                  here. No account, no dashboard, no password for Mike to lose.
#
# NOT VERIFIED: Web3Forms' own pricing page returns 403 to automated fetches and
# their docs do not state the free monthly submission cap. Read the number off
# https://web3forms.com/#pricing during setup and write it into README.md.
# Do not quote a cap to Mike that nobody has actually read.
#
# THE ACCESS KEY IS THE ONLY THING MISSING. It is safe in a public repo.
# While it is empty the form does not pretend to work: it renders a visible
# "call or text" notice and app.js blocks the submit. See README.md step 1.
FORM_ACCESS_KEY = ""

# Fixed provider values. These do not change per client.
FORM_ENDPOINT = "https://api.web3forms.com/submit"
FORM_REDIRECT = SITE + "/thank-you.html"

# Fallback subject, used when JavaScript is off. app.js overwrites this on
# submit with the service and the town so the phone notification is readable
# without opening it. ASCII only: Gmail garbles anything else in a subject.
FORM_SUBJECT_FALLBACK = "New lead from the Colors Your Way USA website"

# Trust block. Every value is None until Mike supplies the real one. None
# renders as a visible "To supply" slot. Never type a plausible-looking value
# in here. An invented policy number is worse than an empty one.
#
# Note for whoever fills these in: Illinois does not license painters or general
# contractors at state level (IDFPR professions list; 225 ILCS 335 covers
# roofing only). So "licensed" for painting in Illinois is close to meaningless
# and a local municipal registration is the honest thing to name if he holds one.
TRUST = {
    "insurance":  None,  # carrier and general liability limit
    "license":    None,  # municipal contractor registration, if any
    "warranty":   None,  # workmanship guarantee IN MIKE'S OWN WORDS, then a term
    "epa_rrp":    None,  # EPA lead-safe firm certification number, if he holds one
    "hours":      None,  # business hours. Do not guess these.
}

# No prices on this site.
#
# 02-MARKET-PRICING-RESEARCH.md section 5 is explicit: every figure it collected
# is a NATIONAL average, Cook County labor sits above the national mean, and two
# of the publishers disagree by roughly 2x on whole-interior work. Publishing
# national midpoints labeled as local ranges would be inaccurate, and inaccurate
# is the one thing a "we publish our ranges" differentiator cannot be.
#
# 09-COMPETITOR-RESEARCH.md adds the second gate: three or more independent
# sources per line item, at least one non-contractor, before anything ships.
#
# The opportunity is real and large. Zero of twelve competitors publish a price,
# and a pricing question appeared in People Also Ask on nine of ten queries
# tested. So the cost page is the highest-value page on the roadmap. It is not
# in this build because the inputs are not ready. Run the section 5 local quote
# protocol (8 to 10 real quotes on one defined reference job), then set this to
# a list and build the page.
PRICING_RANGES = None

# Roofing is on Mike's trade list and is DELIBERATELY ABSENT from this site.
#
# Roofing contractors are state-licensed in Illinois under 225 ILCS 335, the
# Illinois Roofing Industry Licensing Act, and IDFPR lists both "Roofing
# Contractor" and "Qualifying Party Roofing Contractor" as regulated. Painting
# and general contracting are not regulated at state level. No roofing license
# number has been supplied. Advertising roofing without it is the one place on
# this site where an unverified claim carries regulatory exposure and not just a
# credibility problem. Flip this only when the license number is in hand.
INCLUDE_ROOFING = False

# Popcorn ceiling removal is high margin (roughly 2 to 3x the per square foot
# rate of painting the same ceiling) and the map pack for it is held by drywall
# specialists rather than painters, so it is a genuine opening. It is off this
# build because median year built across the city and the near ring runs 1947 to
# 1977, popcorn texture in that stock carries a real asbestos question, and Mike has not
# confirmed how he handles pre-1980 ceilings. Confirm that, then build the page
# with the testing position stated plainly.
INCLUDE_POPCORN_REMOVAL = False

# Ordinary process description that is normal for the trade but has not been
# confirmed by the owner. Rendered into every page as an HTML comment while
# NOINDEX is on, and printed at the end of every build. Clear these with Mike
# before the noindex comes off.
CONFIRM = [
    "Service area. Mike confirmed Chicago and the south suburbs on 2026-08-31. The "
    "shape of the area is confirmed. The individual places at the edge are not, and "
    "there are now 76 of them with a page each. Walk the outer ring with him and cut "
    "any town he will not actually drive to, particularly Frankfort, Mokena, New "
    "Lenox, Romeoville, Park Forest and Chicago Heights. Cutting a town is one line "
    "in the place table and a rebuild.",
    "West suburbs. Berwyn, Cicero, Riverside, Brookfield, La Grange, Oak Park and 27 "
    "others are researched and sitting in the place table with status GATE-WEST, and "
    "INCLUDE_WEST_SUBURBS is False so none of them generate. They are close, old, and "
    "the strongest lead-safe angle on the whole list. Ask him whether he works them. "
    "If yes, flip the flag and 33 more pages build.",
    "Chicago is claimed as a service area but deliberately framed as south side "
    "first. Confirm Mike is happy taking city work at all, and how far north he "
    "will go, before the noindex comes off.",
    "Process copy, and there is now a lot more of it. Every service page carries a "
    "step-by-step of how a job runs and a full section on what good preparation is, "
    "because preparation is the genuine differentiator and explaining it is the "
    "sale. All of it is written as standard trade practice: masking, filling, "
    "caulking, scuffing old enamel, degreasing cabinets, containing drywall dust, "
    "washing and scraping an exterior. None of it claims anything unusual, but it "
    "does describe how Mike's jobs run. Read it through with him and correct "
    "anything he does differently before this is indexed.",
    "Small promises inside the process copy. The site now says we set up and cover "
    "the room, pack up at the end of each day, put the room back, and walk an "
    "exterior with the customer at the end. These are ordinary and they are the "
    "kind of thing a homeowner decides on, which is exactly why they need his "
    "sign-off rather than ours.",
    # POSITIONING, settled 2026-08-31 by the owner. Do not re-introduce the solo
    # framing that used to live here. The site reads as a COMPANY that Mike Walsh
    # owns and runs, not as one man with a brush. Company voice throughout: "we",
    # "our crew", "our painters". Mike stays named as the owner, because owner-run
    # genuinely beats a franchise on trust and it is true. What is gone is any
    # implication that he personally holds every brush.
    #
    # The line nobody may cross: company voice carries NO HEADCOUNT. Never write
    # a crew size, an employee count, "team of X", or "X painters on staff". We
    # do not know it and it is not ours to invent. "Our crew" is a positioning
    # choice the owner directed. "Our crew of eight" would be fabrication.
    "Owner-run company voice. The site says the company does the work and "
    + OWNER + " owns it and runs the jobs. That is the owner's own direction and "
    "it is supported by the transcript. Confirm the wording reads right to him, "
    "and confirm he is happy being named as owner on every page.",
    "Workmanship guarantee. TRUST['warranty'] is empty. The franchises all carry "
    "two years. This is the cheapest single move to parity and it has to be in "
    "Mike's own words, not ours.",
    "Insurance, license and EPA RRP certification numbers. All TO SUPPLY.",
    "Roofing is excluded from this build on purpose (225 ILCS 335). Do not add "
    "it back without the license number.",
    "Business hours. TRUST['hours'] is empty because guessing them puts a wrong "
    "answer on the Google Business Profile too.",
    "Every photograph is Pexels stock, including the before and after pairs, "
    "which are not the same room. See images/CREDITS.md.",
]

# The form item is appended rather than hardcoded so it cannot go stale. Before
# the key exists it reads as the blocker it is. Once the key is pasted in, the
# remaining job is not "wire it", it is "prove it delivers", and the checklist
# says so. A checklist that still lists a solved problem stops being read.
if FORM_ACCESS_KEY:
    CONFIRM.append(
        "Contact form. FORM_ACCESS_KEY is set, but a key that was never tested is "
        "not a working form. Submit a real entry from a phone, confirm the email "
        "arrives, confirm the subject names the service and town, and confirm the "
        "browser lands on thank-you.html.")
else:
    CONFIRM.append(
        "BLOCKER: we do not have an email address for " + OWNER + ". That single "
        "missing input is the only thing standing between the contact form and "
        "working. Get the address, follow README.md section SETTING UP THE FORM, "
        "paste the key into FORM_ACCESS_KEY, re-run, and test from a phone.")

HERE = os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# IMAGES
# =============================================================================

def load_images():
    p = os.path.join(HERE, "images", "manifest.json")
    if not os.path.exists(p):
        sys.exit("images/manifest.json is missing. Run: python3 fetch_images.py")
    return json.load(io.open(p, encoding="utf-8"))

IMG = load_images()

def img(key, cls="", lazy=True, sizes="", up="", alt=None):
    """One <img> with real alt text and real width and height from the file.

    Width and height are mandatory on every image on this site. They are what
    stop the page jumping around while photos load, which is the single most
    annoying thing a slow contractor site does on a phone. They are also the
    whole of the Cumulative Layout Shift story on a page with no ads and no
    injected content.

    ALT TEXT POLICY, and it is a policy, not an oversight:

      The alt strings in images/manifest.json describe what is in the frame and
      nothing else. They do NOT name a town, they do NOT say "painting
      contractor Bridgeview IL", and they will not.

      Every photograph on this site is Pexels stock. Writing "interior painting
      in Bridgeview" into the alt of a stock photograph is two separate
      problems at once: it is a false statement about the image, and it is
      keyword stuffing, which Google's own image guidance names directly. The
      context a search engine needs comes from the heading above the image, the
      figcaption beside it and the copy around it, all of which are true.

      When Mike supplies real job photos, THAT is when the alt text can carry
      "a repaint in Oak Lawn", because it will be one. The `alt` override
      below exists for exactly that moment. seo_audit() enforces the ceiling:
      125 characters, and no keyword repeated twice inside one string.
    """
    m = IMG[key]
    load = 'loading="lazy" decoding="async"' if lazy else 'fetchpriority="high" decoding="async"'
    c = ' class="' + cls + '"' if cls else ""
    s = ' sizes="' + sizes + '"' if sizes else ""
    return ('<img src="' + up + 'images/' + m["file"] + '" alt="' +
            esc(alt if alt is not None else m["alt"]) + '" '
            'width="' + str(m["w"]) + '" height="' + str(m["h"]) + '" ' + load + c + s + '>')

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))

# =============================================================================
# SERVICE AREA
# =============================================================================
# Every town below carries something true and specific to that town. That is the
# rule, and it is a Google rule, not a style preference: pages that differ only
# by the town name are doorway pages under Google's spam policies.
#
# The area is Chicago and the south and southwest suburbs, confirmed by the owner
# on 2026-08-31. The earlier build carried a narrower southwest-suburb guess. Do
# not narrow it back without asking him, and do not widen it into the north side
# or the west suburbs, which he did not confirm and does not work.
#
# The housing figures are U.S. Census Bureau American Community Survey 5-year
# estimates, 2023 (tables B25003 tenure, B25077 median value, B25035 median year
# structure built, B25034 year-built distribution), pulled 2026-08-31 and
# recorded in launch/08-SEO-AND-KEYWORD-RESEARCH.md section 3. They are cited on
# the page.
#
# Beverly and Mount Greenwood are Chicago community areas, and the Census has no
# geography that matches a Chicago neighborhood. Their figures are for the ZIP
# code tabulation areas that cover them, 60643 and 60655, and both entries say so
# in their own fact chip. Never present a ZCTA figure as a neighborhood figure
# without that label.
#
# Order inside each group is by owner-occupied household count, largest first.
# That is deliberate: build_service() takes the first ten of the home, Chicago and
# near groups for its town pill row, so the biggest markets need to sort to the
# top on their own rather than by hand.

CENSUS_CITE = ("U.S. Census Bureau, American Community Survey 5-year estimates, 2023 "
               "(tables B25003, B25034, B25035, B25077).")

# slug, name, tier, owner-occupied households, renter households, median value
# (None where the residential sample is too small to be worth quoting), median
# year built, the h3 heading, a geography note rendered as an extra fact chip,
# and the paragraph that makes the place different from every other place.
TOWNS = [
 ("bridgeview", "Bridgeview", "home", 4079, 2146, "$234,000", 1975,
  "Bridgeview, IL", "",
  "The shop is here, at " + STREET + " Nobody in the Bridgeview map pack is actually "
  "based in Bridgeview: the three companies holding it are run out of Justice, Burbank and "
  "Brookfield. Being ten minutes away is not a marketing line here, it is why a small repair "
  "is worth looking at the same week instead of being bundled into next month. Bridgeview is "
  "also the one place on this list where manufactured housing is a real share of the stock at "
  "16.1 percent, which nobody competing here has noticed and which is a different structure "
  "and a different job from a site-built house."),

 # ---- Chicago ------------------------------------------------------------
 ("chicago", "Chicago", "chicago", 522179, 624368, "$315,200", 1952,
  "Chicago, IL", "",
  "Chicago is the whole city on paper and the south side in practice, and it is worth being "
  "straight about which one you are getting. The Bridgeview shop is a short run from Garfield "
  "Ridge, Clearing, Ashburn, Beverly and Mount Greenwood, and a long way from the north side. "
  "The city is also the oldest housing anywhere in this service area: about 69 percent of "
  "Chicago housing units were built before 1970, and roughly four in ten date to 1939 or "
  "earlier. In practice that means plaster as well as drywall, painted-shut sash windows, deep "
  "millwork, and pre-1978 paint on very nearly everything. Chicago is also a far bigger and "
  "far more competitive market than any suburb on this list, so the honest version is south "
  "side first, and ask about anything further north before you count on it."),
 ("beverly", "Beverly", "chicago", 13392, 4897, "$233,900", 1950,
  "Beverly, Chicago", "",
  "Beverly is bungalow-belt Chicago close to its most intact, with a stretch of larger frame "
  "and stucco houses up on the ridge. On the community-area figures its median build year is "
  "1941 and nearly half its housing, 47.6 percent, is prewar. On stock that old the paint "
  "work is mostly exterior wood and interior trim: sash and storm windows, porch columns, "
  "soffit and fascia, and interior casing that is already carrying a lot of coats. It is also "
  "as close to a guarantee of pre-1978 paint as anywhere on this list, which changes how an "
  "interior job is contained and cleaned rather than how it is painted."),
 ("mount-greenwood", "Mount Greenwood", "chicago", 9023, 1794, "$303,300", 1954,
  "Mount Greenwood, Chicago", "",
  "Mount Greenwood is the most owner-occupied part of the city on this list, 84.6 percent, and "
  "it is a 1950s neighborhood in a literal sense: its median build year is 1955 and 84.1 "
  "percent of its housing is detached single-family. That is brick bungalow and Cape Cod "
  "stock, smaller rooms, a lot of door and window casing for the square footage, and very "
  "often a basement or attic that was finished later and painted to a different standard than "
  "the rest of the house. Interior quotes here are decided by trim footage far more than by "
  "wall area, which is exactly the line most quotes leave vague."),

 # ---- Near southwest suburbs ---------------------------------------------
 ("oak-lawn", "Oak Lawn", "near", 17940, 3805, "$267,900", 1967,
  "Oak Lawn, IL", "",
  "Oak Lawn is the biggest suburban market in the close ring by a distance, close to 18,000 "
  "owner occupied homes, mostly brick from the mid 1960s. Brick means the paint work is "
  "concentrated in the trim, the soffit, the overhead doors and the interior, and it means a "
  "lot of interior trim linear footage: heavy casing, six panel doors, full baseboard runs. "
  "Trim is where an interior job gets long, and it is the line people forget to ask about."),
 ("burbank", "Burbank", "near", 7761, 1913, "$258,900", 1965,
  "Burbank, IL", "",
  "Burbank is the largest of the genuinely old towns in the close ring, a median build year of "
  "1965 across 10,012 housing units, and eight in ten households own their home. Almost all of "
  "that stock predates 1978, which "
  "puts it squarely inside the federal lead-safe renovation rule. That is not a scare line, it "
  "is a real difference in how an interior job gets set up, contained and cleaned, and it is "
  "worth asking any painter about before they start sanding your window casings."),
 ("evergreen-park", "Evergreen Park", "near", 6109, 1219, "$255,700", 1955,
  "Evergreen Park, IL", "",
  "Evergreen Park has a median build year of about 1955, within a few years of Mount Greenwood "
  "and Beverly, and better than eight in ten households own. It behaves like a continuation of "
  "the city bungalow belt rather than like a suburb: the same brick, the same trim-heavy "
  "interiors, the same pre-1978 answer on every window casing. If you have a bungalow here, "
  "the useful question before anybody quotes it is how much of the original trim is still in "
  "place, because stripped and replaced casing prices very differently from original casing "
  "with sixty years of paint on it."),
 ("palos-hills", "Palos Hills", "near", 5831, 1496, "$259,200", 1977,
  "Palos Hills, IL", "",
  "Palos Hills is among the newest housing in the close ring, median build year around 1977, "
  "with a large share of townhomes and association-managed buildings. Association work is its "
  "own thing: matching an existing scheme exactly, working to a board's schedule and doing "
  "several identical units in a row. Worth asking about if you sit on a board."),
 ("palos-heights", "Palos Heights", "near", 4280, 215, "$350,000", 1976,
  "Palos Heights, IL", "",
  "Palos Heights is among the most owner-occupied places on this list, about 95 percent, with "
  "only a couple of hundred renter households in the whole city. There is effectively no "
  "turnover or landlord market here. What there is instead is repeat homeowner work on 1970s "
  "houses that have generally been kept up: repaints on a cycle, trim and door replacement, "
  "and exterior wood that has been maintained rather than left. That is a different job from a "
  "neglected exterior and it should be priced as one, in both directions."),
 ("hickory-hills", "Hickory Hills", "near", 4025, 1585, "$278,400", 1970,
  "Hickory Hills, IL", "",
  "Hickory Hills is split levels and raised ranches from around 1970, and that shape of house "
  "has a specific problem: a lot of exterior wood in hard places. Soffit, fascia, gable ends "
  "and the trim above a split entry all sit high and all fail first. Those are the elevations "
  "worth pricing carefully, because the paint on the walls is usually the part that is fine."),
 ("chicago-ridge", "Chicago Ridge", "near", 2918, 2391, "$217,800", 1973,
  "Chicago Ridge, IL", "",
  "Chicago Ridge runs close to half rental, which makes it two markets in one town. Owners "
  "wanting a kitchen or a full interior, and small landlords wanting a unit painted quickly "
  "and cleanly between tenants. Both get quoted the same way here: we stand in the "
  "room first."),
 ("worth", "Worth", "near", 2835, 1517, "$220,200", 1967,
  "Worth, IL", "",
  "Worth is 1960s ranch houses on modest lots. On that plan the whole exterior job is usually "
  "the garage door surround, the overhang, the front door and the window trim rather than a "
  "big wall area, which is a very different quote from a two story with a lot of siding. It is "
  "also the kind of job that gets underestimated by anyone quoting off a photo."),
 ("justice", "Justice", "near", 2475, 2329, "$235,200", 1976,
  "Justice, IL", "",
  "Justice is one of the most rented places in the close ring: just under half of its "
  "households are renters. That means turnover, units that need a full repaint between "
  "tenants, on a deadline, priced per unit rather than per room. Not one painting company in "
  "this market advertises to landlords or property managers. The van says Maintenance Service "
  "on it, which is exactly the right language for this work."),
 ("willow-springs", "Willow Springs", "near", 2261, 350, "$370,900", 1977,
  "Willow Springs, IL", "",
  "Willow Springs is small, around 2,600 occupied households in total, and unusually high "
  "value for its age: a median build year of 1977 but a median home value closer to Orland "
  "Park than to its immediate neighbors. A 1977 median also puts roughly half the village on "
  "either side of the 1978 lead-safe line, which is a real reason to check the year on your "
  "own house rather than assume it from the street."),
 ("summit", "Summit", "near", 2229, 1388, "$224,800", 1958,
  "Summit, IL", "",
  "Summit is older than most of what sits immediately around it, a median build year of about "
  "1958, and roughly six in ten households own. Older frame and brick on tight lots usually "
  "means the exterior job is scrape, prime and caulk rather than a straight repaint, and an "
  "honest quote for that reads longer than one from somebody who has only priced the topcoat. "
  "It is also firmly pre-1978 stock, so the lead-safe setup applies as a matter of course."),
 ("bedford-park", "Bedford Park", "near", 161, 35, None, 1947,
  "Bedford Park, IL", "Median value not quoted, residential sample under 200 households",
  "Bedford Park is barely a residential town. The Census counts fewer than 200 occupied "
  "households in the entire village, which is why no median home value is shown here: at that "
  "sample size the estimate is too thin to be worth quoting, and quoting it anyway is how a "
  "website starts stating numbers it cannot stand behind. The few houses that are here have a "
  "median build year of 1947. If you manage a building, a unit or a small commercial space "
  "here, that work is in scope and it is a very short drive."),

 # ---- South suburbs -------------------------------------------------------
 ("oak-forest", "Oak Forest", "south", 8242, 2115, "$247,800", 1975,
  "Oak Forest, IL", "",
  "Oak Forest is mid 1970s stock and eight in ten households own, which makes it a "
  "straightforward homeowner market: whole interiors, full exteriors, kitchens. A 1975 median "
  "build year puts a large share of the town just on the older side of the 1978 lead-safe "
  "line, so the year on your particular house is worth confirming before an interior job is "
  "scheduled rather than after the sanding has started."),
 ("alsip", "Alsip", "south", 5071, 2709, "$208,700", 1974,
  "Alsip, IL", "",
  "Alsip is mid 1970s stock at one of the lower median values on this list, and about a third "
  "of its households rent. That mix produces two different calls: owners doing one room or one "
  "elevation at a time on a budget, and small landlords wanting a unit turned around between "
  "tenants. Both are worth quoting. They are not the same quote, and a contractor who prices "
  "them the same way is wrong on one of them."),
 ("midlothian", "Midlothian", "south", 4503, 1331, "$200,300", 1964,
  "Midlothian, IL", "",
  "Midlothian is mid 1960s stock, largely ranches, with a median value around $200,300 and "
  "almost all of it built well before 1978. On a 1960s ranch the exterior work concentrates "
  "into a narrow band: fascia, soffit, the garage door surround, the front entry and the "
  "window trim. That is not much wall area, but it is all detail and almost all of it is off a "
  "ladder, which is exactly why it gets underestimated by anyone quoting from a photo."),
 ("blue-island", "Blue Island", "south", 4250, 4412, "$169,800", 1961,
  "Blue Island, IL", "",
  "Blue Island is the closest suburb on this list to an even split between owners and renters, "
  "4,250 owner households against 4,412 renting, and its median home value of $169,800 is one "
  "of the lowest in the service area. Median build year is 1961. Put those together and the "
  "realistic work here "
  "is turnover repaints, plaster and drywall repair, and exterior maintenance on older houses, "
  "priced tightly and scheduled tightly. It is solidly pre-1978 stock, so lead-safe setup is "
  "the default rather than the exception."),
 ("crestwood", "Crestwood", "south", 3877, 1143, "$187,700", 1975,
  "Crestwood, IL", "",
  "Crestwood is mid 1970s housing at one of the lower median values on this list, around "
  "$187,700, with about three quarters of households owning. On budgets in that range the "
  "useful conversation is not the total, it is sequencing: what genuinely has to be done this "
  "season to stop it costing more later, and what can wait a year at no penalty. A straight "
  "answer to that is worth more than a discount."),

 # ---- Further out, south and southwest ------------------------------------
 ("orland-park", "Orland Park", "far", 20139, 3214, "$349,400", 1988,
  "Orland Park, IL", "",
  "Orland Park is later stock, a median build year around 1988, and bigger houses. Late 1980s "
  "and 1990s construction is now hitting its second or third full exterior cycle, and the "
  "failure points are different from the older ring: cedar and engineered siding, large two "
  "story elevations, and a lot of it. It is further from the shop, so ask about scheduling."),
 ("tinley-park", "Tinley Park", "far", 19302, 2756, "$289,000", 1987,
  "Tinley Park, IL", "",
  "Tinley Park is close to Orland Park in age and size of housing, roughly 1987 median build "
  "year and nearly nine in ten households owning. Same story on exteriors: the original "
  "builder finish is long past done and the second repaint is the one that has to be prepped "
  "properly, because the first one usually was not."),
 ("homer-glen", "Homer Glen", "far", 7480, 521, "$400,000", 1988,
  "Homer Glen, IL", "",
  "Homer Glen is late 1980s construction on larger lots, about 93 percent owner-occupied, with "
  "a median value around $400,000. Big exterior surface area is the whole theme: long "
  "elevations, a lot of soffit and fascia, and cedar or engineered trim now well past its "
  "first repaint. The second exterior on a house like this is the one that has to be prepped "
  "honestly, because the builder finish was carrying the job right up until it stopped."),
 ("mokena", "Mokena", "far", 6554, 673, "$377,100", 1996,
  "Mokena, IL", "",
  "Mokena is 1990s construction, larger homes and very high owner occupancy. That mostly means "
  "big exterior surface area and interiors with two story entries and vaulted rooms. Height is "
  "its own price tier: a two story foyer is not a room rate job, and anybody quoting it as one "
  "has not looked at it properly."),
 ("frankfort", "Frankfort", "far", 6244, 346, "$461,600", 2000,
  "Frankfort, IL", "",
  "Frankfort is the newest and highest value housing in the whole service area, median build "
  "year around 2000. Newer does not mean less work. It means large elevations, tall interior "
  "volumes and finishes that were specified once and never touched since. It is the furthest "
  "point on this list, so it is worth a conversation about travel before anybody drives out."),
 ("lemont", "Lemont", "far", 5524, 810, "$447,800", 1994,
  "Lemont, IL", "",
  "Lemont has the second highest median home value of any suburb on this list, $447,800, and a median "
  "build year of 1994. Newer and larger, with the problems that go with that: two story "
  "elevations, tall interior volumes, and millwork a builder specified once and nobody has "
  "touched since. A two story entry is not a room-rate job. Lemont also sits west of the rest "
  "of this list, so scheduling is a genuine conversation rather than a formality."),
]

# TOWNS is now ONE input among several, not the service area itself. The full
# place table that drives the /areas/ pages lives in the CITY PAGES section
# further down and covers 76 places. What survives here is the hand-written
# paragraph for the 27 places somebody actually sat and wrote about, which is
# rendered on the matching city page as a "From the shop" note underneath the
# generated data sections.
#
# WARNING FOR ANYONE EDITING THESE PARAGRAPHS: several of them make comparative
# claims ("the biggest", "the only", "the second highest"). Those were true of a
# 27-town list and are not automatically true of a 76-place one. Six were
# corrected on 2026-08-31 for exactly that reason. If you add a superlative
# here, check it against the full table first, or better, do not: the ranking
# sentences on every city page are computed by outlier_sentences() from the
# table itself and cannot go stale.
EDITORIAL = dict((t[0], t[9]) for t in TOWNS)

# Pull one or more groups out of TOWNS, in list order.
def towns_in(*tiers):
    return [t for t in TOWNS if t[2] in tiers]

# =============================================================================
# NAVIGATION AND PAGES
# =============================================================================

# Nav labels are kept short on purpose. Seven items plus a brand lockup plus a
# phone button is already more than fits on one row at 1200px, and a header that
# wraps to two rows eats the fold on a laptop.
NAV = [
    ("Interior", "interior-painting.html"),
    ("Exterior", "exterior-painting.html"),
    ("Cabinets", "cabinet-refinishing.html"),
    ("Drywall", "drywall-and-repair.html"),
    ("Remodeling", "remodeling.html"),
    ("Areas", "areas/index.html"),
]

# The footer has room for the full names, so it uses them.
FOOT_NAV = [
    ("Interior painting", "interior-painting.html"),
    ("Exterior painting", "exterior-painting.html"),
    ("Cabinet refinishing", "cabinet-refinishing.html"),
    ("Drywall and repair", "drywall-and-repair.html"),
    ("Remodeling and trades", "remodeling.html"),
    ("Service areas", "areas/index.html"),
]

JOB_TYPES = [
    "Interior painting", "Exterior painting", "Kitchen cabinets",
    "Drywall or plaster repair", "Trim, doors or carpentry",
    "Tile, flooring or subfloor", "Concrete", "Remodeling, whole job",
    "Rental turnover or maintenance", "Something else",
]

# =============================================================================
# CSS
# =============================================================================
# Palette is blue, green and red, taken from the paint splatters already on the
# van. Every text pairing below was checked against WCAG 2.2 AA (4.5:1 for body
# text, 3:1 for large text and UI borders).
#   #12406f on #ffffff   9.4:1
#   #4a5765 on #ffffff   7.0:1
#   #ffffff on #12406f   9.4:1
#   #ffffff on #b8271d   5.9:1
#   #ffffff on #146c3d   5.2:1
#   #8c1c14 on #ffffff   8.3:1  (red used as text)

CRITICAL_CSS = """
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0}
:root{
--blue:#12406f;--blue-d:#0d2f52;--blue-l:#1c5c9e;
--green:#146c3d;--red:#b8271d;--red-d:#8c1c14;
--ink:#151a20;--ink-2:#4a5765;--line:#dde3ea;--paper:#fff;--wash:#f5f7fa;
--amber:#8a5a00;--amber-bg:#fff7e6;--amber-line:#e8c884;
--ff:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
--wrap:1140px;--r:10px;
--sh:0 1px 2px rgba(16,32,52,.06),0 8px 24px rgba(16,32,52,.08);
}
body{font-family:var(--ff);color:var(--ink);background:var(--paper);
line-height:1.62;font-size:17px;-webkit-font-smoothing:antialiased}
img{max-width:100%;height:auto;display:block}
a{color:var(--blue);text-underline-offset:2px}
h1,h2,h3,h4{line-height:1.16;margin:0 0 .5em;letter-spacing:-.017em;font-weight:700}
h1{font-size:clamp(2rem,1.35rem + 2.6vw,3.15rem)}
h2{font-size:clamp(1.5rem,1.2rem + 1.3vw,2.15rem)}
h3{font-size:1.14rem}
p{margin:0 0 1rem}
.wrap{max-width:var(--wrap);margin:0 auto;padding:0 22px}
.skip{position:absolute;left:-9999px;top:0;background:var(--blue);color:#fff;
padding:12px 18px;z-index:200;border-radius:0 0 var(--r) 0}
.skip:focus{left:0}
:focus-visible{outline:3px solid var(--blue-l);outline-offset:2px;border-radius:3px}
.stripe{height:5px;background:linear-gradient(90deg,var(--blue) 0 33.34%,var(--green) 33.34% 66.67%,var(--red) 66.67% 100%)}
.pv{background:var(--amber-bg);border-bottom:1px solid var(--amber-line);color:var(--amber);
font-size:.83rem;line-height:1.5;padding:9px 0}
.pv strong{color:#6b4600}
header{position:sticky;top:0;z-index:100;background:rgba(255,255,255,.97);
backdrop-filter:saturate(140%) blur(8px);border-bottom:1px solid var(--line)}
.bar{display:flex;align-items:center;gap:16px;min-height:66px;
max-width:var(--wrap);margin:0 auto;padding:8px 22px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--blue-d);
font-weight:700;font-size:1.03rem;letter-spacing:-.02em;line-height:1.15;flex:0 0 auto}
.brand span small{display:block;font-weight:600;font-size:.66rem;letter-spacing:.1em;
text-transform:uppercase;color:var(--ink-2)}
nav.nav{display:flex;align-items:center;gap:0;margin-left:auto;flex-wrap:nowrap}
nav.nav a{color:var(--ink);text-decoration:none;font-size:.9rem;font-weight:600;
padding:9px 9px;border-radius:7px;white-space:nowrap}
nav.nav a:hover{background:var(--wash);color:var(--blue)}
nav.nav a[aria-current]{color:var(--blue);box-shadow:inset 0 -2px 0 var(--red)}
.hcall{display:inline-flex;align-items:center;gap:8px;background:var(--red);color:#fff;
text-decoration:none;font-weight:700;padding:11px 16px;border-radius:8px;font-size:.97rem;
white-space:nowrap;margin-left:6px}
.hcall:hover{background:var(--red-d)}
.burger{display:none;margin-left:auto;background:none;border:1px solid var(--line);
border-radius:8px;width:44px;height:44px;padding:0;cursor:pointer}
.burger span{display:block;width:20px;height:2px;background:var(--ink);margin:4px auto;border-radius:2px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;
background:var(--red);color:#fff;text-decoration:none;font-weight:700;font-size:1rem;
padding:14px 22px;border-radius:9px;border:0;cursor:pointer;font-family:inherit;line-height:1.2}
.btn:hover{background:var(--red-d)}
.btn-b{background:var(--blue)}.btn-b:hover{background:var(--blue-d)}
.btn-o{background:transparent;color:var(--blue);border:2px solid var(--blue);padding:12px 20px}
.btn-o:hover{background:var(--blue);color:#fff}
.hero{background:var(--wash);border-bottom:1px solid var(--line);overflow:hidden}
.hero-in{display:grid;grid-template-columns:1.05fr .95fr;
/* max-content on row 1 stops the form (which spans both rows) from inflating the
   copy row and leaving a gap above the photo. */
grid-template-rows:max-content auto;gap:26px 40px;align-items:start;padding:52px 22px 56px}
.hero-copy{grid-column:1;grid-row:1}
.hero-form{grid-column:2;grid-row:1/span 2}
.hero-shot{grid-column:1;grid-row:2}
.eyebrow{font-size:.76rem;font-weight:700;letter-spacing:.11em;text-transform:uppercase;
color:var(--green);margin:0 0 .8rem}
.lede{font-size:1.11rem;color:var(--ink-2);max-width:56ch}
.hero h1{margin-bottom:.55rem}
.hero-photo{border-radius:var(--r);overflow:hidden;box-shadow:var(--sh)}
.hero-photo img{width:100%;aspect-ratio:16/9;object-fit:cover}
.qf{background:#fff;border:1px solid var(--line);border-radius:14px;padding:22px;box-shadow:var(--sh)}
.qf h2{font-size:1.3rem;margin-bottom:.2rem}
.qf .sub{font-size:.92rem;color:var(--ink-2);margin-bottom:1rem}
.qf label{display:block;font-weight:600;font-size:.88rem;margin-bottom:5px}
.qf .hint{font-weight:400;color:var(--ink-2)}
/* Honeypot. A real person never sees this and never tabs into it, so anything
   that ticks it is a bot and Web3Forms drops the submission server side. This
   is display:none on purpose rather than an off-screen input: off-screen fields
   still get filled by password managers and by assistive tech. */
.qf .hp{display:none}
.qf input,.qf select,.qf textarea{width:100%;font-family:inherit;font-size:1rem;
padding:11px 12px;border:1px solid #767f8c;border-radius:8px;background:#fff;color:var(--ink)}
/* #767f8c on #ffffff is 4.05:1. The old #c4ccd6 was 1.62:1, which fails WCAG
   2.2 AA 1.4.11 non-text contrast: the border IS the only thing identifying
   where a form field is, so it has to clear 3:1. */
.qf input:focus,.qf select:focus,.qf textarea:focus{border-color:var(--blue-l)}
.qf .row{margin-bottom:13px}
.qf .two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.qf .btn{width:100%;margin-top:4px}
.qf .note{font-size:.85rem;color:var(--ink-2);margin:12px 0 0;padding-top:12px;border-top:1px solid var(--line)}
.qf .msg{margin:12px 0 0;padding:12px 14px;border-radius:8px;font-size:.92rem;
background:var(--amber-bg);border:1px solid var(--amber-line);color:#6b4600}
@media(max-width:1040px){
 .hero-in{grid-template-columns:1fr;gap:26px;padding:34px 22px 40px}
 /* On a phone the quote form outranks the photo, so it moves above it. */
 .hero-copy,.hero-form,.hero-shot{grid-column:1;grid-row:auto}
 nav.nav{display:none;position:fixed;inset:66px 0 auto;background:#fff;flex-direction:column;
 align-items:stretch;padding:10px 14px 18px;border-bottom:1px solid var(--line);gap:0;
 box-shadow:0 14px 30px rgba(16,32,52,.12);max-height:calc(100vh - 66px);overflow:auto}
 nav.nav.open{display:flex}
 nav.nav a{padding:13px 10px;border-bottom:1px solid var(--line);border-radius:0}
 .hcall{margin-left:auto;padding:10px 13px;font-size:.9rem}
 .burger{display:block;margin-left:0}
 body{padding-bottom:66px}
}
@media(max-width:420px){.hcall span.lbl{display:none}.brand span small{display:none}}
"""

REST_CSS = """
section{padding:58px 0}
section.alt{background:var(--wash);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
section.tight{padding:40px 0}
.narrow{max-width:760px}
.strip{background:var(--blue-d);color:#dbe6f2}
.strip ul{display:flex;flex-wrap:wrap;gap:8px 34px;list-style:none;margin:0;padding:15px 0;
font-size:.9rem;font-weight:600}
.strip li{position:relative;padding-left:17px}
.strip li::before{content:"";position:absolute;left:0;top:.62em;width:7px;height:7px;
border-radius:50%;background:var(--green)}
.strip li:nth-child(2)::before{background:#e8dfd0}
.strip li:nth-child(3)::before{background:var(--red)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(268px,1fr));gap:20px;margin-top:26px}
.card{display:flex;flex-direction:column;background:#fff;border:1px solid var(--line);
border-radius:var(--r);overflow:hidden;text-decoration:none;color:inherit;transition:box-shadow .18s,transform .18s}
.card:hover{box-shadow:var(--sh);transform:translateY(-2px)}
.card img{width:100%;aspect-ratio:16/10;object-fit:cover}
.card .body{padding:17px 18px 20px}
.card h3{margin:0 0 .35em;color:var(--blue-d)}
.card p{margin:0;font-size:.94rem;color:var(--ink-2)}
.card .more{display:inline-block;margin-top:11px;font-weight:700;font-size:.9rem;color:var(--red-d)}
.two-col{display:grid;grid-template-columns:1.1fr .9fr;gap:44px;align-items:start}
.two-col img{border-radius:var(--r);box-shadow:var(--sh);width:100%;aspect-ratio:4/3;object-fit:cover}
.ticks{list-style:none;padding:0;margin:1.1rem 0 0}
.ticks li{position:relative;padding:0 0 .62rem 30px}
.ticks li::before{content:"";position:absolute;left:2px;top:.5em;width:14px;height:8px;
border-left:3px solid var(--green);border-bottom:3px solid var(--green);transform:rotate(-45deg)}
.nums{list-style:none;counter-reset:s;padding:0;margin:1.2rem 0 0}
.nums li{counter-increment:s;position:relative;padding:0 0 1.05rem 46px}
.nums li strong{display:block;color:var(--blue-d)}
.nums li::before{content:counter(s);position:absolute;left:0;top:1px;width:30px;height:30px;
border-radius:50%;background:var(--blue);color:#fff;font-weight:700;font-size:.9rem;
display:grid;place-items:center}
.ba{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:26px;margin-top:24px}
.ba figure{margin:0;background:#fff;border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
.ba .pair{display:grid;grid-template-columns:1fr 1fr;gap:2px;background:var(--line)}
.ba .shot{position:relative;background:#fff}
.ba .shot img{width:100%;aspect-ratio:4/3;object-fit:cover}
.ba .tag{position:absolute;left:9px;top:9px;font-size:.68rem;font-weight:700;letter-spacing:.09em;
text-transform:uppercase;color:#fff;background:var(--ink);padding:4px 9px;border-radius:5px}
.ba .tag.a{background:var(--green)}
.ba figcaption{padding:13px 15px;font-size:.94rem;font-weight:600}
.ba figcaption .ph{display:block;font-weight:400;font-size:.8rem;color:var(--amber);margin-top:3px}
.ph-note{margin-top:20px;background:var(--amber-bg);border:1px solid var(--amber-line);
border-left:5px solid var(--amber-line);border-radius:8px;padding:14px 17px;font-size:.9rem;color:#6b4600}
.ph-note strong{color:#6b4600}
.trust{list-style:none;display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));
gap:2px;background:var(--line);border:1px solid var(--line);border-radius:var(--r);
overflow:hidden;padding:0;margin:24px 0 0}
.trust li{background:#fff;padding:17px 19px}
.trust .k{display:block;font-size:.73rem;font-weight:700;letter-spacing:.09em;
text-transform:uppercase;color:var(--ink-2);margin-bottom:5px}
.trust .v{font-weight:700;color:var(--blue-d)}
.trust .v.pending{color:var(--amber);font-weight:600}
.trust .v.pending::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;
background:var(--amber-line);margin-right:7px;vertical-align:middle}
.towns{margin-top:26px}
.town{border-top:1px solid var(--line);padding:26px 0}
.town:first-child{border-top:0;padding-top:6px}
.town h3{font-size:1.32rem;color:var(--blue-d);margin-bottom:.35em}
.town .facts{list-style:none;display:flex;flex-wrap:wrap;gap:6px 10px;padding:0;margin:0 0 .8rem}
.town .facts li{font-size:.79rem;font-weight:600;color:var(--ink-2);background:var(--wash);
border:1px solid var(--line);border-radius:99px;padding:4px 11px}
.town p{max-width:74ch}
.tier{font-size:.74rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
color:var(--green);margin:34px 0 2px}
details{border:1px solid var(--line);border-radius:var(--r);margin-bottom:10px;background:#fff}
details[open]{box-shadow:var(--sh)}
summary{cursor:pointer;font-weight:700;padding:15px 18px;list-style:none;position:relative;
padding-right:48px;color:var(--blue-d)}
summary::-webkit-details-marker{display:none}
summary::after{content:"";position:absolute;right:20px;top:22px;width:9px;height:9px;
border-right:2.5px solid var(--ink-2);border-bottom:2.5px solid var(--ink-2);
transform:rotate(45deg);transition:transform .16s}
details[open] summary::after{transform:rotate(-135deg);top:26px}
details .in{padding:0 18px 16px}
details .in p:last-child{margin-bottom:0}
.callout{background:var(--wash);border:1px solid var(--line);border-left:5px solid var(--blue);
border-radius:8px;padding:18px 20px;margin:24px 0}
.callout h3,.callout h2{margin-bottom:.35em;color:var(--blue-d);font-size:1.14rem;
line-height:1.25;letter-spacing:-.01em}
.callout p:last-child{margin-bottom:0}
.callout .src{font-size:.82rem;color:var(--ink-2)}
.cta{background:var(--blue-d);color:#fff}
.cta h2{color:#fff}
.cta p{color:#c8d8e8;max-width:58ch}
.cta .big{display:inline-block;font-size:clamp(1.7rem,1.2rem + 2vw,2.5rem);font-weight:700;
color:#fff;text-decoration:none;letter-spacing:-.02em;margin:.3rem 0 1rem}
.cta .big:hover{color:#fff;text-decoration:underline}
.cta .row{display:flex;flex-wrap:wrap;gap:12px}
/* thank-you.html. Numbered "what happens next" list and its button pair. */
.steps{margin:20px 0 0;padding-left:1.3em}
.steps li{margin-bottom:14px;line-height:1.65}
.steps li strong{display:block;color:var(--blue-d)}
.btnrow{display:flex;flex-wrap:wrap;gap:12px}
/* Breadcrumbs. Visible and marked up, so the BreadcrumbList in the JSON-LD
   describes something that is actually on the page. Also gives keyboard users
   a one-tab route back up the tree instead of hunting the nav. */
.crumbs{background:var(--wash);border-bottom:1px solid var(--line);font-size:.83rem}
.crumbs ol{list-style:none;display:flex;flex-wrap:wrap;gap:0;margin:0;padding:9px 0}
.crumbs li{color:var(--ink-2)}
.crumbs li+li::before{content:"/";margin:0 8px;color:#8a94a3}
.crumbs a{color:var(--blue);text-decoration:none}
.crumbs a:hover{text-decoration:underline}
.crumbs [aria-current]{font-weight:600;color:var(--ink-2)}
/* The "worth reading first" block on a service page, and the notes teaser on
   the home page. This is the pillar linking down into the cluster, so it is a
   real list of real headlines, not a row of pills. */
.reads{list-style:none;padding:0;margin:22px 0 0;display:grid;gap:14px}
.reads li{border:1px solid var(--line);border-left:4px solid var(--green);border-radius:var(--r);
padding:15px 18px;background:#fff}
.reads h3{margin:0 0 .3em;font-size:1.03rem;line-height:1.3}
.reads h3 a{color:var(--blue-d);text-decoration:none}
.reads h3 a:hover{text-decoration:underline}
.reads h4{margin:0 0 .3em;font-size:1rem;line-height:1.3}
.reads h4 a{color:var(--blue-d);text-decoration:none}
.reads h4 a:hover{text-decoration:underline}
.reads p{margin:0;font-size:.9rem;color:var(--ink-2)}
/* City pages. .chips is the fact panel at the top of every town page: the
   published figures, stated before any sales copy, because the figures are the
   reason the page is allowed to exist. */
.chips{list-style:none;display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));
gap:1px;background:var(--line);border:1px solid var(--line);border-radius:var(--r);
overflow:hidden;padding:0;margin:22px 0 24px}
.chips li{background:#fff;padding:12px 15px}
.chips .k{display:block;font-size:.68rem;font-weight:700;letter-spacing:.08em;
text-transform:uppercase;color:var(--ink-2);margin-bottom:3px}
.chips .v{font-weight:700;color:var(--blue-d);font-size:1.02rem}
.areas-list{grid-template-columns:repeat(auto-fit,minmax(252px,1fr))}
.notes{list-style:none;padding:0;margin:18px 0 4px;display:grid;gap:10px}
.notes li{border-left:3px solid var(--green);padding:2px 0 2px 14px;font-size:.95rem;
color:var(--ink-2)}
.notes strong{color:var(--blue-d)}
.city-body h2{margin-top:1.9em}
.city-body h2:first-child{margin-top:0}
.src{font-size:.85rem;color:var(--ink-2);margin-top:22px}
.posts{list-style:none;padding:0;margin:26px 0 0;display:grid;gap:18px}
.posts li{border:1px solid var(--line);border-radius:var(--r);padding:20px 22px;background:#fff}
.posts h3{margin-bottom:.3em}
.posts h3 a{color:var(--blue-d);text-decoration:none}
.posts h3 a:hover{text-decoration:underline}
.posts time{font-size:.82rem;color:var(--ink-2);font-weight:600}
.posts p{margin:.4rem 0 0;color:var(--ink-2);font-size:.95rem}
.empty{border:2px dashed var(--line);border-radius:var(--r);padding:30px 24px;
text-align:center;color:var(--ink-2);margin-top:24px}
.post{padding:46px 0 10px}
.post h1{font-size:clamp(1.72rem,1.2rem + 1.9vw,2.5rem)}
.post .post-meta{font-size:.86rem;color:var(--ink-2);font-weight:600;margin-top:-.4rem}
.post-hero{margin:26px 0 0}
.post-hero img{width:100%;border-radius:var(--r);box-shadow:var(--sh)}
.cred,.prose figcaption{font-size:.8rem;color:var(--ink-2);margin-top:8px}
.prose{padding-top:26px;padding-bottom:44px}
.prose h2{margin:2.1rem 0 .6rem;font-size:1.62rem;color:var(--blue-d);scroll-margin-top:88px}
.prose h3{margin:1.6rem 0 .4rem;font-size:1.14rem;scroll-margin-top:88px}
.prose p{margin:0 0 1.05rem}
.prose ul.md,.prose ol.md{margin:0 0 1.15rem;padding-left:1.35rem}
.prose li{margin-bottom:.5rem}
.prose blockquote{margin:1.4rem 0;padding:2px 0 2px 20px;border-left:4px solid var(--green);
color:var(--ink-2);font-style:italic}
.prose hr{border:0;border-top:1px solid var(--line);margin:2.2rem 0}
.prose figure{margin:1.8rem 0}
.prose figure svg{max-width:100%;height:auto;display:block;background:#fff;
border:1px solid var(--line);border-radius:var(--r)}
/* Tables can be wider than a phone. They scroll inside their own box so the
   page body never scrolls sideways. */
.tw{overflow-x:auto;margin:1.3rem 0;border:1px solid var(--line);border-radius:var(--r)}
.tw table{border-collapse:collapse;width:100%;font-size:.93rem;min-width:min(560px,100%)}
.tw th,.tw td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);
vertical-align:top}
.tw th{background:var(--wash);font-size:.79rem;letter-spacing:.05em;text-transform:uppercase;
color:var(--ink-2);white-space:nowrap}
.tw tr:last-child td{border-bottom:0}
.pills{display:flex;flex-wrap:wrap;gap:9px;margin-top:14px}
.pill{display:inline-block;background:#fff;border:1px solid var(--line);border-radius:99px;
padding:8px 15px;font-size:.9rem;font-weight:600;color:var(--blue-d);text-decoration:none}
.pill:hover{border-color:var(--blue);background:var(--wash)}
.pill .mi{color:var(--ink-2);font-weight:600;font-size:.8em}
footer{background:var(--blue-d);color:#b8cadd;font-size:.92rem;padding:44px 0 26px}
footer a{color:#fff}
.foot{display:grid;grid-template-columns:1.25fr 1fr 1fr;gap:32px}
/* .fh is on an h2. The footer column headings used to be h4, which skipped a
   level from the last h2 in <main> on literally every page. Level is semantics,
   size is style: the size lives here. */
footer h4,footer .fh{color:#fff;font-size:.76rem;letter-spacing:.1em;text-transform:uppercase;
margin:0 0 .8em;font-weight:700;line-height:1.3}
footer address{font-style:normal;line-height:1.75}
.fl{list-style:none;padding:0;margin:0;line-height:2}
.fl a{text-decoration:none}
.fl a:hover{text-decoration:underline}
.legal{border-top:1px solid rgba(255,255,255,.16);margin-top:32px;padding-top:18px;font-size:.82rem;color:#94aac2}
.mbar{display:none}
@media(max-width:1040px){
 section{padding:40px 0}
 .two-col{grid-template-columns:1fr;gap:24px}
 .foot{grid-template-columns:1fr;gap:24px}
 .mbar{display:grid;grid-template-columns:1fr 1fr;gap:1px;position:fixed;left:0;right:0;bottom:0;
 z-index:99;background:var(--line);box-shadow:0 -3px 14px rgba(16,32,52,.13)}
 .mbar a{padding:16px 8px;text-align:center;font-weight:700;text-decoration:none;font-size:.97rem}
 .mbar .c{background:var(--red);color:#fff}
 .mbar .q{background:#fff;color:var(--blue-d)}
}
@media(max-width:560px){
 .ba .pair{grid-template-columns:1fr}
 .qf .two{grid-template-columns:1fr}
}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;
scroll-behavior:auto!important}}
@media print{header,.mbar,.qf,.pv,.cta{display:none}body{font-size:12pt}}
"""

# =============================================================================
# JS
# =============================================================================
# Runs on every page, so nothing here may assume an element exists. One null
# dereference throws and takes the whole file down with it.

APP_JS = """(function(){
 'use strict';
 var $=function(id){return document.getElementById(id);};

 // ---- mobile nav ---------------------------------------------------------
 var burger=$('burger'), nav=$('nav');
 if(burger&&nav){
  var set=function(open){
   nav.classList.toggle('open',open);
   burger.setAttribute('aria-expanded',open?'true':'false');
  };
  burger.addEventListener('click',function(){set(!nav.classList.contains('open'));});
  nav.addEventListener('click',function(e){if(e.target.tagName==='A')set(false);});
  document.addEventListener('keydown',function(e){
   if(e.key==='Escape'&&nav.classList.contains('open')){set(false);burger.focus();}
  });
  window.addEventListener('resize',function(){
   if(window.innerWidth>1040&&nav.classList.contains('open'))set(false);
  });
 }

 // ---- quote form ---------------------------------------------------------
 // Three jobs, in this order:
 //   1. Refuse to submit into a void when no access key is configured.
 //   2. Catch the empty required field before the round trip.
 //   3. Rewrite the subject line so the notification is readable on a phone
 //      without opening it: "New lead: Interior painting in Palos Hills".
 // On success the browser follows the hidden redirect field to thank-you.html.
 // There is deliberately no CAPTCHA. The honeypot below plus the relay's own
 // server-side filtering carry the spam load, because a CAPTCHA on a
 // contractor quote form costs more real leads than it blocks fake ones.
 var form=$('quote-form'), msg=$('quote-msg');
 if(form&&msg){
  var dead=form.getAttribute('data-endpoint')!=='1';
  var sent=false;
  var show=function(html,focusEl){
   msg.hidden=false;
   msg.innerHTML=html;
   if(focusEl)focusEl.focus();
  };
  var phone=function(){
   return '<a href="tel:'+form.getAttribute('data-tel')+'">'+
    form.getAttribute('data-phone')+'</a>';
  };
  form.addEventListener('submit',function(e){
   // Double submit guard. An impatient second tap on a slow phone connection
   // is the easiest way to send Mike the same lead twice.
   if(sent){e.preventDefault();return;}

   // Honeypot. A human cannot see or tab to this box, so a tick means a bot.
   // Fail quietly: telling a bot why it was blocked just helps it adapt.
   var hp=$('qf-botcheck');
   if(hp&&hp.checked){e.preventDefault();return;}

   var bad=null, i, f=form.querySelectorAll('[required]');
   for(i=0;i<f.length;i++){
    if(!f[i].value.trim()){bad=f[i];break;}
   }
   if(bad){
    e.preventDefault();
    show('Please add your '+(bad.getAttribute('data-label')||'details')+
     ', or just call '+phone()+'.',bad);
    return;
   }

   // Email is optional, but a typed one that cannot work is worse than a blank
   // one: it makes Mike think he has a way to reply when he does not.
   var em=$('qf-email');
   if(em&&em.value.trim()){
    var v=em.value.trim(), at=v.indexOf('@'), dot=v.lastIndexOf('.');
    if(at<1||dot<at+2||dot===v.length-1||v.indexOf(' ')>-1){
     e.preventDefault();
     show('That email address looks incomplete. Fix it, clear it, or just call '+
      phone()+'.',em);
     return;
    }
   }

   if(dead){
    e.preventDefault();
    show('This form is not connected yet. Call or text '+phone()+
     ' and you will get a faster answer anyway.');
    return;
   }

   // Subject line. Mike reads this on a phone between jobs, so it has to say
   // what it is, what the work is and where, before he opens anything.
   var svc=$('qf-service'), twn=$('qf-town'), subj=form.querySelector('input[name=subject]');
   if(subj){
    var s='New lead: '+(svc&&svc.value?svc.value:'quote request');
    if(twn&&twn.value.trim())s+=' in '+twn.value.trim();
    // ASCII only. Anything else garbles in the phone notification.
    subj.value=s.replace(/[^\\x20-\\x7E]/g,'');
   }

   sent=true;
   var btn=form.querySelector('button[type=submit]');
   if(btn){btn.disabled=true;btn.textContent='Sending...';}
   show('Sending. If this does not move, call '+phone()+'.');
  });
 }
})();
"""

# =============================================================================
# LOGO
# =============================================================================
# Placeholder mark only. The real logo is multicolor paint splatters on white
# and is on the van. Get the artwork (or a clean photo of the van) from Mike and
# replace this. It is a stand-in for layout, not a rebrand.

LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" role="img" aria-label="">
<circle cx="13" cy="13" r="9" fill="#12406f"/>
<circle cx="26" cy="17" r="7.5" fill="#146c3d" fill-opacity=".9"/>
<circle cx="18" cy="27" r="8" fill="#b8271d" fill-opacity=".88"/>
<circle cx="31" cy="30" r="3.2" fill="#12406f" fill-opacity=".75"/>
<circle cx="6" cy="28" r="2.4" fill="#146c3d" fill-opacity=".8"/>
</svg>
"""

# =============================================================================
# SHELL
# =============================================================================

def canonical_url(relpath):
    """The canonical URL for a built file.

    A static host serves blog/index.html at /blog/ and index.html at /. The
    canonical, the og:url and the sitemap must all name that same served URL,
    not the file name, or the three disagree and Google picks one at random.
    """
    u = SITE + "/" + relpath.replace(os.sep, "/")
    if u.endswith("/index.html"):
        u = u[: -len("index.html")]
    return u


def social_title(title):
    """The brand suffix is already in og:site_name, so repeating it in the card
    headline just eats the visible line. Strip it for the social title only."""
    tail = " | " + BRAND
    return title[: -len(tail)] if title.endswith(tail) else title


def head(title, desc, canon, ogkey, up="", og_type="website", og_image=None,
         og_image_alt=None, og_image_wh=None, extra_meta="", always_noindex=False):
    """One head for every page.

    NOTE ON PRECONNECT: there is deliberately no preconnect, dns-prefetch or
    font preload here. The site uses the system font stack and loads nothing
    from a third-party origin, so a preconnect would open a connection to
    nowhere and cost a DNS lookup for no benefit. Add one only if a webfont or
    an external script is ever introduced.
    """
    robots = ""
    if always_noindex:
        # PERMANENT, unlike the preview flag below. This one does NOT come off at
        # go-live. A thank-you page ranks for nothing, and once indexed it starts
        # collecting direct entrances from people who never filled the form in,
        # which quietly ruins every conversion count pointed at it.
        robots = ('<!-- PERMANENT noindex. This does NOT come off at go-live, unlike the\n'
                  '     preview flag on the other pages. An indexed thank-you page ruins\n'
                  '     the conversion count it exists to produce. -->\n'
                  '<meta name="robots" content="noindex, nofollow">\n')
    elif NOINDEX:
        robots = ('<!-- PREVIEW BUILD. This noindex is TEMPORARY. Remove it at go-live by\n'
                  '     setting NOINDEX = False in build.py and re-running. A site left\n'
                  '     noindexed by accident is the most common way a launch like this\n'
                  '     quietly produces nothing for six months. -->\n'
                  '<meta name="robots" content="noindex, nofollow">\n')
    else:
        robots = ('<meta name="robots" content="index, follow, max-image-preview:large, '
                  'max-snippet:-1">\n')
    if og_image:
        og = og_image
        og_alt = og_image_alt or ""
        wh = og_image_wh
    else:
        og = SITE + "/images/" + IMG[ogkey]["file"]
        og_alt = IMG[ogkey]["alt"]
        wh = (IMG[ogkey]["w"], IMG[ogkey]["h"])
    dims = ""
    if wh:
        dims = ('<meta property="og:image:width" content="' + str(wh[0]) + '">\n'
                '<meta property="og:image:height" content="' + str(wh[1]) + '">\n')
    canon_url = canonical_url(canon)
    st = esc(social_title(title))
    return ('<!DOCTYPE html>\n<html lang="en">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<!-- Generated by build.py. Do not hand-edit: edit build.py and re-run. -->\n'
            + robots +
            '<title>' + esc(title) + '</title>\n'
            '<meta name="description" content="' + esc(desc) + '">\n'
            '<link rel="canonical" href="' + canon_url + '">\n'
            '<meta name="theme-color" content="#12406f">\n'
            '<meta name="format-detection" content="telephone=yes">\n'
            '<meta property="og:type" content="' + og_type + '">\n'
            '<meta property="og:site_name" content="' + BRAND + '">\n'
            '<meta property="og:locale" content="en_US">\n'
            '<meta property="og:title" content="' + st + '">\n'
            '<meta property="og:description" content="' + esc(desc) + '">\n'
            '<meta property="og:url" content="' + canon_url + '">\n'
            '<meta property="og:image" content="' + og + '">\n'
            + dims +
            '<meta property="og:image:alt" content="' + esc(og_alt) + '">\n'
            + extra_meta +
            '<meta name="twitter:card" content="summary_large_image">\n'
            '<meta name="twitter:title" content="' + st + '">\n'
            '<meta name="twitter:description" content="' + esc(desc) + '">\n'
            '<meta name="twitter:image" content="' + og + '">\n'
            '<meta name="twitter:image:alt" content="' + esc(og_alt) + '">\n'
            '<link rel="icon" href="' + up + 'logo.svg" type="image/svg+xml">\n'
            '<style>' + CRITICAL_CSS.strip() + '</style>\n'
            '<link rel="preload" as="style" href="' + up + 'style.css?v=' + ASSET_V +
            '" onload="this.onload=null;this.rel=\'stylesheet\'">\n'
            '<noscript><link rel="stylesheet" href="' + up + 'style.css?v=' + ASSET_V + '"></noscript>\n'
            '</head>\n<body>\n'
            '<a class="skip" href="#main">Skip to content</a>\n')


def preview_bar():
    if not (NOINDEX and PREVIEW_BANNER):
        return ""
    return ('<div class="pv"><div class="wrap">'
            '<strong>Preview build, not live.</strong> All photos are stock, including the '
            'before and after pairs. License, insurance, warranty and hours are blank because no '
            'real values have been supplied, and the town list still needs ' + OWNER + ' to '
            'confirm it. Set to noindex until that is settled.'
            '</div></div>\n')


def header(active="", up=""):
    links = ""
    for label, href in NAV:
        cur = ' aria-current="page"' if href == active else ""
        links += '<a href="' + up + href + '"' + cur + '>' + label + '</a>'
    cur_c = ' aria-current="page"' if active == "contact.html" else ""
    links += '<a href="' + up + 'contact.html"' + cur_c + '>Contact</a>'
    return ('<div class="stripe" aria-hidden="true"></div>\n'
            + preview_bar() +
            '<header>\n  <div class="bar">\n'
            '    <a class="brand" href="' + up + 'index.html">'
            '<img src="' + up + 'logo.svg" width="34" height="34" alt="" aria-hidden="true">'
            # The tagline is the SCOPE line, so it names the region. The
            # Bridgeview address is a fact and it stays, in the footer NAP block
            # and on the contact page, where an address belongs.
            '<span>Colors Your Way USA<small>Painting &amp; remodeling &middot; Chicago '
            '&amp; the south suburbs</small></span></a>\n'
            '    <button class="burger" id="burger" aria-label="Menu" aria-expanded="false" '
            'aria-controls="nav"><span></span><span></span><span></span></button>\n'
            '    <nav class="nav" id="nav" aria-label="Main">' + links + '</nav>\n'
            '    <a class="hcall" href="tel:' + PHONE_E164 + '" '
            'aria-label="Call ' + BRAND + ' on ' + PHONE_DISPLAY + '">'
            '<span aria-hidden="true">&#9742;</span> '
            '<span class="lbl" aria-hidden="true">' + PHONE_DISPLAY + '</span></a>\n'
            '  </div>\n</header>\n')


def quote_form(heading, sub, page="", up=""):
    """The one form on the page. One per page, never two, because two forms mean
    two sets of duplicated ids and a screen reader that reads the second set as
    broken.

    Field ORDER is load-bearing, not cosmetic. Web3Forms builds the notification
    email in the order the inputs appear in the DOM, and Mike reads that email on
    a phone standing in somebody's kitchen. So the order is what he needs first:
    name, phone, email, service, town, details, and the page it came from. Do not
    reorder these to suit the layout.
    """
    live = bool(FORM_ACCESS_KEY)
    action = FORM_ENDPOINT if live else "#"
    has = "1" if live else "0"
    # Method matters when the key is missing. A POST to "#" on GitHub Pages is a
    # POST to a static .html, which answers 405 and throws the visitor onto an
    # error page. That IS submitting into a void, and app.js only prevents it
    # while JavaScript is on. So with no key the form is GET, and the submit
    # button is replaced below by a tel: link, which means there is no submit
    # control at all and no implicit submission either (the form has four text
    # fields, so Enter does nothing). Degraded with JavaScript off as well.
    method = "post" if live else "get"

    if live:
        # access_key, subject, from_name and redirect are all reserved names that
        # the relay consumes rather than printing, so they are safe at the top.
        hidden = ('\n  <input type="hidden" name="access_key" value="' + esc(FORM_ACCESS_KEY) + '">'
                  '\n  <input type="hidden" name="subject" value="' + esc(FORM_SUBJECT_FALLBACK) + '">'
                  '\n  <input type="hidden" name="from_name" value="' + esc(BRAND) + ' website">'
                  '\n  <input type="hidden" name="redirect" value="' + esc(FORM_REDIRECT) + '">')
        # "page" is NOT reserved, so it does print, which means its position in
        # the DOM is its position in Mike's email. It goes LAST, after the
        # details. It is the least urgent line and it must not push the phone
        # number down the screen.
        #
        # Call sites pass display labels that already contain HTML entities
        # (s["nav"] is "Drywall &amp; repair"). Feeding that straight to esc()
        # double-escapes it into "&amp;amp;" and Mike's email reads
        # "Drywall &amp; repair". Decode the entities back to text FIRST, then
        # escape once for the attribute.
        label = re.sub(r"<[^>]+>", "", page or "unknown")
        for ent, ch in (("&middot;", "-"), ("&rsquo;", "'"), ("&nbsp;", " "),
                        ("&quot;", '"'), ("&lt;", "<"), ("&gt;", ">"),
                        ("&amp;", "&")):
            label = label.replace(ent, ch)
        tail = ('\n  <input type="hidden" name="page" value="' + esc(label) + '">')
        notice = ""
    else:
        hidden = ("\n  <!-- TO SUPPLY: FORM_ACCESS_KEY is empty in build.py, so this form has no\n"
                  "       delivery address and posts nowhere. Get the key (README.md step 1),\n"
                  "       paste it in, re-run, and test with a real submission. Until then the\n"
                  "       visible notice below and app.js both point the visitor at the phone. -->")
        tail = ""
        notice = ('\n  <p class="msg" style="display:block;background:#fff6e5;border-left:3px solid '
                  '#b8271d;padding:10px 12px;margin:0 0 14px">'
                  '<strong>This form is not connected yet.</strong> Call or text '
                  '<a href="tel:' + PHONE_E164 + '">' + PHONE_DISPLAY + '</a> and you will get a '
                  'faster answer anyway.</p>')

    # The action control. Live: a real submit button. Dead: a phone link, so a
    # visitor with JavaScript off is never handed a button that goes nowhere.
    if live:
        submit = '<button class="btn" type="submit">Ask for a quote</button>'
    else:
        submit = ('<a class="btn" href="tel:' + PHONE_E164 + '">Call or text ' +
                  PHONE_DISPLAY + '</a>')

    opts = "".join('<option>' + o + '</option>' for o in JOB_TYPES)
    return ('<form class="qf" id="quote-form" method="' + method + '" action="' + action + '" '
            'data-endpoint="' + has + '" data-phone="' + PHONE_DISPLAY + '" '
            'data-tel="' + PHONE_E164 + '" data-brand="' + esc(BRAND) + '" novalidate>' + hidden + '''
  <h2>''' + heading + '''</h2>
  <p class="sub">''' + sub + '''</p>''' + notice + '''
  <div class="row two">
    <div>
      <label for="qf-name">Your name</label>
      <input id="qf-name" name="name" type="text" autocomplete="name" required data-label="name">
    </div>
    <div>
      <label for="qf-phone">Phone</label>
      <input id="qf-phone" name="phone" type="tel" inputmode="tel" autocomplete="tel" required data-label="phone number">
    </div>
  </div>
  <div class="row">
    <label for="qf-email">Email <span class="hint">optional, calling is quicker</span></label>
    <input id="qf-email" name="email" type="email" autocomplete="email" data-label="email">
  </div>
  <div class="row">
    <label for="qf-service">What needs doing</label>
    <select id="qf-service" name="service">''' + opts + '''</select>
  </div>
  <div class="row">
    <label for="qf-town">Your town <span class="hint">so we know how far out you are</span></label>
    <input id="qf-town" name="town" type="text" autocomplete="address-level2" required data-label="town">
  </div>
  <div class="row">
    <label for="qf-details">Anything else <span class="hint">optional, but it helps</span></label>
    <textarea id="qf-details" name="details" rows="3" placeholder="How many rooms, roughly how old the house is, and what is bothering you about it"></textarea>
  </div>''' + tail + '''
  <div class="hp" aria-hidden="true">
    <label for="qf-botcheck">Leave this empty</label>
    <input id="qf-botcheck" type="checkbox" name="botcheck" tabindex="-1" autocomplete="off">
  </div>
  ''' + submit + '''
  <p class="msg" id="quote-msg" role="status" hidden></p>
  <p class="note"><strong>A photo tells us more than anything you can type.</strong>
  Text us a picture of the room, the wall or the front of the house at
  <a href="sms:''' + PHONE_E164 + '''">''' + PHONE_DISPLAY + '''</a>. It will not be the final
  price, because nothing gets priced without somebody standing in front of it, but it lets us
  tell you what to expect before we come out.</p>
</form>
''')


def trust_row(up=""):
    """License, insurance and warranty. Every value is None and every None
    renders as a visible pending slot. Nothing here is ever invented."""
    rows = [
        ("Insurance", TRUST["insurance"]),
        ("Local registration", TRUST["license"]),
        ("Workmanship guarantee", TRUST["warranty"]),
        ("Lead-safe certification", TRUST["epa_rrp"]),
    ]
    out = '<ul class="trust">'
    for k, v in rows:
        if v:
            out += '<li><span class="k">' + k + '</span><span class="v">' + esc(v) + '</span></li>'
        else:
            out += ('<li><span class="k">' + k + '</span>'
                    '<span class="v pending">To supply</span></li>')
    out += "</ul>"
    return out


def ba_gallery(pairs):
    """Before and after pairs.

    Painting sells on before and after, so the component is built properly now
    and the photos get swapped later. What it must never do is present stock as
    a real job. Every pair is labeled on the page and in the markup.
    """
    out = '<div class="ba">'
    for before, after, caption in pairs:
        out += ('<figure>'
                '<div class="pair">'
                '<div class="shot"><span class="tag">Before</span>' + img(before) + '</div>'
                '<div class="shot"><span class="tag a">After</span>' + img(after) + '</div>'
                '</div>'
                '<figcaption>' + caption +
                '<span class="ph">Stock placeholder. Not a Colors Your Way USA job.</span>'
                '</figcaption></figure>')
    out += "</div>"
    out += ('<p class="ph-note"><strong>These are placeholders.</strong> They are stock '
            'photographs and the two halves of each pair are not the same room. Real before '
            'and after pairs from ' + OWNER + '&rsquo;s own jobs go here before this site goes '
            'live. That swap will do more for this page than anything else on it.</p>')
    return out


def faq(items):
    rows = ""
    for q, a in items:
        rows += ('<details><summary>' + q + '</summary><div class="in"><p>' + a + '</p></div></details>\n')
    ld = {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q,
         "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}}
        for q, a in items]}
    return rows, ld


def cta(up=""):
    return ('<section class="cta">\n  <div class="wrap">\n'
            '    <p class="eyebrow" style="color:#8fd3aa">Ready when you are</p>\n'
            '    <h2>Give us a call and we will come and look at it.</h2>\n'
            '    <p>Tell us your town and what you want done, and we will set a time to come and '
            'see it. You get a real number once somebody has stood in the room, not a guess over '
            'the phone. ' + OWNER + ' owns the company and runs the crew, so you are talking to '
            'the person responsible for the work.</p>\n'
            '    <a class="big" href="tel:' + PHONE_E164 + '">' + PHONE_DISPLAY + '</a>\n'
            '    <div class="row"><a class="btn" href="tel:' + PHONE_E164 + '">Call now</a>'
            '<a class="btn btn-b" href="' + up + 'contact.html#quote">Rather type it out?</a></div>\n'
            '  </div>\n</section>\n')


def footer(up=""):
    navlinks = "".join('<li><a href="' + up + h + '">' + t + '</a></li>' for t, h in FOOT_NAV)
    # The footer carries the region groups, not 76 town names. A footer link
    # block that lists every location page on the site is the oldest programmatic
    # SEO tell there is, it pushes the real navigation off the screen on a phone,
    # and it spreads the same 76 links across every page so none of them mean
    # anything. Regions plus the close ring is a real navigation aid: it answers
    # "is my area on here" in one glance and hands the rest to the hub.
    regions = "".join('<li><a href="' + up + 'areas/index.html#' + k + '">' + label +
                      "</a></li>" for k, label, _ in REGIONS)
    # Every entry points at its own page under areas/, Bridgeview included. It
    # used to be the exception, redirected to the home page, because the home
    # page carried the Bridgeview head term. The home page is regional now, so
    # the conflict is gone and the town links like every other town.
    close = ", ".join(
        '<a href="' + up + "areas/" + q["slug"] + '.html">' + q["name"] + "</a>"
        for q in built_places()[:10])
    hours = TRUST["hours"] if TRUST["hours"] else "Hours to supply"
    # Headings here are h2, not h4. They sit at the top level of the footer, so
    # h4 skipped from the last h2 on the page straight to h4 and broke the
    # heading outline on every single page. Styling comes from .fh, not the tag.
    return ('<footer>\n  <div class="wrap">\n    <div class="foot">\n'
            '      <div>\n'
            '        <h2 class="fh">' + BRAND + '</h2>\n'
            '        <address>' + STREET + '<br>' + CITY + ', ' + REGION + ' ' + POSTAL + '<br>'
            '<a href="tel:' + PHONE_E164 + '">' + PHONE_DISPLAY + '</a></address>\n'
            '        <p style="margin-top:12px">Painting and remodeling, inside and out. Owned '
            'and run by ' + OWNER + '. Call and you get the company, not a call center.</p>\n'
            '        <p style="font-size:.84rem">' + hours + '</p>\n'
            '      </div>\n'
            '      <nav aria-label="Footer">\n        <h2 class="fh">Work</h2>\n'
            '        <ul class="fl">' + navlinks +
            '<li><a href="' + up + 'blog/index.html">Notes</a></li>'
            '<li><a href="' + up + 'contact.html">Contact</a></li></ul>\n      </nav>\n'
            '      <div>\n        <h2 class="fh">Where we work</h2>\n'
            '        <ul class="fl">' + regions + '</ul>\n'
            '        <p style="font-size:.86rem;line-height:1.8;margin-top:10px">Closest towns to '
            'the shop: ' + close + '.</p>\n'
            '        <p style="font-size:.86rem"><a href="' + up + 'areas/index.html">'
            'See all ' + str(len(built_places())) + ' towns we cover</a></p>\n'
            '      </div>\n'
            '    </div>\n'
            '    <p class="legal">&copy; 2026 ' + BRAND + '. ' + STREET + ', ' + CITY + ', '
            + REGION + ' ' + POSTAL + '. ' + PHONE_DISPLAY + '.</p>\n'
            '  </div>\n</footer>\n'
            '<div class="mbar">\n'
            '  <a class="c" href="tel:' + PHONE_E164 + '">Call ' + PHONE_DISPLAY + '</a>\n'
            '  <a class="q" href="' + up + 'contact.html#quote">Get a quote</a>\n'
            '</div>\n'
            '<script src="' + up + 'app.js?v=' + ASSET_V + '"></script>\n')


def confirm_comment():
    if not NOINDEX:
        return ""
    body = "\n".join("  - " + re.sub(r"\s+", " ", c) for c in CONFIRM)
    return ("<!--\n  NEEDS OWNER SIGN-OFF BEFORE THIS SITE IS INDEXED\n" + body + "\n-->\n")


# =============================================================================
# STRUCTURED DATA
# =============================================================================
# HousePainter is a subtype of LocalBusiness and is the closest match Schema.org
# has. No aggregateRating and no review markup: there are no reviews, and
# inventing them would violate Google's structured data policy on top of the
# house rules. No priceRange either, because no price has been established.

# areaServed is built from the place table, so the markup can never drift from
# the pages that actually exist. Only the MUNICIPALITIES go in the business-wide
# list. The 22 Chicago community areas are inside the City of Chicago, which is
# already in the list, so repeating them here would add 22 entries to the graph
# on every page of the site to say something the Chicago entry already says.
# Each neighborhood page names itself as a Place on its own Service node, which
# is where that statement belongs and where it is actually specific.
def area_served():
    out = []
    for p in built_places():
        if p["kind"] == "town":
            out.append({"@type": "City", "name": p["name"] + ", IL"})
    return out


def ld_json(extra=None):
    biz = {
        "@type": ["HousePainter", "GeneralContractor"],
        "@id": SITE + "/#business",
        "name": BRAND,
        "alternateName": "Colors Your Way",
        "description": ("Painting and remodeling contractor based in Bridgeview, Illinois. "
                        "Interior and exterior painting, cabinet refinishing, drywall repair, "
                        "carpentry, tile, flooring and general remodeling across Chicago and the "
                        "south and southwest suburbs."),
        "url": SITE + "/",
        "telephone": PHONE_E164,
        "image": SITE + "/images/" + IMG["hero-home"]["file"],
        "logo": SITE + "/logo.svg",
        "founder": {"@type": "Person", "name": OWNER},
        "address": {
            "@type": "PostalAddress",
            "streetAddress": STREET,
            "addressLocality": CITY,
            "addressRegion": REGION,
            "postalCode": POSTAL,
            "addressCountry": "US",
        },
        "areaServed": area_served(),
        "knowsAbout": ["Interior painting", "Exterior painting", "Cabinet refinishing",
                       "Drywall repair", "Trim carpentry", "Tile", "Flooring",
                       "Subfloor repair", "Concrete", "Faux finishes", "Remodeling"],
        "contactPoint": {"@type": "ContactPoint", "telephone": PHONE_E164,
                         "contactType": "customer service", "areaServed": "US",
                         "availableLanguage": "English"},
    }
    graph = [biz]
    if extra:
        graph += extra if isinstance(extra, list) else [extra]
    return ('<script type="application/ld+json">'
            + json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=1)
            + '</script>\n')


def service_ld(name, desc, url):
    return {
        "@type": "Service",
        "@id": canonical_url(url) + "#service",
        "name": name,
        "description": desc,
        "serviceType": name,
        "url": canonical_url(url),
        "provider": {"@id": SITE + "/#business"},
        "areaServed": area_served(),
        "audience": {"@type": "Audience", "audienceType":
                     "Homeowners, landlords and property managers"},
    }


def breadcrumbs(trail, up=""):
    """Visible breadcrumb nav plus the matching BreadcrumbList.

    `trail` is a list of (label, href_or_None). The last item is the current
    page and carries no link. Emitted on every page except the home page, where
    a one-item breadcrumb is noise. Returns (html, jsonld).

    The visible markup and the JSON-LD are generated from the same list on
    purpose. Structured data that describes a breadcrumb the page does not
    actually show is the most common way this markup ends up wrong.
    """
    items, crumbs = [], []
    for i, (label, href) in enumerate(trail):
        if href and i < len(trail) - 1:
            items.append('<li><a href="' + up + href + '">' + label + "</a></li>")
        else:
            items.append('<li><span aria-current="page">' + label + "</span></li>")
        node = {"@type": "ListItem", "position": i + 1, "name": re.sub(r"<[^>]+>", "", label)}
        if href:
            node["item"] = canonical_url(href)
        crumbs.append(node)
    html = ('<nav class="crumbs" aria-label="Breadcrumb"><div class="wrap">'
            '<ol>' + "".join(items) + "</ol></div></nav>\n")
    return html, {"@type": "BreadcrumbList",
                  "itemListElement": crumbs}


def webpage_ld(url, name, desc, crumb_id=None):
    node = {
        "@type": "WebPage",
        "@id": canonical_url(url) + "#webpage",
        "url": canonical_url(url),
        "name": name,
        "description": desc,
        "isPartOf": {"@id": SITE + "/#website"},
        "about": {"@id": SITE + "/#business"},
        "inLanguage": "en-US",
    }
    return node


def website_ld():
    return {"@type": "WebSite", "@id": SITE + "/#website", "url": SITE + "/",
            "name": BRAND, "publisher": {"@id": SITE + "/#business"},
            "inLanguage": "en-US"}


# =============================================================================
# PAGE CONTENT
# =============================================================================

SERVICES = [
 dict(slug="interior-painting", nav="Interior", card="Interior painting", hero="hero-interior",
      title="Interior Painting in Chicagoland | Colors Your Way USA",
      desc=("Walls, ceilings, trim and doors painted properly, across Chicago and the south and "
            "southwest suburbs. We prep first and put the room back. Call "
            + PHONE_DISPLAY + "."),
      h1="Interior painting for rooms that have started to look tired.",
      lede=("Scuffed hallways, a kitchen ceiling that has gone yellow, trim that has been "
            "painted so many times the detail has disappeared. We paint walls, ceilings, trim "
            "and doors across Chicago and the south and southwest suburbs. We do the patching "
            "and the sanding first, because that is what decides how it looks in five years. We "
            "move the furniture, we cover the floors, and we put the room back when we are done."),
      formhead="Get an interior quote",
      formsub="Tell us which rooms and what town you are in.",
      situations=[
        ("The whole place has just gone dull",
         "Nothing is wrong exactly. The walls have picked up ten years of scuffs, the white has "
         "gone cream, and you notice it every time you walk in the door. That is the most common "
         "call we get."),
        ("One room has to be right, and soon",
         "A nursery before a baby arrives, a dining room before the holidays, a spare bedroom "
         "turning into an office. Small jobs are still jobs and we quote them."),
        ("You are moving in or moving out",
         "An empty house paints faster and costs less than a full one. If there is a window "
         "before the furniture arrives or after it leaves, that is the cheapest week to do it."),
        ("You still have to live here while it happens",
         "You do, and most people do. We work room by room, keep the dust inside plastic, and "
         "pack up at the end of each day so you get your house back every evening.")],
      prep_intro=("Two painters can quote the same three rooms and come back a long way apart, "
                  "and it is almost never about the paint. It is about what happens before the "
                  "paint."),
      prep=[
        ("Filling, then sanding",
         "Every nail hole, dent, hairline crack and old picture anchor gets filled, and then it "
         "gets sanded flat. Filled and not sanded is a bump you will see the first sunny "
         "morning after we leave."),
        ("Caulking the gaps",
         "The line where the trim meets the wall gets caulked before it gets painted. It is slow "
         "and nobody watches it being done, which is exactly why it is the first thing dropped."),
        ("Scuffing the old trim",
         "Old trim paint is glossy and new paint will not grip it. It has to be sanded first. "
         "Skip that and the finish comes off in flakes the first time a chair hits the "
         "baseboard."),
        ("Priming what needs it",
         "Bare filler, water stains and any big color change get primed. Without it you are "
         "buying a third coat that nobody quoted you for."),
        ("Covering everything",
         "Floors, furniture, hardware and switch plates. Taken off or covered up, not painted "
         "around.")],
      cheap=("A quote that comes in well under the others is rarely cheaper labor. It is fewer "
             "hours: one coat instead of two, filler that never got sanded, no caulk, no primer, "
             "and tape instead of taking the switch plates off. On day one it looks the same as "
             "everybody else's work. The difference shows up around month eight, on the wall the "
             "afternoon sun hits."),
      inc=["Walls, ceilings, trim, doors and window casings, priced separately so you can see what "
           "you are paying for",
           "Patching, filling and sanding before anything is coated",
           "Masking, floor protection and putting the room back",
           "Color matching to what is already there, or a full change with the right primer under it",
           "Closets, stairwells and hallways, which are the parts that get skipped"],
      steps=[("We come and walk it with you", "We stand in the room, count the doors and the trim "
              "runs, and look at the condition of what is already on the wall. That is the only "
              "honest way to price it, and it does not take long."),
             ("We set up", "Furniture to the middle of the room and covered, floors down, "
              "hardware and switch plates off, doors kept shut. It is what stops your house "
              "turning into a building site while the work is going on."),
             ("Prep", "Filling, sanding, caulking and scuffing the old paint. On an older house "
              "this is the longest part of the job and the part nobody photographs. It is "
              "written out in full further down this page."),
             ("Paint", "Primer where it is needed, then the finish coats, cut in by hand and "
              "rolled out. Then we look at it in daylight and fix whatever daylight shows."),
             ("We put the room back", "Furniture back where it was, hardware and switch plates "
              "back on, floors clear. Putting the room back is part of the job rather than "
              "something left to you.")],
      price_drivers=[
        ("Condition, not square footage", "This is the biggest variable and the least visible one. "
         "Patched drywall, old nicotine staining, chalking plaster and previously peeling enamel all "
         "add hours before a finish coat goes anywhere near the wall."),
        ("Whether the color is changing", "Two coats is the normal assumption. Going dark to light, "
         "or into any deep base color, is realistically three coats plus a tinted primer."),
        ("Ceiling height", "A two story entry or a vaulted room is a staging job, not a room job. It "
         "should never be quoted at the same rate as a bedroom."),
        ("How much trim there is", "Two houses with identical floor area can be very different jobs. "
         "A 1960s house with heavy casing, six panel doors and full baseboard runs is a lot of linear "
         "feet of cutting in, and trim is the line homeowners forget to ask about."),
        ("If the house is older than 1978", "Homes built before then can have lead paint under "
         "what is on the walls now, and there are rules about how it has to be contained and "
         "cleaned up. That is a real difference in setup and cleanup, and most houses around "
         "here are old enough for it to apply.")],
      faq=[("Do you paint ceilings and trim, or just walls?",
            "All of it, and they are priced separately so you can decide. A lot of people ask for "
            "walls only, then look at the trim next to fresh paint and change their mind. It is worth "
            "asking for both numbers up front so that is a decision and not a surprise."),
           ("Can you match a color I already have?",
            "Usually. Bring a chip off the wall, a switch plate or the old can and it can be matched "
            "at the paint counter. If the existing color has faded and a perfect match is not "
            "possible, you will be told that before the work starts, not after."),
           ("How many coats?",
            "Two is normal over a similar color. A big change, a deep color or bare patched drywall "
            "needs primer and often a third coat. That gets settled at the walk-through so it is in "
            "the price rather than added later."),
           ("Do I need to move everything out?",
            "No. Big furniture usually moves to the middle of the room and gets covered. Small, "
            "breakable and personal things are better off out of the way before anybody arrives."),
           ("My house is from the 1960s. Does that matter?",
            "Yes, and it is worth knowing why. Houses built before 1978 can have lead paint "
            "somewhere under the layers, and there are federal rules about how a paid contractor "
            "has to contain the dust and clean up afterwards. Most of the housing around here is "
            "old enough for that to apply. It changes how a room gets set up and cleaned, not how "
            "it gets painted, and it is a fair question to ask anybody who quotes you. "
            "<a href=\"https://www.epa.gov/lead/lead-renovation-repair-and-painting-program\" "
            "rel=\"nofollow noopener\">The EPA explains the rule here</a>.")],
      ba=[("ba1-before", "ba1-after", "Interior repaint, walls and ceiling"),
          ("ba3-before", "ba3-after", "Kitchen, cabinets and walls")],
      related=["exterior-painting", "cabinet-refinishing", "drywall-and-repair"]),

 dict(slug="exterior-painting", nav="Exterior", card="Exterior painting", hero="hero-exterior",
      title="Exterior House Painting, Chicagoland | Colors Your Way",
      desc=("Exterior house painting across Chicago and the south and southwest suburbs. Siding, "
            "trim, soffit, fascia, garage doors, prepped properly. Call "
            + PHONE_DISPLAY + "."),
      h1="Exterior house painting, and the peeling wall that started it.",
      lede=("It usually starts on one wall, the one that takes the afternoon sun. By the time "
            "you notice it from the street, the trim and the soffit are normally going too. We "
            "paint siding, trim, soffit, fascia, garage doors and front doors across Chicago and "
            "the south and southwest suburbs. An exterior here is mostly a preparation job. What "
            "gets washed, scraped, repaired and primed matters more than whatever goes on top."),
      formhead="Get an exterior quote",
      formsub="Spring books up early. Ask now, paint later.",
      situations=[
        ("One wall is peeling and the rest looks fine",
         "That is normal, not a mystery. South and west walls take the sun and fail years before "
         "the shaded sides. We will tell you honestly whether you are looking at one elevation "
         "this year or the whole house."),
        ("You cannot see what is going on up top",
         "Soffit, fascia and gable ends go long before the walls do, and none of it can be "
         "judged from the driveway. We get a ladder on it before anybody puts a number on it."),
        ("You are wondering if it is too late in the season",
         "The working window here runs roughly April to October, and it depends on temperature "
         "and humidity as much as the date on the calendar. Call and ask. If it is too late we "
         "will say so rather than rush it on."),
        ("You are not sure it needs painting at all",
         "Sometimes it does not. Sometimes it needs a wash, some caulk and a look at two boards. "
         "If that is the true answer, that is the answer you will get.")],
      prep_intro=("On an exterior the paint is the cheap part. Nearly the whole price of an "
                  "honest exterior quote is the hours that happen before the first finish coat "
                  "goes on."),
      prep=[
        ("Washing it down",
         "Dirt, chalk and mildew come off first. Paint over a chalky wall and the new coat lifts "
         "away with the chalk, usually inside two seasons."),
        ("Scraping back to sound",
         "Everything loose comes off and everything still bonded stays. How much comes off is "
         "the real size of the job, and nobody knows it exactly until the scraping is done."),
        ("Fixing the wood first",
         "Split trim, soft fascia and rotted sills get replaced before they get coated. Paint "
         "over rot and you have bought yourself one season."),
        ("Caulk and spot primer",
         "Open joints get caulked and every bare patch gets primed. Bare wood left unprimed is "
         "where the next failure starts, and it starts quickly."),
        ("Painting on the right day",
         "Temperature, dew point and how much daylight is left all decide whether today is a "
         "painting day. Some days are not, and pushing through them is how a finish fails "
         "early.")],
      cheap=("The cheap exterior quote is a rinse and a coat. Little or no scraping, no wood "
             "repair, no spot priming, sprayed on in one pass on whatever day the crew was free. "
             "It looks excellent for a year. Then the same wall that was peeling peels again, "
             "this time through the new paint, and the money is gone. If a quote is thousands "
             "below the others, find the line about scraping and rotten wood and read it "
             "carefully."),
      inc=["Wood, aluminum, vinyl, stucco and painted brick, which all behave differently and get "
           "prepped differently",
           "Trim, soffit, fascia and gable ends, which fail long before the walls do",
           "Scraping, washing, spot priming and caulking before any finish goes on",
           "Garage doors, front doors and the metal work people forget to include",
           "Decks and fences, stained or sealed, as a separate line"],
      steps=[("We walk all four sides", "Including the parts you can only see from a ladder. The "
              "rot at the end of a fascia board is invisible from the driveway, and it is not "
              "something you want discovered halfway through the job."),
             ("We agree a window, not a single day", "Exteriors run on the weather. You get a "
              "range of days rather than a promise of one, and if it moves you hear about it "
              "from us rather than wondering where everybody is."),
             ("We set up around your house", "Plants covered, walkways kept clear, and ladders "
              "and staging placed where they will not trap your cars in the driveway. Your doors "
              "and windows stay usable while the work runs."),
             ("The work itself", "Washing, scraping, repairs, caulk, primer, then finish coats, "
              "in that order. What each of those actually involves is set out further down this "
              "page, because that is where the entire price sits."),
             ("We walk it with you at the end", "Round the house together, and you point at "
              "anything you are not happy with while we are still set up to put it right.")],
      price_drivers=[
        ("Stories", "A one story and a three story are not the same job at the same square footage. "
         "Access, staging and ladder time scale faster than surface area does."),
        ("Siding material", "Wood, aluminum, stucco, brick and vinyl each take different preparation "
         "and different products, and they do not cost the same per square foot."),
        ("How much came off during scraping", "The honest answer to what an exterior costs is not "
         "fully known until the scraping is done. A good quote says so and tells you what happens if "
         "there is more."),
        ("Trim and fascia linear footage", "Exterior trim is billed by the foot and it is slow, "
         "detailed, high-up work. On a house with a lot of detail it can be a bigger number than the "
         "walls."),
        ("Time of year", "Painting contractors around here are busiest from spring into early summer. "
         "Getting a quote in February gets you a better slot than getting one in June.")],
      faq=[("When is the right time of year?",
            "The working window in this climate runs from roughly April to October, and it depends on "
            "temperature and humidity as much as the calendar. The practical advice is to get the "
            "quote and get on the schedule in late winter, because the good slots go first."),
           ("Do you paint aluminum and vinyl siding?",
            "Yes, and both need the right preparation and the right product. Vinyl in particular has "
            "to stay within a heat-safe color range or it warps. That is a conversation to have before "
            "you pick a color, not after."),
           ("What about rotted trim and fascia?",
            "That gets replaced before it gets painted. It is one of the reasons a multi-trade "
            "contractor is useful here. A painting-only company has to hand the carpentry to somebody "
            "else, and that is where a job stalls."),
           ("Do you do decks and fences?",
            "Yes, stained or sealed. Worth knowing that a short fence and a long fence often price "
            "closer together than you would expect, because the setup and the travel are the same "
            "either way."),
           ("Can you paint brick?",
            "It can be done and it is permanent. Painted brick cannot go back to bare brick without a "
            "lot of expense and damage. Anyone who says otherwise is selling.")],
      ba=[("ba2-before", "ba2-after", "Exterior repaint, siding and trim")],
      related=["interior-painting", "drywall-and-repair", "remodeling"]),

 dict(slug="cabinet-refinishing", nav="Cabinets", card="Cabinet refinishing", hero="hero-cabinets",
      title="Kitchen Cabinet Painting, Chicagoland | Colors Your Way",
      desc=("Kitchen cabinet painting and refinishing across Chicago and the south suburbs. Doors "
            "off, degreased, primed, sprayed and rehung. Call " + PHONE_DISPLAY + "."),
      h1="Kitchen cabinet refinishing, before you pay for a whole new kitchen.",
      lede=("The question almost everybody asks first is whether the kitchen has to be replaced. "
            "Usually it does not. If the boxes are solid and the layout still works for you, the "
            "doors are what you are unhappy with, and doors can be taken off, degreased, primed "
            "and sprayed. You keep the layout, the boxes and the countertops, and you change the "
            "part you actually look at. Kitchens across Chicago and the south and southwest "
            "suburbs."),
      formhead="Get a cabinet quote",
      formsub="A photo of the kitchen tells us most of it.",
      situations=[
        ("You do not hate the kitchen, you hate the color",
         "Honey oak, 1990s cherry, a white that has gone yellow above the stove. If the layout "
         "still works, that is a paint problem, not a kitchen problem, and it is a fraction of "
         "the money."),
        ("You have a quote for new cabinets and it made your eyes water",
         "Put the refinishing number next to it before you decide. Sometimes new really is the "
         "right call. You should be choosing between two numbers rather than guessing at one."),
        ("The doors are peeling or lifting at the edges",
         "Thermofoil that has started to delaminate will not take paint, and we will tell you "
         "that instead of spraying it anyway. That is a door replacement, and the boxes can "
         "usually still stay."),
        ("You want to change the handles too",
         "New handles normally mean new holes and old holes filled. That has to happen before "
         "the finish goes on, so it is worth saying at the walk-through rather than after.")],
      prep_intro=("A cabinet finish is the easiest job in this trade to make look perfect for six "
                  "weeks and the hardest one to make last for years. The whole difference is "
                  "preparation, and one step in particular."),
      prep=[
        ("Degreasing",
         "A kitchen carries years of cooking film that you cannot see and can definitely feel. "
         "If it is not washed off, nothing sticks to it, whatever gets sprayed on top. This is "
         "the single most common reason a cabinet job peels inside a year."),
        ("Doors off and numbered",
         "Every door and drawer front comes off and gets labeled, with its hinges bagged to it. "
         "Painting doors while they are still hanging is faster and it always shows."),
        ("Sanding and filling",
         "The factory finish gets scuffed so the primer has something to hold on to, and dents "
         "and old hardware holes get filled while the doors are flat."),
        ("A bonding primer, not wall primer",
         "Cabinets need a primer built to grip a finished factory surface. Wall primer is not "
         "that, and wall primer is what is in the bucket on a cheap cabinet job."),
        ("Sprayed, then left to harden",
         "Sprayed, so there is no brush texture on a surface your hand is on every day. Then "
         "left alone long enough to cure before anything gets hung back up and handled.")],
      cheap=("The fast cabinet job is a quick scuff and two coats of wall paint over the grease, "
             "brushed on with the doors still hanging. It photographs beautifully. Then the doors "
             "either side of the stove go tacky, the edges by the handles wear through to the old "
             "color, and a year later you have a kitchen that looks worse than the one you "
             "started with and is harder to put right. Ask any cabinet quote two questions: how "
             "do you degrease, and which primer are you using."),
      inc=["Doors and drawer fronts removed, numbered and worked off site or in a controlled space",
           "Degreasing, which is the step that decides whether the finish sticks",
           "Sanding, filling and a bonding primer made for cabinets",
           "Sprayed finish coats, not brush marks",
           "Hardware refitted, or new hardware fitted if you are changing it",
           "Boxes and face frames done in place"],
      steps=[("We look at the boxes first", "If the carcasses are sound, refinishing makes sense. "
              "If they are falling apart or the layout is wrong, you are better off being told "
              "that than being sold a finish on top of a bad box."),
             ("You pick the color and the sheen", "Sheen matters more on a cabinet than it does "
              "on a wall, because your hands are on it. Worth looking at the real thing rather "
              "than deciding off a paper chip."),
             ("The doors come off, and your kitchen keeps working", "You lose the doors, not the "
              "kitchen. The boxes, the sink and the appliances all stay usable. Move anything you "
              "use daily out of the cupboards before day one and life is much easier."),
             ("The work happens", "Degreasing, sanding, filling, bonding primer and sprayed "
              "finish coats. That sequence is written out further down this page, because it is "
              "the whole difference between a cabinet job that lasts and one that does not."),
             ("Everything goes back where it came from", "Numbered, so each door returns to its "
              "own opening, hinges adjusted and handles refitted. Then go easy on it for a while "
              "while the finish finishes hardening.")],
      price_drivers=[
        ("How many doors and drawers", "Cabinets are counted, not measured by kitchen. Two kitchens of "
         "the same size can have very different door counts."),
        ("What they are made of", "Solid wood, veneer, thermofoil and laminate all take different "
         "preparation and not all of them take paint well. This gets checked before it is quoted."),
        ("How greasy they are", "Degreasing is real labor and it varies enormously between kitchens."),
        ("Inside the boxes or not", "Doing the interiors is a meaningful addition. Most people do not "
         "need it. It should be your decision, made with the number in front of you."),
        ("Whether you are changing hardware", "New handles often mean new holes, filled old holes, and "
         "that has to happen before the finish goes on.")],
      faq=[("Is painting cabinets actually worth it, or should I replace them?",
            "It depends entirely on the boxes. If the carcasses are solid, the doors are not "
            "delaminating and you are happy with the layout, refinishing changes the look of the room "
            "for a fraction of a replacement. If the boxes are shot or the layout is wrong, paint will "
            "not fix that and you should be told so."),
           ("How long does it take?",
            "It is a multi-day job, not an afternoon. Doors come off, get prepped, get finished and "
            "then have to cure before they are handled. You get a realistic day count at the "
            "walk-through, including how long the kitchen is partly out of action."),
           ("Will it chip?",
            "A cabinet finish lives or dies on preparation. Degreased, sanded, primed with a bonding "
            "primer and sprayed, it holds up to daily use. Painted over grease with wall paint, it "
            "will not last a year. That difference is most of the price difference between quotes."),
           ("Can you spray, or is it brushed?",
            "Sprayed. On a surface you touch every day, brush texture is the first thing you notice "
            "and the last thing you stop noticing."),
           ("Can you do bathroom vanities too?",
            "Yes, same process, smaller job. It is often worth adding to a kitchen job while the "
            "equipment is already set up.")],
      ba=[("ba3-before", "ba3-after", "Kitchen cabinets refinished")],
      related=["interior-painting", "remodeling", "drywall-and-repair"]),

 dict(slug="drywall-and-repair", nav="Drywall &amp; repair", card="Drywall and repair",
      hero="hero-drywall",
      title="Drywall Repair, Chicago and South Suburbs | Colors Your Way",
      desc=("Drywall and plaster repair with the painting that goes over it. Cracks, holes, water "
            "damage and texture matching, Chicago and the south suburbs. "
            + PHONE_DISPLAY + "."),
      h1="The crack that keeps coming back, and the repair that stops it.",
      lede=("You have filled it twice and it has opened twice. Or there is a hole behind a door, "
            "or a brown ring on the ceiling from a leak that got fixed last year. We do drywall "
            "and plaster repair across Chicago and the south and southwest suburbs, we match the "
            "texture, and we prime and paint it so the wall reads as one surface again. That "
            "last part is not standard. Plenty of drywall crews leave you a bare patch and "
            "another phone call to make."),
      formhead="Get a repair quote",
      formsub="A photo of the damage tells us most of it.",
      situations=[
        ("The crack keeps coming back",
         "Filling it a third time will not hold. A crack that reopens in the same place is "
         "movement, and it needs taping across the joint rather than another skim of filler. "
         "Different fix, and it is the one that lasts."),
        ("Something went through the wall",
         "A doorknob, a moving day, a foot. A hole is the straightforward one. It gets cut back "
         "to solid board, patched, taped, textured and painted."),
        ("There is a stain on the ceiling from an old leak",
         "Paint on its own will not cover it. Water stains bleed back through, sometimes months "
         "later. It needs a stain blocking primer, and if the board has gone soft it needs "
         "replacing rather than coating."),
        ("Your house has plaster, not drywall",
         "A lot of the older houses around here do. Plaster over lath repairs differently and "
         "takes longer, and anybody quoting it as drywall has not really looked at it.")],
      prep_intro=("The visible part of a repair takes about an hour. Whether it disappears or "
                  "stares at you from across the room forever is decided by everything around "
                  "that hour."),
      prep=[
        ("Working out why it happened",
         "Settlement, a leak and a failed tape joint all look similar on the wall and all need "
         "different answers. Patch the wrong one and you are doing it again next year."),
        ("Cutting back to solid",
         "Soft, wet or crumbling material comes out. Patching over it just moves the problem a "
         "few months down the calendar."),
        ("Building the compound up in coats",
         "Thin coats, each one dry and sanded before the next goes on. Filled in one go is how "
         "you get a bulge with a shadow around it."),
        ("Matching the texture",
         "Knockdown, orange peel and hand troweled finishes all have to be matched. This is the "
         "step that decides whether you can pick out the repair from the doorway."),
        ("Priming, then blending",
         "New compound drinks paint differently from the wall around it. With no primer and no "
         "blend, the patch shows up as a dull shape under the finish coat.")],
      cheap=("The cheap repair is filler, one pass, no tape, no texture and paint straight over "
             "it. It vanishes while the compound is still damp and comes back as a matte outline "
             "as soon as it dries, by which point whoever did it has gone. If a quote does not "
             "mention matching the texture or priming the patch, it is a quote for half a job."),
      inc=["Cracks, holes, nail pops and failed tape joints",
           "Water damaged drywall and ceilings, once the leak itself is fixed",
           "Plaster repair, which is a different job from drywall and common in the older housing here",
           "Texture matching so the patch does not read as a patch",
           "Priming and painting the repair, and blending it into the rest of the wall"],
      steps=[("Send us a photo first", "A picture of the crack, the hole or the stain usually "
              "tells us whether this is an hour, a morning or a whole day, and whether it needs "
              "anything more than a repair. It saves everybody a trip."),
             ("We contain the room", "Sanding compound makes a fine dust that finds its way into "
              "every room in the house. Plastic goes up, floors get covered and the vents in the "
              "work area get taped off before any sanding starts."),
             ("The repair, built up in coats", "Cut back, patched, taped and built up. Compound "
              "has to dry between coats, so most repairs are two shorter visits rather than one "
              "long day. What that involves is set out further down this page."),
             ("Texture, then paint", "The texture gets matched, then the repair is primed, "
              "painted and blended out so the wall reads as one surface again."),
             ("We clean up properly", "Drywall dust is the entire reputation of this job. "
              "Vacuumed and wiped down, not swept into the air and left.")],
      price_drivers=[
        ("How many separate repairs", "Ten small patches in one room is a very different job from one "
         "large one, and usually a bigger one."),
        ("Drywall or plaster", "Older houses around here are often plaster over lath. It repairs "
         "differently, it takes longer, and it should be priced differently."),
        ("Texture", "A flat wall is straightforward. Knockdown, orange peel and hand-troweled finishes "
         "have to be matched, and matching is a skill charge, not a materials charge."),
        ("Ceilings", "Overhead work is slower than wall work at every stage."),
        ("Whether the cause is fixed", "Nobody should be patching water damage while the leak is still "
         "running. If the source is not fixed, that comes first.")],
      faq=[("Does drywall repair include painting?",
            "Here it does, and that is worth checking with anyone you call, because the answer is often "
            "no. Plenty of drywall specialists leave a bare, primed patch and consider the job "
            "finished, which leaves you finding a painter. Repair and finish are quoted together here."),
           ("Do painting companies do drywall?",
            "Some do and many do not. It is one of the most common surprises in this trade: a painter "
            "arrives, finds real damage behind the furniture, and now you need a second contractor and "
            "a second appointment. Asking the question before you book saves a week."),
           ("Can you match my ceiling texture?",
            "Usually. Knockdown and orange peel can be matched closely. Hand-troweled plaster and some "
            "older sprayed finishes are harder, and if a perfect match is not realistic you will hear "
            "that before the work starts."),
           ("My ceiling has a stain from an old leak. Will paint cover it?",
            "Not on its own. A water stain bleeds through ordinary paint, sometimes months later. It "
            "needs a stain-blocking primer, and if the board is soft it needs replacing rather than "
            "coating."),
           ("Is a hairline crack worth fixing?",
            "If it keeps reopening in the same place, filling it again will not hold. That is usually "
            "movement, and it needs taping across the joint rather than another skim of filler.")],
      ba=[("ba1-before", "ba1-after", "Wall repair and repaint")],
      related=["interior-painting", "remodeling", "cabinet-refinishing"]),

 dict(slug="remodeling", nav="Remodeling", card="Remodeling and trades", hero="hero-remodeling",
      title="Remodeling and Trades, Chicagoland | Colors Your Way USA",
      desc=("Carpentry, tile, flooring, subfloor repair, concrete, faux finishes and "
            "remodeling across Chicago's south side and the south suburbs. Call "
            + PHONE_DISPLAY + "."),
      h1="When the job turns out to be more than paint.",
      lede=("Plenty of jobs turn out to be something else once somebody looks underneath. The "
            "bathroom needs painting, and the floor by the tub has a soft spot. The trim needs "
            "repainting, and the sill behind it has gone. Most painters stop there and hand you "
            "a list of people to call. We do the carpentry, the tile, the flooring, the "
            "subfloors and the concrete as well, across Chicago and the south and southwest "
            "suburbs, so the job keeps moving instead of sitting half finished while you chase "
            "somebody else."),
      formhead="Ask about a bigger job",
      formsub="Tell us what you are actually looking at.",
      situations=[
        ("A painter has already told you it is not a painting job",
         "That usually means rot, a soft floor, or a wall that has to be rebuilt before anything "
         "can be coated. All of that is work we do, and it is the reason this page exists."),
        ("You have been trying to get three trades to line up",
         "Subfloor, then tile, then trim, then paint. Three companies and three calendars is why "
         "that project has taken four months. One company is one calendar."),
        ("It started as one room and grew",
         "Bathrooms and kitchens do this constantly. The honest move is to look at all of it at "
         "once and tell you the real size of the job at the quote, not on day two."),
        ("You want to know whether it is even worth doing",
         "Sometimes the answer is that the job belongs with a specialist, or that it is not "
         "worth the money this year. If that is the true answer, you will hear it.")],
      prep_intro=("On a remodel the surprises are never in the finish work. They are underneath "
                  "it. So the part worth paying for is the looking, and that has to happen "
                  "before the quote rather than after the demolition."),
      prep=[
        ("Protecting the rest of the house",
         "Dust from tile and drywall work travels through a whole house through the return "
         "vents. Doorways get sealed, the route in and out gets covered, and the vents in the "
         "work area get taped off before anything gets broken up."),
        ("Taking it apart carefully",
         "Demolition looks like the fun part and it is where most of the accidental damage "
         "happens. Tile comes off without wrecking the wall behind it, and trim that is going "
         "back on comes off in one piece."),
        ("Making the substrate right before the finish goes on",
         "Tile laid over a soft or uneven subfloor cracks its grout inside a year, however good "
         "the tile is. The floor gets made flat and solid first, and that is the part that never "
         "shows up in a photograph of a finished bathroom."),
        ("Dealing with the water first",
         "In a bathroom or a basement, whatever is letting water in gets sorted out before "
         "anything is closed up over it. Otherwise you are paying to bury the problem somewhere "
         "you can no longer reach it."),
        ("Prepping the new work for paint",
         "New trim and new drywall need filling, caulking and priming before they take a finish "
         "coat, exactly like any other paint job. Skipping that is why new work sometimes looks "
         "worse than the old work next to it.")],
      cheap=("On bigger jobs the low quote is usually the one that did not look underneath. It "
             "is a real price for a smaller job than the one you have, and the difference comes "
             "back as a change order once the floor is up and you have nowhere else to go. A "
             "quote that tells you in advance what happens if there is rot is worth more than a "
             "cheaper one that says nothing about it."),
      inc=["Carpentry: trim, casing, doors, sills, fascia and the rot behind the paint",
           "Tile: floors, walls, bathrooms, backsplashes",
           "Flooring and subfloors, including the soft spot under the tile that caused the problem",
           "Concrete work",
           "Faux finishes",
           "General remodeling, where several of the above are one project"],
      steps=[("Look at the whole thing", "A bathroom that needs painting sometimes needs the floor "
              "pulled up first. Finding that out at the quote is better than finding it out on day "
              "two."),
             ("Say what it actually is", "If a job is bigger than you were hoping, you get told at the "
              "quote. If it is smaller, you get told that too."),
             ("One company, one schedule", "The reason this list exists is sequencing. Subfloor, then "
              "tile, then trim, then paint, in that order, run off one calendar instead of three "
              "companies coordinating diaries."),
             ("Finish it", "Including the painting, which is the part that usually gets left when a "
              "remodeler hands over.")],
      price_drivers=[
        ("What is underneath", "Almost every remodeling surprise is under something. Soft subfloor, "
         "rot behind trim, and old work done badly are the three usual ones."),
        ("How many trades the job needs", "Sequencing several trades on one schedule is the value "
         "here, and it is also what makes the number bigger than a paint quote."),
        ("Materials you choose", "Tile, flooring and hardware ranges are wide. That part is genuinely "
         "your decision and it moves the total a long way."),
        ("Whether anything structural is involved", "Some things are not a remodeling job and need the "
         "right professional. You will be told which is which.")],
      faq=[("Are you a painter or a remodeler?",
            "Mostly a painter, which is why painting is what this site leads with. The rest of the "
            "trade list is real work that gets done here, and it exists so a job does not stop when "
            "it turns out to need more than paint."),
           ("Why does that matter to me?",
            "Because the common version of this goes: a painter finds a rotten sill, stops, and you "
            "spend two weeks finding a carpenter who will take a small job. One contractor who can do "
            "both is not a bigger company, it is a shorter calendar."),
           ("Do you do full kitchen and bathroom remodels?",
            "Ask. Some are a good fit and some are better off with a company that does nothing else. "
            "You will get a straight answer about which one yours is rather than a yes to everything."),
           ("Do you do tile and subfloors?",
            "Yes. Worth saying plainly because almost nobody else in this market offers tile or "
            "subfloor work alongside painting, and a soft floor under a tiled bathroom is one of the "
            "most common jobs that gets bounced between contractors."),
           ("Who actually does the work?",
            "We do, and the owner runs it. " + OWNER + " quotes the job himself and stays on it "
            "while our crew works, rather than handing it to a branch office and a salesperson. "
            "That is not something a franchise can copy, and it is the main reason people call "
            "back.")],
      ba=[("ba4-before", "ba4-after", "Bathroom, tile and finish"),
          ("ba1-before", "ba1-after", "Room brought back and repainted")],
      related=["interior-painting", "drywall-and-repair", "cabinet-refinishing"]),
]

SERVICE_BY_SLUG = dict((s["slug"], s) for s in SERVICES)

# =============================================================================
# PILLAR AND CLUSTER
# =============================================================================
# The service pages are the pillars. The blog posts are the cluster. For that to
# be a real structure rather than a diagram in a deck, the links have to run
# BOTH ways:
#
#   post  -> service page   handled by the `service_page` key in each post's
#                           front matter, rendered as the "See our X page"
#                           button at the end of the post.
#   service page -> posts   handled by the map below. Before this existed, not
#                           one service page linked to a single blog post, so
#                           the posts were reachable only from the Notes index
#                           and passed no relevance to the pages that earn the
#                           phone calls.
#
# Rules enforced in build_service():
#   - every service page names at least two posts
#   - every named slug must be a post that actually exists, or the build fails
#
# 08-SEO-AND-KEYWORD-RESEARCH.md section 6 is explicit that the internal link
# graph is what stops a small site behaving like a pile of orphans.
MIN_POSTS_PER_SERVICE = 2

SERVICE_POSTS = {
    "interior-painting": [
        "interior-painting-cost-southwest-chicago-suburbs",
        "how-to-tell-good-prep-from-a-fast-cheap-job",
        "choosing-paint-colors-older-southwest-suburb-homes",
    ],
    "exterior-painting": [
        "best-time-to-paint-house-exterior-chicago",
        "how-to-tell-good-prep-from-a-fast-cheap-job",
        "choosing-paint-colors-older-southwest-suburb-homes",
    ],
    "cabinet-refinishing": [
        "cabinet-refinishing-vs-replacing",
        "interior-painting-cost-southwest-chicago-suburbs",
        "choosing-paint-colors-older-southwest-suburb-homes",
    ],
    "drywall-and-repair": [
        "how-to-tell-good-prep-from-a-fast-cheap-job",
        "interior-painting-cost-southwest-chicago-suburbs",
        "rental-turnover-painting-southwest-suburbs",
    ],
    "remodeling": [
        "cabinet-refinishing-vs-replacing",
        "rental-turnover-painting-southwest-suburbs",
        "interior-painting-cost-southwest-chicago-suburbs",
    ],
}


def post_links(slug, posts, up=""):
    """The "Worth reading before you call" block on a service page.

    Returns "" when there are no posts at all (a bare checkout of the repo with
    an empty blog/ folder still has to build). Anything else is a hard failure,
    because a service page that silently stops linking into the cluster is
    exactly the kind of regression nobody notices for a year.
    """
    if not posts:
        return ""
    by_slug = dict((p["slug"], p) for p in posts)
    want = SERVICE_POSTS.get(slug)
    if want is None:
        sys.exit("BUILD FAILED: " + slug + " has no entry in SERVICE_POSTS. Every service "
                 "page must link to at least " + str(MIN_POSTS_PER_SERVICE) + " blog posts.")
    missing = [w for w in want if w not in by_slug]
    if missing:
        sys.exit("BUILD FAILED: SERVICE_POSTS['" + slug + "'] names " + ", ".join(missing) +
                 " but there is no such post in blog/. Fix the slug or add the post.")
    if len(want) < MIN_POSTS_PER_SERVICE:
        sys.exit("BUILD FAILED: SERVICE_POSTS['" + slug + "'] lists " + str(len(want)) +
                 " post(s). The minimum is " + str(MIN_POSTS_PER_SERVICE) + ".")
    out = '<ul class="reads">'
    money = False
    for w in want:
        p = by_slug[w]
        d = str(p.get("description", ""))
        money = money or "$" in d
        out += ('<li><h3><a href="' + up + 'blog/' + w + '.html">' + esc(str(p["title"])) +
                '</a></h3><p>' + esc(d) + "</p></li>")
    out += "</ul>"
    # Some post summaries quote a market range. The same rule applies here as on
    # the posts themselves: a figure on this site is never presented as Mike's
    # price. build.py states it rather than trusting a future summary to.
    if money:
        out += ('<p class="ph-note">Any dollar figure in these summaries is a published market '
                'range, quoted from a source named in the post. None of it is a ' + BRAND +
                ' price. Every job is quoted after a walk-through.</p>')
    return out


# =============================================================================
# PAGE BUILDERS
# =============================================================================

def hero(page_h1, lede, eyebrow, herokey, formhead, formsub, page="", up=""):
    return ('<section class="hero">\n  <div class="wrap hero-in">\n'
            '    <div class="hero-copy">\n'
            '      <p class="eyebrow">' + eyebrow + '</p>\n'
            '      <h1>' + page_h1 + '</h1>\n'
            '      <p class="lede">' + lede + '</p>\n'
            '    </div>\n'
            '    <div class="hero-form" id="quote">' + quote_form(formhead, formsub, page, up) + '</div>\n'
            '    <div class="hero-shot"><div class="hero-photo">' + img(herokey, lazy=False, up=up) +
            '</div></div>\n'
            '  </div>\n</section>\n')


def build_service(s, posts=()):
    fn = s["slug"] + ".html"
    inc = "".join("<li>" + x + "</li>" for x in s["inc"])
    steps = "".join("<li><strong>" + a + "</strong>" + b + "</li>" for a, b in s["steps"])
    drivers = "".join("<li><strong>" + a + "</strong>" + b + "</li>" for a, b in s["price_drivers"])
    # The two homeowner-facing blocks. `situations` is the page's opening move:
    # somebody arriving from a search does not want a definition of the trade,
    # they want to see their own house described back to them. `prep` is the
    # sale: preparation is the real difference between two quotes and almost no
    # homeowner has been told how to judge it, so explaining it plainly is worth
    # more than any claim this site is not allowed to make.
    sits = "".join("<li><strong>" + a + ".</strong> " + b + "</li>" for a, b in s["situations"])
    prep = "".join("<li><strong>" + a + "</strong>" + b + "</li>" for a, b in s["prep"])
    faqrows, faqld = faq(s["faq"])
    rel = "".join('<a class="pill" href="' + r + '.html">' + SERVICE_BY_SLUG[r]["card"] + '</a>'
                  for r in s["related"])
    # Town pills are capped at the close ring. A service page that dumps 76 town
    # links into one pill row is link soup, not internal linking: it dilutes
    # every link on the page and it is the most recognizable programmatic-SEO
    # signature there is. The ten nearest places get a real deep link to their
    # own page, and the rest is one link to the hub that holds all of them.
    towns = "".join('<a class="pill" href="areas/' + q["slug"] + '.html">' + city_anchor(q) + '</a>'
                    for q in built_places()[:10])
    towns += ('<a class="pill" href="areas/index.html"><strong>See all ' +
              str(len(built_places())) + ' towns we cover &rarr;</strong></a>')
    reads = post_links(s["slug"], posts)
    crumb_html, crumb_ld = breadcrumbs([("Home", "index.html"), (s["card"], fn)])

    html = head(s["title"], s["desc"], fn, s["hero"]) + header(fn)
    html += '<main id="main">\n' + crumb_html
    html += hero(s["h1"], s["lede"], s["nav"] + " &middot; " + REGION_SHORT, s["hero"],
                 s["formhead"], s["formsub"], page=s["nav"] + " (" + fn + ")")
    html += ('<div class="strip"><div class="wrap"><ul>'
             '<li>' + REGION_LONG + '</li>'
             '<li>Owned and run by ' + OWNER + ', based in ' + CITY + '</li>'
             '<li>Painting, carpentry, tile and flooring</li>'
             '<li>We come and look before we quote</li></ul></div></div>\n')

    html += ('<section>\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Sound familiar</p>\n'
             '    <h2>Most people call us for one of these reasons</h2>\n'
             '    <p class="lede">If one of these is roughly your situation, you are in the '
             'right place.</p>\n'
             '    <ul class="ticks">' + sits + '</ul>\n  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap two-col">\n    <div>\n'
             '      <p class="eyebrow">What is covered</p>\n'
             '      <h2>' + s["card"] + ', in full</h2>\n'
             '      <ul class="ticks">' + inc + '</ul>\n'
             '    </div>\n    ' + img(s["ba"][0][1]) + '\n  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">How the job runs</p>\n'
             '    <h2>What happens, in the order it happens</h2>\n'
             '    <ol class="nums">' + steps + '</ol>\n  </div>\n</section>\n')

    # The prep section. This is the one thing on the page that changes how
    # somebody reads every other quote they get, which is why it is written out
    # at length instead of compressed into a bullet. It also does the job a
    # testimonial would normally do on a contractor site, and this site is not
    # allowed to have testimonials because there are none.
    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">The part you cannot see</p>\n'
             '    <h2>What good preparation is, and why the cheap quote is cheap</h2>\n'
             '    <p class="lede">' + s["prep_intro"] + '</p>\n'
             '    <ol class="nums">' + prep + '</ol>\n'
             '    <div class="callout"><h3>Where a cheap quote saves its money</h3><p>'
             + s["cheap"] + '</p></div>\n'
             '  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap">\n'
             '    <p class="eyebrow">Recent work</p>\n'
             '    <h2>Before and after</h2>\n'
             '    <p class="lede">A before and after pair of the same room is the only fair way '
             'to judge a painter.</p>\n'
             '    ' + ba_gallery(s["ba"]) + '\n  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">What moves the number</p>\n'
             '    <h2>Why two quotes for the same job can look nothing alike</h2>\n'
             '    <p class="lede">There are no prices on this site, because a real number needs '
             'somebody standing in front of the work. What we can tell you is what actually '
             'drives it, so you can read any quote you get and understand what you are looking '
             'at.</p>\n'
             '    <ol class="nums">' + drivers + '</ol>\n'
             '    <div class="callout"><h3>Ask everybody who quotes you these three questions</h3>'
             '<p>What preparation is included. How many coats. What happens to the price if the '
             'preparation turns out worse than it looks. The answers tell you far more than the '
             'total at the bottom does.</p></div>\n'
             '  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Questions</p>\n'
             '    <h2>What people ask about ' + s["card"].lower() + '</h2>\n'
             '    ' + faqrows +
             '    <p class="eyebrow" style="margin-top:2rem">We also do</p>\n'
             '    <div class="pills">' + rel + '</div>\n'
             '    <p class="eyebrow" style="margin-top:1.6rem">Towns closest to the shop</p>\n'
             '    <div class="pills">' + towns + '</div>\n'
             '  </div>\n</section>\n')

    if reads:
        html += ('<section class="alt">\n  <div class="wrap narrow">\n'
                 '    <p class="eyebrow">Worth a read first</p>\n'
                 '    <h2>The longer answers</h2>\n'
                 '    <p class="lede">The same questions people ask us on the phone, written out '
                 'properly, with every figure sourced.</p>\n'
                 '    ' + reads + '\n'
                 '    <p style="margin-top:18px"><a href="blog/index.html">All notes &rarr;</a></p>\n'
                 '  </div>\n</section>\n')

    html += cta()
    html += "</main>\n" + footer()
    html += ld_json([webpage_ld(fn, s["title"], s["desc"]),
                     service_ld(s["card"], s["desc"], fn), faqld, crumb_ld])
    html += confirm_comment() + "</body>\n</html>\n"
    write(fn, html)
    return fn


def build_home(posts=()):
    cards = ""
    for s in SERVICES:
        cards += ('<a class="card" href="' + s["slug"] + '.html">' + img(s["hero"]) +
                  '<div class="body"><h3>' + s["card"] + '</h3><p>' +
                  s["lede"].split(".")[0] + '.</p>'
                  '<span class="more">See what is involved &rarr;</span></div></a>')
    cards += ('<a class="card" href="areas/index.html">' + img("hero-service-area") +
              '<div class="body"><h3>Where we work</h3><p>Chicago and the south and southwest '
              'suburbs. Find your town and see what the houses around there are usually '
              'like.</p>'
              '<span class="more">Find your town &rarr;</span></div></a>')

    faqrows, faqld = faq([
      ("Do you cover my town?",
       "Chicago and the south and southwest suburbs. The shop is in Bridgeview, so the close ring "
       "is Oak Lawn, Burbank, Evergreen Park, Palos Hills, Palos Heights, Hickory Hills, Chicago "
       "Ridge, Worth, Justice and Summit, and we go out as far as Orland Park, Tinley Park, "
       "Mokena, Frankfort and Lemont. On the city side it is the south and southwest sides. There "
       "is a page for every town we cover, and if yours is not on it, call and ask rather than "
       "assume."),
      ("How much is this going to cost?",
       "That depends on things nobody can see in a photograph, which is why there are no prices "
       "on this site. On an interior it comes down to the condition of what is already on the "
       "wall and how much trim there is. Send us photos and we will tell you what to expect, then "
       "we come and look and you get a real number."),
      ("Do you do small jobs?",
       "Yes. One room, one wall, one ceiling, a patch, a door. Close to the shop a small repair "
       "is worth a trip on its own. Further out it is worth asking, and you will get a straight "
       "answer about whether the drive makes sense rather than a quiet no."),
      ("Do you do more than painting?",
       "Yes, and that is unusual around here. Alongside interior and exterior painting we do "
       "carpentry, tile, flooring, subfloor repair, concrete, faux finishes and general "
       "remodeling. The point is not a longer list. It is that your job does not stop dead when "
       "it turns out to need more than paint."),
      ("Who will actually be in my house?",
       "Our own crew, run by the owner. " + OWNER + " owns the company, walks and prices the job "
       "himself, and stays on it while it runs. There is no branch office and no salesperson on "
       "commission standing between you and the people doing the painting."),
      ("Are you insured?",
       "Ask on the phone and you will get a straight answer. Insurance and any local registration "
       "details go on this website the moment the paperwork is handed over, and not a day before. "
       "Nothing is claimed here that has not been produced."),
      ("Can I read your reviews?",
       "Not yet. This business has run on word of mouth and a van, and no reviews have been "
       "collected. Rather than fill the page with something invented, the space is left empty "
       "until there are real ones to put in it."),
    ])

    # The home page owns the REGIONAL head terms. It used to be scoped to
    # Bridgeview, a village of 16,721 people, while 76 city pages underneath it
    # covered all of Chicagoland. The address is still Bridgeview and it is
    # still on this page, in the strip, the footer and the LocalBusiness schema.
    # It is the base, not the market.
    html = head("House Painters, Chicago and South Suburbs | Colors Your Way",
                "Painting and remodeling across Chicago and the south and southwest suburbs. "
                "Interior, exterior, cabinets, drywall, carpentry and tile. Call "
                + PHONE_DISPLAY + ".",
                "index.html", "og-home")
    html += header("index.html")
    html += '<main id="main">\n'
    html += hero("House painters for Chicago and the south suburbs. Call and we come look.",
                 "Inside or outside, one room or the whole house, plus the cabinets, drywall, "
                 "carpentry, tile and flooring most painters hand off to somebody else. Call "
                 + PHONE_DISPLAY + " and we will arrange a time to come and see the job. Nobody "
                 "gets a number until somebody has stood in front of the work. We are owner run "
                 "out of our own shop in Bridgeview, and " + OWNER + " walks and prices every "
                 "job himself.",
                 "Painting &amp; remodeling &middot; " + REGION_LONG, "og-home",
                 "Ask for a quote", "Tell us your town and what needs doing.",
                 page="Home (index.html)")
    html += ('<div class="strip"><div class="wrap"><ul>'
             '<li>' + REGION_LONG + '</li>'
             '<li>Our shop is at ' + STREET + ', ' + CITY + '</li>'
             '<li>Owner run, not a franchise branch</li>'
             '<li>Painting, carpentry, tile, flooring, concrete</li>'
             '<li>We come and look before we quote</li></ul></div></div>\n')

    html += ('<section>\n  <div class="wrap">\n'
             '    <p class="eyebrow">What we do</p>\n'
             '    <h2>Start with whatever is bothering you</h2>\n'
             '    <p class="lede">Nearly every call is one of these. Each page tells you what is '
             'included, what happens on the day, and what makes one quote different from '
             'another.</p>\n'
             '    <div class="cards">' + cards + '</div>\n  </div>\n</section>\n')

    # How a quote happens. This is the single most asked question on a
    # contractor site and it was previously answered only inside an FAQ toggle
    # halfway down the page. It is a decision-making step, so it goes above the
    # photographs.
    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">How it works</p>\n'
             '    <h2>How you get a price from us</h2>\n'
             '    <p class="lede">Four steps, no sales appointment, and nothing you have to sit '
             'through.</p>\n'
             '    <ol class="nums">'
             '<li><strong>You call or send the form.</strong> One number, ' + PHONE_DISPLAY + ', '
             'and it goes to the company rather than a call center. Texting a photo of the room '
             'or the front of the house is the fastest thing you can do.</li>'
             '<li><strong>We come and look at it.</strong> Somebody stands in the room, counts '
             'the doors and the trim runs, and looks at the condition of what is already on the '
             'wall. There is no honest way to price this work off a photograph, and a number '
             'given without a visit is a guess made in the contractor&rsquo;s favor.</li>'
             '<li><strong>You get the number and what sits behind it.</strong> What is included, '
             'how many coats, what the preparation is, and what happens to the price if the '
             'preparation turns out worse than it looks. That last line is the one to compare '
             'between quotes.</li>'
             '<li><strong>We book a date and do the work.</strong> You know who is coming and '
             'roughly how many days it takes. The owner runs the job, so if something changes you '
             'hear it from the person responsible for it.</li>'
             '</ol>\n  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap two-col">\n    <div>\n'
             '      <p class="eyebrow">On the day</p>\n'
             '      <h2>What it is like having us working in your house</h2>\n'
             '      <ul class="ticks">'
             '<li><strong>You can carry on living there.</strong> We work room by room. Furniture '
             'moves to the middle and gets covered, floors get protected, and doors stay shut so '
             'the dust stays where the work is.</li>'
             '<li><strong>You get your house back every evening.</strong> Tools and materials get '
             'packed up at the end of the day rather than left across your living room for a '
             'week.</li>'
             '<li><strong>You know who is coming.</strong> Our own crew, run by the owner, not a '
             'different subcontracted van every morning.</li>'
             '<li><strong>The room goes back together.</strong> Furniture back where it was, '
             'hardware and switch plates back on, floors clear. Putting the room back is part of '
             'the job, not a favor.</li>'
             '<li><strong>If you hate it, say so on day one.</strong> Colors look different on a '
             'wall than they do on a chip. Tell us early and it is a small conversation. Tell us '
             'at the end and it is a repaint.</li>'
             '</ul>\n    </div>\n    ' + img("prep-tape") + '\n  </div>\n</section>\n')

    html += ('<section class="alt" id="work">\n  <div class="wrap">\n'
             '    <p class="eyebrow">Recent work</p>\n'
             '    <h2>Before and after</h2>\n'
             '    <p class="lede">Before and after pairs of the same room are the only fair way '
             'to judge a painter.</p>\n'
             '    ' + ba_gallery([("ba1-before", "ba1-after", "Interior repaint"),
                                  ("ba2-before", "ba2-after", "Exterior, siding and trim"),
                                  ("ba3-before", "ba3-after", "Kitchen cabinets refinished"),
                                  ("ba4-before", "ba4-after", "Bathroom, tile and finish")]) +
             '\n  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap two-col">\n    <div>\n'
             '      <p class="eyebrow">Why people call us</p>\n'
             '      <h2>What a local owner gives you that a franchise branch cannot</h2>\n'
             '      <ul class="ticks">'
             '<li><strong>The person who quotes it is the person running it.</strong> ' + OWNER +
             ' owns the company. He walks the job, prices it, and stays on it while our crew '
             'works. Nothing gets promised at your kitchen table by a salesman on commission and '
             'then forgotten by the start date.</li>'
             '<li><strong>We can finish the whole job.</strong> Painting, carpentry, tile, '
             'flooring, subfloors, concrete and faux finishes. When a bathroom repaint turns out '
             'to be a soft subfloor, it does not turn into a month of hunting for a second '
             'contractor.</li>'
             '<li><strong>We are actually from here.</strong> The shop is in Bridgeview, about '
             'where the city stops and the southwest suburbs start. We work the south side and '
             'the towns south and southwest of it. Not the whole metro, and not a territory map '
             'drawn up in another state.</li>'
             '<li><strong>If something is wrong there is one person to tell.</strong> One number, '
             'one owner, no branch manager to be escalated to. That is the whole of it.</li>'
             '</ul>\n    </div>\n    ' + img("tools-floor") + '\n  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Straight answers</p>\n'
             '    <h2>License, insurance and guarantee: the honest version</h2>\n'
             '    <p class="lede">Most contractor websites carry a row of badges with nothing '
             'behind any of them. Here is what we can and cannot show you, and what the word '
             '"licensed" actually means for a painter in Illinois.</p>\n'
             + '    ' + trust_row() + '\n'
             '    <div class="callout"><h3>Why these say "to supply"</h3>'
             '<p>Because the real values have not been handed over yet, and putting a plausible '
             'looking number in an empty box is how a website starts lying on a business owner\'s '
             'behalf. They will appear here exactly as they are, and not before.</p>'
             '<p>Worth knowing while you compare quotes: Illinois does not license painters or '
             'general contractors at state level. The state licenses roofing contractors under the '
             'Illinois Roofing Industry Licensing Act, and IDFPR does not list painter, painting '
             'contractor, general contractor or remodeler as regulated professions. So a "licensed" '
             'badge on a painting company\'s website in this state does not mean what most people '
             'assume it means. Insurance is the thing that actually protects you, and it is worth '
             'asking every contractor to show you the certificate.</p>'
             '<p class="src">Sources: '
             '<a href="https://idfpr.illinois.gov/profs/proflist.html" rel="nofollow noopener">'
             'IDFPR list of regulated professions</a>, '
             '<a href="https://www.ilga.gov/Legislation/ILCS/Articles?ActID=1346&amp;ChapterID=24" '
             'rel="nofollow noopener">225 ILCS 335</a>.</p>'
             '</div>\n  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Reviews</p>\n'
             '    <h2>We do not have reviews to show you yet</h2>\n'
             # Do NOT write "has never collected a single online review". The brief
             # records "Website: none" and lists review capture as a system still to
             # be built, which supports "none here yet". It does not support an
             # absolute claim about every review site on the internet, and an
             # unverifiable absolute is exactly what this site does not do.
             '    <p class="lede">This business has run on word of mouth, so there is nothing '
             'to show here yet. That is a real gap and it is being closed the slow, honest way, '
             'by asking customers after the work is done.</p>\n'
             '    <div class="empty"><p><strong>This space is reserved for real reviews from real '
             'customers.</strong></p><p style="margin:0">Nothing invented will ever be put here. '
             'If you have had work done and you are willing to write one, it genuinely matters '
             'more than anything else on this site.</p></div>\n'
             '  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Questions</p>\n'
             '    <h2>The things people ask us before they call</h2>\n'
             '    ' + faqrows + '  </div>\n</section>\n')

    # The home page is the top of the pillar. It has to reach the cluster
    # directly, not only through a "Notes" link buried in the footer.
    if posts:
        top = sorted(posts, key=lambda x: x.get("order") or 99)[:3]
        latest = "".join(
            '<li><h3><a href="blog/' + p["slug"] + '.html">' + esc(str(p["title"])) +
            '</a></h3><p>' + esc(str(p.get("description", ""))) + "</p></li>" for p in top)
        note = ""
        if any("$" in str(p.get("description", "")) for p in top):
            note = ('<p class="ph-note">Any dollar figure in these summaries is a published '
                    'market range, quoted from a source named in the post. None of it is a '
                    + BRAND + ' price. Every job is quoted after a walk-through.</p>')
        html += ('<section>\n  <div class="wrap narrow">\n'
                 '    <p class="eyebrow">Notes</p>\n'
                 '    <h2>A few things worth reading before you decide</h2>\n'
                 '    <p class="lede">Written out at length, with every price figure named as a '
                 'published market range and its source given.</p>\n'
                 '    <ul class="reads">' + latest + '</ul>\n' + note +
                 '    <p style="margin-top:18px"><a href="blog/index.html">All notes &rarr;</a>'
                 '</p>\n  </div>\n</section>\n')

    html += cta()
    html += "</main>\n" + footer()
    html += ld_json([website_ld(),
                     webpage_ld("index.html",
                                BRAND + ", house painters for Chicago and the south suburbs",
                                "Painting and remodeling contractor covering " + REGION_LONG +
                                ", working from its own shop in Bridgeview, Illinois."),
                     faqld])
    html += confirm_comment() + "</body>\n</html>\n"
    write("index.html", html)
    return "index.html"


def build_service_area():
    """The old service-area.html, kept alive as a signpost.

    It used to be the whole service area on one page: 27 towns as accordion
    blocks under one title tag. That page could not grow. At 76 places it would
    have been a single enormous scroll competing with itself for every town name
    on it, which is the opposite of what a location page set is for.

    The content moved to areas/index.html and one page per place. This file
    stays because the preview URL has been shared, README.md refers to it, and a
    404 on a link somebody already has is a worse outcome than one extra page.
    It carries a PERMANENT noindex (not the preview flag), it is kept out of the
    sitemap, and it links straight through. Do not turn it back into a content
    page: two pages describing the same service area is the duplicate-content
    problem this build spends a whole audit avoiding.
    """
    fn = "service-area.html"
    hub = "areas/index.html"
    title = "Service Area, Moved to the Areas Index | Colors Your Way"
    desc = ("The service area now has a page for each town and Chicago neighborhood. This "
            "page links through to the areas index and is kept only so older links still "
            "land somewhere useful.")
    crumb_html, crumb_ld = breadcrumbs([("Home", "index.html"), ("Service area", fn)])
    groups = "".join('<li><a href="' + hub + '#' + k + '">' + label + "</a></li>"
                     for k, label, _ in REGIONS)
    html = head(title, desc, fn, "hero-service-area", always_noindex=True,
                extra_meta='<meta http-equiv="refresh" content="4; url=' +
                           canonical_url(hub) + '">\n')
    html += header(hub)
    html += '<main id="main">\n' + crumb_html
    html += ('<section>\n  <div class="wrap narrow">\n'
             '    <h1>The service area moved to its own section.</h1>\n'
             '    <p class="lede">There is now a page for each of the ' +
             str(len(built_places())) + ' towns and Chicago neighborhoods covered, built off '
             'that place&rsquo;s own published housing figures, because a 1941 median in '
             'Beverly and a 2000 median in Frankfort are not the same job.</p>\n'
             '    <p><a class="btn" href="' + hub + '">Go to the areas index</a></p>\n'
             '    <h2>Or jump to a region</h2>\n'
             '    <ul class="fl">' + groups + '</ul>\n'
             '  </div>\n</section>\n')
    html += cta()
    html += "</main>\n" + footer()
    html += ld_json([webpage_ld(fn, title, desc), crumb_ld])
    html += confirm_comment() + "</body>\n</html>\n"
    write(fn, html)
    return fn


def build_contact():
    fn = "contact.html"
    hours = TRUST["hours"]
    hours_html = ('<p><strong>Hours</strong><br>' + esc(hours) + '</p>' if hours else
                  '<p><strong>Hours</strong><br><span style="color:var(--amber)">To supply</span>'
                  '<br><span style="font-size:.87rem;color:var(--ink-2)">Not listed yet, because '
                  'guessing them would put a wrong answer here and on the Google listing. Call and '
                  'ask.</span></p>')

    faqrows, faqld = faq([
      ("What is the fastest way to reach you?",
       "The phone. " + PHONE_DISPLAY + ". There is one number and it goes to " + OWNER + ". If "
       "you would rather text, then texting photos of the room or the front of the house is "
       "genuinely the most useful thing you can send us."),
      ("What should I have ready when I call?",
       "Your town, roughly what needs doing, and a rough idea of how old the house is. For an "
       "interior, how many rooms and whether you want the trim and ceilings included. For an "
       "exterior, how many stories and what the siding is made of. None of it has to be exact."),
      ("What if I am not sure what I need?",
       "Then just describe what is bothering you and we will work out what the job actually is. "
       "Plenty of calls start with somebody apologizing for not knowing the right word for "
       "something. It does not matter in the slightest."),
      ("Will I get a price over the phone?",
       "You will get a useful idea of what is involved and what tends to move the number. You "
       "will not get a final price. The two things that decide an interior job are the condition "
       "of what is already on the wall and how much trim there is, and neither of those can be "
       "judged down a phone line."),
      ("Do you charge to come out and look?",
       "Ask when you call. It is a fair question and you should get a clear answer before "
       "anybody drives out, not afterwards."),
      ("Can I come to the shop?",
       "Call first. It is a working address in Bridgeview rather than a showroom, so there is "
       "not always somebody there to meet you."),
    ])

    crumb_html, crumb_ld = breadcrumbs([("Home", "index.html"), ("Contact", fn)])

    html = head("Contact a Chicagoland Painting Contractor | Colors Your Way",
                "Call " + PHONE_DISPLAY + " or text photos of the job. " + BRAND + ", "
                + STREET + ", " + CITY + ", " + REGION + " " + POSTAL + ". Painting and "
                "remodeling, Chicago and south suburbs.",
                fn, "hero-contact")
    html += header(fn)
    html += '<main id="main">\n' + crumb_html
    # The phone goes in the hero, at the top, and it is the biggest thing on the
    # page. This is a phone business with one number and no CRM, so the most
    # useful thing this page can do is put that number at thumb height on a
    # phone screen before anything else loads. Sized with clamp() inline rather
    # than in the stylesheet because it is the only element on the site that
    # needs it, and a new CSS rule would mean a cache-busting version bump.
    big_phone = ('<a href="tel:' + PHONE_E164 + '" style="display:block;margin:.6rem 0 .5rem;'
                 'font-size:clamp(2.1rem,1.2rem + 5vw,3.4rem);font-weight:800;line-height:1.05;'
                 'letter-spacing:-.02em;color:var(--blue-d);text-decoration:none">'
                 + PHONE_DISPLAY + '</a>')
    html += hero("Call us and tell us what you are looking at.",
                 "One number, and it goes to " + OWNER + " rather than a call center. "
                 + big_phone + " "
                 "Calls and texts both. A photo of the room, the wall or the front of the house "
                 "tells us more than anything you can type. We cover " + REGION_LONG + " from "
                 "our shop in " + CITY + ".",
                 "Contact &middot; " + REGION_SHORT, "hero-contact",
                 "Rather type it out?", "Fill this in and we will call you.",
                 page="Contact (contact.html)")

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">What happens next</p>\n'
             '    <h2>What happens after you get in touch</h2>\n'
             '    <ol class="nums">'
             '<li><strong>We talk for a few minutes.</strong> Which town, what needs doing, and '
             'roughly how old the house is. Nothing has to be exact and there is no script.</li>'
             '<li><strong>You send photos if you have them.</strong> Text them to the same '
             'number. Photos will not produce a final price, but they let us tell you what to '
             'expect and let you tell us what is bothering you without writing an essay.</li>'
             '<li><strong>We arrange a time to come and look.</strong> Somebody stands in the '
             'room, or walks all four sides of the house. That is the only way anybody can price '
             'this work honestly.</li>'
             '<li><strong>You get a number, and what sits behind it.</strong> What is included, '
             'how many coats, what the preparation is, and what happens to the price if the '
             'preparation turns out worse than it looks.</li>'
             '<li><strong>You decide, in your own time.</strong> There is no follow-up campaign '
             'and nobody chasing you. If you want to think about it, think about it.</li>'
             '</ol>\n  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap two-col">\n    <div>\n'
             '      <p class="eyebrow">Where we are</p>\n      <h2>The shop</h2>\n'
             '      <p><strong>' + BRAND + '</strong><br>' + STREET + '<br>' + CITY + ', '
             + REGION + ' ' + POSTAL + '</p>\n'
             '      <p><strong>Phone and text</strong><br>'
             '<a href="tel:' + PHONE_E164 + '">' + PHONE_DISPLAY + '</a></p>\n'
             '      ' + hours_html + '\n'
             '      <p style="font-size:.88rem;color:var(--ink-2)">Bridgeview is where the shop '
             'is, not the limit of where we work. It is a working address rather than a '
             'showroom, so call before you come by.</p>\n'
             '    </div>\n    ' + img("swatches") + '\n  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Paperwork</p>\n'
             '    <h2>What we can and cannot show you</h2>\n'
             '    ' + trust_row() + '\n'
             '    <p style="margin-top:18px;font-size:.93rem;color:var(--ink-2)">These stay '
             'marked as to supply until the real documents are handed over. Ask on the phone and '
             'you will get a straight answer either way.</p>\n  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Questions</p>\n'
             '    <h2>Before you pick up the phone</h2>\n'
             '    ' + faqrows + '  </div>\n</section>\n')
    html += cta()
    html += "</main>\n" + footer()

    contact_ld = {"@type": "ContactPage", "@id": canonical_url(fn) + "#webpage",
                  "url": canonical_url(fn), "name": "Contact " + BRAND,
                  "description": ("How to reach " + BRAND + ", painting and remodeling across "
                                  + REGION_LONG + ", based at " + STREET + " in Bridgeview, "
                                  "Illinois."),
                  "isPartOf": {"@id": SITE + "/#website"}, "inLanguage": "en-US",
                  "about": {"@id": SITE + "/#business"}}
    html += ld_json([contact_ld, faqld, crumb_ld])
    html += confirm_comment() + "</body>\n</html>\n"
    write(fn, html)
    return fn


def build_thankyou():
    """Where the form relay sends people after a successful submission.

    Three rules shaped this page.

    1. NO INVENTED SLA. "We respond within 24 hours" is a promise nobody here
       has authority to make on Mike's behalf, and the first time he is on a
       roof until seven it becomes a broken one. The page says he is on a job
       site during the day and that the phone is faster. That is true, it is
       useful, and it costs nothing to keep.
    2. It has to give the visitor somewhere to go. A dead-end confirmation is a
       bounce. So it points at the before and after gallery and at the notes,
       and it asks for the one thing that genuinely speeds up a quote: photos.
    3. It is PERMANENTLY noindex. Not the preview flag, which comes off at
       go-live. This one stays. See the note in head().

    Deliberately not in the sitemap either, for the same reason.
    """
    fn = "thank-you.html"
    crumbhtml, crumbld = breadcrumbs([("Home", "index.html"),
                                      ("Contact", "contact.html"),
                                      ("Message sent", None)])

    # The description length is audited (140 to 160) like every other page, even
    # though this one is permanently noindex and nothing will ever display it.
    # Keeping it in range costs nothing and stops the page tripping the build.
    html = head("Message sent | " + BRAND,
                "Your quote request reached " + OWNER + " and went straight to his phone. "
                "He gets back to people between jobs. If you are in a hurry, call "
                + PHONE_DISPLAY + ".",
                fn, "hero-contact", always_noindex=True)
    html += header("contact.html")
    html += crumbhtml
    html += '<main id="main">\n'

    html += ('<section>\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Message sent</p>\n'
             '    <h1>That reached ' + OWNER + '.</h1>\n'
             '    <p class="lede">Your details went straight to his phone. There is one number '
             'and the owner reads it, so nothing is sitting in a call center queue waiting to be '
             'assigned to somebody.</p>\n'
             '  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">What happens next</p>\n'
             '    <h2>In order</h2>\n'
             '    <ol class="steps">\n'
             '      <li><strong>' + OWNER + ' calls you back.</strong> He runs the jobs, so he is '
             'out on site most of the day and realistically that is between jobs, at lunch, or in '
             'the evening. If you need an answer sooner than that, calling is faster than '
             'waiting.</li>\n'
             '      <li><strong>A few questions on the phone.</strong> The town, roughly what '
             'needs doing, and the age of the house. You will get a useful idea of what is '
             'involved and what tends to move the number.</li>\n'
             '      <li><strong>We stand in front of it.</strong> No final number gets '
             'quoted without a walk-through, because the two things that decide an interior job '
             'are the condition of what is already on the wall and how much trim there is. '
             'Neither is visible over the phone.</li>\n'
             '    </ol>\n'
             '  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">In a hurry</p>\n'
             '    <h2>Call, do not wait.</h2>\n'
             '    <p style="font-size:1.5rem;font-weight:700;margin:0 0 6px">'
             '<a href="tel:' + PHONE_E164 + '">' + PHONE_DISPLAY + '</a></p>\n'
             '    <p style="font-size:.93rem;color:var(--ink-2)">Same number, and it goes to '
             + OWNER + '.</p>\n'
             '    <p style="margin-top:22px"><strong>One thing that genuinely speeds this up: '
             'send photos.</strong> Text pictures of the room, the wall or the front of the house '
             'to <a href="sms:' + PHONE_E164 + '">' + PHONE_DISPLAY + '</a>. Photos are how you '
             'get told what to expect before anybody drives out.</p>\n'
             '  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">While you wait</p>\n'
             '    <h2>Worth a look</h2>\n'
             '    <p>Two things that answer most of what people ask on the first call.</p>\n'
             '    <div class="btnrow" style="margin-top:18px">'
             '<a class="btn" href="index.html#work">See before and after</a>'
             '<a class="btn btn-b" href="blog/index.html">Read the notes</a></div>\n'
             '    <p style="margin-top:18px;font-size:.93rem;color:var(--ink-2)">The notes cover '
             'how to tell real prep from a fast cheap job, when refinishing cabinets beats '
             'replacing them, and what actually drives the number on a repaint.</p>\n'
             '  </div>\n</section>\n')

    html += "</main>\n" + footer()
    html += ld_json([webpage_ld(fn, "Message sent", "Confirmation that your quote request "
                                "reached " + OWNER + " at " + BRAND + "."), crumbld])
    html += confirm_comment() + "</body>\n</html>\n"
    write(fn, html)
    return fn


# ---------------------------------------------------------------- blog
# Posts are written into blog/ as Markdown with YAML front matter by the content
# side of this project. build.py renders them into real pages using the same
# shell as the rest of the site, so a post automatically gets the header, the
# phone number, the sticky mobile call bar, the footer, the schema and the
# noindex. Adding a post is: drop the .md in, re-run build.py. Nothing to
# register anywhere.
#
# The renderer covers exactly the Markdown these posts use: h2, h3, paragraphs,
# bold, italic, links, pipe tables, ordered and unordered lists, blockquotes,
# horizontal rules, and raw HTML blocks (the posts embed hand-built inline SVG
# figures, which pass through untouched). It is deliberately not a general
# purpose Markdown engine, and it fails loudly rather than silently mangling
# something it does not understand.

BLOG_DIR = os.path.join(HERE, "blog")
BLOG_SKIP = ("index.md", "README.md")

# Short <title> strings for the posts.
#
# The h1 headlines are 79 to 122 characters, which is right for a reader and
# far too long for a title tag. Google renders roughly 600 pixels of title, so
# anything past about 60 characters is cut with an ellipsis and the keyword at
# the front is the only part that survives. These are the front-loaded versions.
# Adding " | Colors Your Way USA" costs 22 characters, so each string below has
# to come in at 37 or fewer.
#
# A post can override this with `seo_title` in its own front matter. A post with
# neither fails the build rather than shipping a truncated title.
BLOG_SEO_TITLE = {
    "interior-painting-cost-southwest-chicago-suburbs": "Interior Painting Cost, SW Suburbs",
    "how-to-tell-good-prep-from-a-fast-cheap-job":      "How to Spot Good Paint Prep Work",
    "best-time-to-paint-house-exterior-chicago":        "Best Time to Paint a Chicago Exterior",
    "cabinet-refinishing-vs-replacing":                 "Cabinet Refinishing vs Replacing Cost",
    "choosing-paint-colors-older-southwest-suburb-homes": "Paint Colors for Older Suburb Homes",
    "rental-turnover-painting-southwest-suburbs":       "Rental Turnover Painting, SW Suburbs",
}

# Posts link to service pages using a directory style URL that this site does
# not use, and to two pages that deliberately do not exist yet. Every internal
# target a post can name has to be mapped here. An unmapped one FAILS THE BUILD,
# because a dead internal link on a nine page site is inexcusable and is exactly
# the kind of thing nobody notices for a year.
LINK_MAP = {
    "/": "../index.html",
    "/interior-painting/": "../interior-painting.html",
    "/exterior-painting/": "../exterior-painting.html",
    "/cabinet-painting/": "../cabinet-refinishing.html",
    "/cabinet-refinishing/": "../cabinet-refinishing.html",
    "/drywall-repair-and-painting/": "../drywall-and-repair.html",
    "/drywall-and-repair/": "../drywall-and-repair.html",
    "/remodeling/": "../remodeling.html",
    "/service-area/": "../areas/index.html",
    "/areas/": "../areas/index.html",
    "/contact/": "../contact.html",
    # Not built yet. Both are on the month 2 to 3 queue in
    # 08-SEO-AND-KEYWORD-RESEARCH.md section 7. Point them at the closest real
    # page rather than shipping a 404, and re-point them when the pages exist.
    "/rental-turnover-painting/": "../areas/index.html",
    "/deck-and-fence-staining/": "../exterior-painting.html",
    # The dedicated cost page is blocked on the local quote protocol. See the
    # note on PRICING_RANGES at the top of this file. The cost post is the
    # closest real thing on the site today.
    "/painting-cost-southwest-suburbs/":
        "interior-painting-cost-southwest-chicago-suburbs.html",
}

BLOCK_TAGS = ("figure", "div", "table", "details", "svg", "aside", "section")

# Plain-language name of each real page, keyed by the path a blog post ends up
# pointing at. Used for the "See our X page" button, which must describe where
# the reader actually lands.
PAGE_LABEL = {
    "../index.html": "home",
    "../interior-painting.html": "interior painting",
    "../exterior-painting.html": "exterior painting",
    "../cabinet-refinishing.html": "cabinet refinishing",
    "../drywall-and-repair.html": "drywall and repair",
    "../remodeling.html": "remodeling and trades",
    "../areas/index.html": "service areas",
    "../contact.html": "contact",
}


def _scalar(v):
    v = v.strip()
    if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v == "true":
        return True
    if v == "false":
        return False
    if re.match(r"^-?\d+$", v):
        return int(v)
    return v


def parse_front_matter(text):
    """Small YAML subset: scalars, one level of nested map, and lists of scalars.

    Not a YAML parser and not pretending to be one. It handles exactly the shape
    these posts use, and anything outside that shape is ignored rather than
    guessed at.
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    raw = text[text.find("\n") + 1:end]
    body = text[end + 4:]
    data, key = {}, None
    for line in raw.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        s = line.strip()
        if indent == 0:
            m = re.match(r"^([A-Za-z_]\w*):\s*(.*)$", s)
            if not m:
                continue
            key = m.group(1)
            val = m.group(2).strip()
            data[key] = _scalar(val) if val else None
        elif key:
            if s.startswith("- "):
                if not isinstance(data.get(key), list):
                    data[key] = []
                data[key].append(_scalar(s[2:]))
            else:
                m = re.match(r"^([A-Za-z_]\w*):\s*(.*)$", s)
                if m:
                    if not isinstance(data.get(key), dict):
                        data[key] = {}
                    data[key][m.group(1)] = _scalar(m.group(2))
    return data, body


def map_link(url, slugs, where):
    """Rewrite one link. Unknown internal targets stop the build."""
    if url.startswith(("http://", "https://", "tel:", "sms:", "mailto:", "#")):
        return url
    m = re.match(r"^/blog/([a-z0-9-]+)/?$", url)
    if m:
        if m.group(1) not in slugs:
            sys.exit("BUILD FAILED: " + where + " links to /blog/" + m.group(1) +
                     "/ but there is no such post. Fix the link or add the post.")
        return m.group(1) + ".html"
    if url in LINK_MAP:
        return LINK_MAP[url]
    if url.startswith("/"):
        sys.exit("BUILD FAILED: " + where + " links to " + url + " which is not in "
                 "LINK_MAP in build.py. Add a mapping or fix the link. Refusing to "
                 "ship a dead internal link.")
    return url


def inline(s, slugs, where):
    """Inline markup. Escapes bare ampersands, leaves angle brackets alone
    because the posts embed real HTML and none of them use a stray '<' in prose."""
    s = re.sub(r"&(?!#?\w+;)", "&amp;", s)
    def link(m):
        url = map_link(m.group(2).strip(), slugs, where)
        ext = ""
        if url.startswith("http"):
            ext = ' rel="nofollow noopener" target="_blank"'
        return '<a href="' + url + '"' + ext + ">" + m.group(1) + "</a>"
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    return s


def markdown(text, slugs, where):
    lines = text.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()

        # raw HTML block: passthrough until the matching close tag at column 0
        m = re.match(r"^<([a-zA-Z][a-zA-Z0-9]*)", line)
        if m and m.group(1) in BLOCK_TAGS:
            tag = m.group(1)
            buf = [line]
            i += 1
            while i < n and not re.match(r"^</" + tag + r">", lines[i]):
                buf.append(lines[i])
                i += 1
            if i < n:
                buf.append(lines[i])
                i += 1
            out.append("\n".join(buf))
            continue

        if not s:
            i += 1
            continue

        if s == "---" or re.match(r"^-{3,}$", s):
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{2,3})\s+(.*)$", s)
        if m:
            lv = len(m.group(1))
            txt = inline(m.group(2).strip(), slugs, where)
            anchor = re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", txt).lower()).strip("-")[:60]
            out.append("<h%d id=\"%s\">%s</h%d>" % (lv, anchor, txt, lv))
            i += 1
            continue

        # pipe table
        if s.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            def cells(row):
                return [c.strip() for c in row.strip().strip("|").split("|")]
            head = cells(lines[i])
            i += 2
            body = []
            while i < n and lines[i].strip().startswith("|"):
                body.append(cells(lines[i]))
                i += 1
            t = ['<div class="tw"><table><thead><tr>']
            t += ["<th>" + inline(c, slugs, where) + "</th>" for c in head]
            t.append("</tr></thead><tbody>")
            for r in body:
                t.append("<tr>" + "".join("<td>" + inline(c, slugs, where) + "</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue

        # lists (no nesting in these posts; wrapped lines are indented continuations)
        m = re.match(r"^([-*+]|\d+\.)\s+(.*)$", s)
        if m:
            ordered = not m.group(1) in ("-", "*", "+")
            items = []
            while i < n:
                cur = lines[i]
                mm = re.match(r"^([-*+]|\d+\.)\s+(.*)$", cur.strip())
                if not cur.strip():
                    break
                if mm and (len(cur) - len(cur.lstrip())) == 0:
                    items.append([mm.group(2).strip()])
                elif items and (len(cur) - len(cur.lstrip())) > 0:
                    items[-1].append(cur.strip())
                else:
                    break
                i += 1
            tag = "ol" if ordered else "ul"
            out.append("<" + tag + ' class="md">' +
                       "".join("<li>" + inline(" ".join(x), slugs, where) + "</li>" for x in items) +
                       "</" + tag + ">")
            continue

        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append("<blockquote><p>" + inline(" ".join(buf), slugs, where) + "</p></blockquote>")
            continue

        # paragraph: join the wrapped lines back together
        buf = []
        while i < n and lines[i].strip() and not re.match(
                r"^(#{2,3}\s|\||>|<|-{3,}$|([-*+]|\d+\.)\s)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            out.append("<p>" + inline(" ".join(buf), slugs, where) + "</p>")
        else:
            i += 1
    return "\n".join(out)


def discover_posts():
    if not os.path.isdir(BLOG_DIR):
        return []
    posts = []
    for f in sorted(os.listdir(BLOG_DIR)):
        if not f.endswith(".md") or f in BLOG_SKIP:
            continue
        fm, body = parse_front_matter(io.open(os.path.join(BLOG_DIR, f), encoding="utf-8").read())
        if not fm.get("title"):
            print("  skipped %s: no title in front matter" % f)
            continue
        fm["_src"] = f
        fm["_body"] = body
        fm.setdefault("slug", f[:-3])
        fm.setdefault("order", 99)
        fm.setdefault("category", "Notes")
        posts.append(fm)
    posts.sort(key=lambda p: (str(p.get("category")), p.get("order") or 99))
    return posts


def build_post(p, posts):
    slugs = set(x["slug"] for x in posts)
    where = "blog/" + p["_src"]
    fn = os.path.join("blog", p["slug"] + ".html")
    body = markdown(p["_body"], slugs, where)

    hero = p.get("hero") or {}
    hero_html = ""
    if hero.get("src"):
        hp = os.path.join(BLOG_DIR, hero["src"])
        if not os.path.exists(hp):
            sys.exit("BUILD FAILED: " + where + " hero image " + hero["src"] + " is missing.")
        cred = ""
        if hero.get("credit"):
            c = esc(str(hero["credit"]))
            if hero.get("credit_url"):
                c = ('<a href="' + hero["credit_url"] + '" rel="nofollow noopener" '
                     'target="_blank">' + c + "</a>")
            cred = '<figcaption class="cred">Stock photo. ' + c + "</figcaption>"
        hero_html = ('<figure class="post-hero"><img src="' + hero["src"] + '" alt="' +
                     esc(str(hero.get("alt", ""))) + '" width="' + str(hero.get("width", 1600)) +
                     '" height="' + str(hero.get("height", 1067)) +
                     '" fetchpriority="high" decoding="async">' + cred + "</figure>")

    # If a post quotes money, build.py states the pricing position itself rather
    # than trusting every future post to remember to. This is the house rule that
    # market ranges are never presented as this business's price.
    money = ""
    if "$" in body:
        # h2, not h3. This block is the first heading after the post h1, so an
        # h3 here skipped a level on every post that quotes a number.
        money = ('<div class="callout"><h2>About the numbers on this page</h2>'
                 '<p>Every dollar figure below is a published market range from the sources '
                 'listed at the end of the post. None of it is a ' + BRAND + ' price. Every job '
                 'is quoted after a walk-through, because the two things that decide the number '
                 'are the condition of what is already there and how much trim is involved, and '
                 'neither of those is visible in a photograph.</p></div>')

    stock = ""
    if p.get("stock_photos"):
        stock = ('<p class="ph-note"><strong>The photographs on this page are stock.</strong> '
                 'They are placeholders until ' + OWNER + '&rsquo;s own job photos are '
                 'available. Any diagrams are drawn for this post.</p>')

    svc = ""
    if p.get("service_page"):
        target = map_link(str(p["service_page"]), slugs, where)
        label = PAGE_LABEL.get(target)
        if not label:
            sys.exit("BUILD FAILED: " + where + " service_page resolves to " + target +
                     " which has no entry in PAGE_LABEL. Add one so the button says "
                     "where the link actually goes.")
        svc = ('<p style="margin-top:1.6rem"><a class="btn btn-o" href="' + target +
               '">See our ' + label + ' page</a></p>')

    # The front matter writes related targets as "some-slug.html". The lookup is
    # keyed on the bare slug, so every related list silently resolved to nothing
    # and not one post rendered a Related block. Normalize instead of demanding
    # every future post remember which of the two forms this code wanted, and
    # fail loudly on a name that is neither.
    rel = ""
    by_slug = dict((x["slug"], x) for x in posts)
    rl = []
    for r in (p.get("related") or []):
        key = str(r).strip().strip("/")
        if key.endswith(".html"):
            key = key[: -len(".html")]
        if key not in by_slug:
            sys.exit("BUILD FAILED: " + where + " lists related post " + repr(str(r)) +
                     " but there is no post with slug " + repr(key) + " in blog/.")
        if key != p["slug"]:
            rl.append(by_slug[key])
    if rl:
        rel = ('<p class="eyebrow" style="margin-top:2.2rem">Related</p><div class="pills">' +
               "".join('<a class="pill" href="' + r["slug"] + '.html">' + esc(str(r["title"])) +
                       "</a>" for r in rl) + "</div>")

    when = str(p.get("date", ""))
    title = esc(str(p["title"]))
    desc = str(p.get("description", ""))

    # The h1 stays the full descriptive headline, because that is what serves a
    # reader who has landed on the page. The <title> is a separate, shorter
    # string, because the h1 headlines run 79 to 122 characters and Google cuts
    # a title tag off around 60. Front matter `seo_title` wins if present.
    seo = str(p.get("seo_title") or BLOG_SEO_TITLE.get(p["slug"], "")).strip()
    if not seo:
        sys.exit("BUILD FAILED: " + where + " has no short title for the <title> tag. Add a "
                 "`seo_title` to the front matter, or an entry in BLOG_SEO_TITLE in build.py. "
                 "The h1 headline is too long to use as a title tag.")

    art_meta = ""
    if when:
        art_meta = ('<meta property="article:published_time" content="' + when + '">\n'
                    '<meta property="article:modified_time" content="' + when + '">\n')
    art_meta += ('<meta property="article:section" content="' +
                 esc(str(p.get("category", "Notes"))) + '">\n')

    og_img = og_alt = None
    og_wh = None
    if hero.get("src"):
        og_img = SITE + "/blog/" + hero["src"]
        og_alt = str(hero.get("alt", ""))
        og_wh = (hero.get("width", 1600), hero.get("height", 1067))

    # The short title, not the h1. A 122 character headline in a breadcrumb
    # wraps to three lines on a phone and reads as noise.
    crumb_html, crumb_ld = breadcrumbs(
        [("Home", "index.html"), ("Notes", "blog/index.html"), (esc(seo), None)], up="../")

    html = head(seo + " | " + BRAND, desc, "blog/" + p["slug"] + ".html", "hero-blog", up="../",
                og_type="article", og_image=og_img, og_image_alt=og_alt, og_image_wh=og_wh,
                extra_meta=art_meta)
    html += header("", up="../")
    html += '<main id="main">\n' + crumb_html + '<article class="post">\n  <div class="wrap narrow">\n'
    html += '    <p class="eyebrow"><a href="index.html">Notes</a> &middot; ' + \
            esc(str(p.get("category"))) + "</p>\n"
    html += "    <h1>" + title + "</h1>\n"
    if desc:
        html += '    <p class="lede">' + esc(desc) + "</p>\n"
    if when:
        html += '    <p class="post-meta"><time datetime="' + when + '">' + when + \
                "</time> &middot; " + BRAND + ", Bridgeview, IL</p>\n"
    html += "  </div>\n"
    if hero_html:
        html += '  <div class="wrap">' + hero_html + "</div>\n"
    html += '  <div class="wrap narrow prose">\n' + money + stock + body + svc + rel + \
            "\n  </div>\n</article>\n"
    html += cta(up="../")
    html += "</main>\n" + footer(up="../")

    # BlogPosting, not the generic Article. It is the correct subtype for a post
    # that lives inside a Blog node, and the Blog node on blog/index.html
    # already points back here.
    art = {
        "@type": "BlogPosting",
        "@id": canonical_url("blog/" + p["slug"] + ".html") + "#post",
        "headline": str(p["title"])[:110],
        "description": desc,
        "url": canonical_url("blog/" + p["slug"] + ".html"),
        "inLanguage": "en-US",
        "isPartOf": {"@id": SITE + "/blog/#blog"},
        "author": {"@id": SITE + "/#business"},
        "publisher": {"@id": SITE + "/#business"},
        "mainEntityOfPage": canonical_url("blog/" + p["slug"] + ".html"),
        "articleSection": str(p.get("category", "Notes")),
    }
    if p.get("keywords"):
        art["keywords"] = ", ".join(str(k) for k in p["keywords"])
    if when:
        art["datePublished"] = when
        art["dateModified"] = when
    if hero.get("src"):
        art["image"] = SITE + "/blog/" + hero["src"]
    html += ld_json([art, crumb_ld])
    html += confirm_comment() + "</body>\n</html>\n"
    write(fn, html)
    return fn


def build_blog(posts):
    """The index is generated from each post's own front matter (category and
    order), so publishing a post never means remembering to edit an index."""
    fn = os.path.join("blog", "index.html")
    if posts:
        body, cat = "", None
        for p in posts:
            if p.get("category") != cat:
                cat = p.get("category")
                body += '<p class="tier">' + esc(str(cat)) + "</p>"
            when = ('<time datetime="' + str(p["date"]) + '">' + str(p["date"]) + "</time><br>") \
                if p.get("date") else ""
            body += ('<li>' + when + '<h3><a href="' + p["slug"] + '.html">' +
                     esc(str(p["title"])) + "</a></h3>" +
                     ('<p>' + esc(str(p.get("description", ""))) + "</p>"
                      if p.get("description") else "") + "</li>")
        body = '<ul class="posts">' + body + "</ul>"
    else:
        body = ('<div class="empty"><p><strong>Nothing published yet.</strong></p>'
                '<p style="margin:0">Posts are written as Markdown into the <code>blog/</code> '
                'folder and this page lists them automatically on the next build.</p></div>')

    crumb_html, crumb_ld = breadcrumbs(
        [("Home", "index.html"), ("Notes", "blog/index.html")], up="../")

    html = head("Painting and Remodeling Notes | " + BRAND,
                "What painting, cabinet and repair work actually involves in Chicago and the "
                "south suburbs. Costs, prep, timing and color, from a Bridgeview "
                "contractor.",
                "blog/index.html", "hero-blog", up="../")
    html += header("", up="../")
    html += '<main id="main">\n' + crumb_html
    html += ('<section class="hero">\n  <div class="wrap hero-in">\n'
             '    <div class="hero-copy">\n'
             '      <p class="eyebrow">Notes</p>\n'
             '      <h1>Straight answers, written down.</h1>\n'
             '      <p class="lede">Most of what people want to know before they call a painter is '
             'the same handful of questions: what changes the price, how many coats, whether the '
             'repair is included, and what an older house needs that a newer one does not. These '
             'are the answers, written out properly. Every price quoted is a published market '
             'range with its source named, never our price.</p>\n'
             '    </div>\n'
             '    <div class="hero-form" id="quote">' + quote_form(
                 "Ask for a quote", "Reading is fine. A phone call is faster.",
                 page="Notes (blog/index.html)", up="../") +
             '</div>\n'
             '    <div class="hero-shot"><div class="hero-photo">'
             + img("hero-blog", lazy=False, up="../") + '</div></div>\n'
             '  </div>\n</section>\n')
    # The summaries below repeat market ranges out of the posts, so the same
    # pricing position has to be stated here as it is on each post.
    money = ('<div class="callout"><h3>About the numbers in these posts</h3>'
             '<p>Every dollar figure in these posts is a published market range from a named '
             'cost source. None of it is a ' + BRAND + ' price. Every job is quoted after a '
             'walk-through. Sources are listed at the end of each post.</p></div>') \
        if "$" in body else ""
    html += ('<section>\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Posts</p>\n    <h2>All notes</h2>\n'
             '    ' + money + body + '\n  </div>\n</section>\n')
    html += cta(up="../")
    html += "</main>\n" + footer(up="../")
    html += ld_json([{"@type": "Blog", "@id": SITE + "/blog/#blog",
                      "url": SITE + "/blog/", "name": "Notes from " + BRAND,
                      "publisher": {"@id": SITE + "/#business"}, "inLanguage": "en-US",
                      "blogPost": [{"@type": "BlogPosting",
                                    "@id": canonical_url("blog/" + p["slug"] + ".html") + "#post",
                                    "headline": str(p["title"])[:110],
                                    "url": canonical_url("blog/" + p["slug"] + ".html")}
                                   for p in posts]}, crumb_ld])
    html += confirm_comment() + "</body>\n</html>\n"
    write(fn, html)
    return fn


# ---------------------------------------------------------------- site files

# Pages that are built but deliberately kept out of the sitemap. A sitemap is a
# list of URLs you WANT indexed, so anything carrying a permanent noindex must
# not appear in it. Listing a noindexed URL is a direct contradiction and it is
# what produces "Submitted URL marked noindex" errors in Search Console.
# thank-you.html is permanently noindex because an indexed thank-you page ruins
# the conversion count it exists to produce. service-area.html is permanently
# noindex because its content moved to areas/index.html and listing both would
# be asking Google to index two pages about the same thing.
SITEMAP_EXCLUDE = ("thank-you.html", "service-area.html")


def build_sitemap(pages, posts):
    # `pages` already contains every rendered file, including the blog posts
    # returned by build_post(). Do not append `posts` a second time: that
    # emitted every post twice and a duplicate <loc> is an invalid sitemap.
    #
    # No <priority> and no <changefreq>. Google has stated it ignores both, so
    # they are noise that invites someone to argue about numbers that do not do
    # anything. <lastmod> IS used, so it is emitted only where a real date
    # exists: the post front matter. A made-up lastmod on every URL is worse
    # than none, because once Google learns the dates are fiction it stops
    # trusting the field.
    post_date = dict(("blog/" + p["slug"] + ".html", str(p.get("date", ""))) for p in posts)
    urls = []
    seen = set()
    for p in pages:
        key = p.replace(os.sep, "/")
        if key in seen or key in SITEMAP_EXCLUDE:
            continue
        seen.add(key)
        row = "  <url><loc>" + canonical_url(key) + "</loc>"
        when = post_date.get(key)
        if when and re.match(r"^\d{4}-\d{2}-\d{2}$", when):
            row += "<lastmod>" + when + "</lastmod>"
        urls.append(row + "</url>")
    note = ""
    if NOINDEX:
        note = ("<!-- PREVIEW: robots.txt currently disallows everything and every page carries\n"
                "     noindex, so this sitemap is not yet doing anything. Both come off together\n"
                "     at go-live. -->\n")
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n' + note +
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "\n".join(urls) + "\n</urlset>\n")


def build_robots():
    if NOINDEX:
        # NOTE: Disallow blocks crawling, which also stops Google reading the
        # noindex meta tag on the pages themselves. That is fine while both are
        # on together, and it is exactly why they must flip together. Shipping
        # Disallow WITHOUT the meta tag would let already-known URLs appear in
        # results as a bare link with no snippet.
        txt = ("# PREVIEW BUILD. Everything is blocked on purpose.\n"
               "# Remove this block at go-live by setting NOINDEX = False in build.py\n"
               "# and re-running. Leaving it in place is the most common way a launch\n"
               "# quietly produces nothing for six months.\n"
               "User-agent: *\nDisallow: /\n")
    else:
        txt = ("User-agent: *\nAllow: /\n\n"
               "# The thank-you page carries a permanent noindex and is not in the sitemap.\n"
               "# It is left crawlable on purpose: a page blocked in robots.txt cannot have\n"
               "# its noindex read.\n\n"
               "Sitemap: " + SITE + "/sitemap.xml\n")
    write("robots.txt", txt)


def write(relpath, content):
    path = os.path.join(HERE, relpath)
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(path, "w", encoding="utf-8").write(content)


# =============================================================================
# AUDIT
# =============================================================================
# Cheap guards against the four ways this deliverable becomes unusable. Runs on
# every build. Not a substitute for reading it, but it catches a paste.

BANNED = [
    (u"—", "em dash (house rule: use periods, commas, colons or parentheses)"),
    (u"–", "en dash"),
    ("licensed and insured", "unsupported credential claim"),
    ("licensed, bonded", "unsupported credential claim"),
    ("years of experience", "unsupported claim, no year count has been supplied"),
    ("years in business", "unsupported claim, no year count has been supplied"),
    ("jobs completed", "unsupported claim, no job count has been supplied"),
    ("aggregateRating", "review markup with no reviews behind it"),
    ("5 stars", "invented rating"),
    ("5-star", "invented rating"),
    ("free estimate", "not established, and it is the exact phrase all 12 competitors use"),
]
UK = [("analyse", "analyze"), ("prioritise", "prioritize"), ("colour", "color"),
      ("centre", "center"), ("organise", "organize"), ("labour", "labor"),
      ("neighbourhood", "neighborhood"), ("licence", "license")]

def audit(files):
    problems = []
    for f in files:
        txt = io.open(os.path.join(HERE, f), encoding="utf-8").read()
        low = txt.lower()
        for needle, why in BANNED:
            if needle.lower() in low:
                problems.append(f + ": contains " + repr(needle) + " (" + why + ")")
        for bad, good in UK:
            # skip matches inside urls and attribute names
            for m in re.finditer(r"\b" + bad + r"\w*", low):
                seg = low[max(0, m.start() - 60):m.start()]
                if "http" in seg.split(" ")[-1]:
                    continue
                problems.append(f + ": UK spelling " + repr(m.group(0)) + ", use " + good)
                break
        if "$" in txt:
            # Dollar figures are banned as this business's prices. The rule is
            # now uniform rather than a per-folder exception list, because the
            # service pages started carrying blog teasers that quote market
            # ranges and the old blog-only carve-out let that through silently.
            #
            # ONE exception, and it is checked rather than assumed:
            #   areas/*.html       Census median HOME values. Facts about towns,
            #                      not prices for work. The exemption is NOT a
            #                      blanket one: the page has to carry CENSUS_MARK,
            #                      the sentence that says in so many words that
            #                      the dollar figure is a house value and not a
            #                      price. Stripping that sentence fails the build,
            #                      which is the point.
            #
            # Everywhere else, any page that shows a dollar figure must also
            # carry the market-range disclaimer and must name a source. Both
            # blocks are injected by the builders, so a page that quotes money
            # and forgets them is a build bug, not a copy decision.
            key = f.replace(os.sep, "/")
            if key.startswith(CITY_DIR + "/"):
                if CENSUS_MARK not in txt:
                    problems.append(key + ": shows a dollar figure but is missing the "
                                          "sentence that says it is a Census home value and "
                                          "not a price. See CENSUS_MARK in build.py.")
            else:
                if "None of it is a " + BRAND + " price" not in txt:
                    problems.append(f + ": quotes money but is missing the market-range "
                                        "disclaimer. No figure may read as this business's "
                                        "price.")
                if "References" not in txt and "ource" not in txt:
                    problems.append(f + ": quotes money with no sources named.")
    return problems


# =============================================================================
# SEO AUDIT
# =============================================================================
# The on-page rules from 08-SEO-AND-KEYWORD-RESEARCH.md section 6, enforced
# instead of documented. Every one of these was a real defect in the build
# before it was added, which is the argument for having it: a title that grew
# past 60 characters, a duplicated meta description or a lost h1 is invisible
# in a browser and obvious in a SERP six weeks later.
#
# These FAIL the build. That is deliberate. A warning nobody reads is the same
# as no check at all, and the fix is always a one-line string edit.

TITLE_MAX = 60      # Google renders roughly 600px. Past ~60 chars it truncates.
DESC_MIN = 140      # Shorter than this and the SERP pads it with page text.
DESC_MAX = 160      # Longer than this and it gets cut mid-sentence.
ALT_MAX = 125       # Past this a screen reader user is listening to an essay.


def _tag(html, pattern, flags=re.S):
    m = re.search(pattern, html, flags)
    return m.group(1) if m else None


def _unescape(s):
    return (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&#39;", "'").replace("&rsquo;", "'")
             .replace("&middot;", "-").replace("&rarr;", "->").replace("&nbsp;", " "))


def seo_audit(files):
    problems = []
    titles, descs, canons = {}, {}, {}

    for f in files:
        key = f.replace(os.sep, "/")
        txt = io.open(os.path.join(HERE, f), encoding="utf-8").read()
        head_html = txt.split("</head>", 1)[0]

        # ---- title -------------------------------------------------------
        t = _tag(head_html, r"<title>(.*?)</title>")
        if not t:
            problems.append(key + ": no <title>.")
        else:
            t = _unescape(t)
            if len(t) > TITLE_MAX:
                problems.append(key + ": title is " + str(len(t)) + " chars, max is " +
                                str(TITLE_MAX) + ". Trim " + str(len(t) - TITLE_MAX) +
                                ". -> " + repr(t))
            titles.setdefault(t, []).append(key)

        # ---- meta description --------------------------------------------
        d = _tag(head_html, r'<meta name="description" content="(.*?)">')
        if not d:
            problems.append(key + ": no meta description.")
        else:
            d = _unescape(d)
            n = len(d)
            # Permanently noindexed pages are exempt from the length window. A
            # thank-you page will never appear in a SERP, so padding its
            # description to 140 characters is writing for a robot that has
            # been told not to look. It still needs one, for link previews.
            if key not in SITEMAP_EXCLUDE and (n < DESC_MIN or n > DESC_MAX):
                problems.append(key + ": meta description is " + str(n) + " chars, wanted " +
                                str(DESC_MIN) + " to " + str(DESC_MAX) + ". -> " + repr(d))
            descs.setdefault(d, []).append(key)

        # ---- canonical ----------------------------------------------------
        c = _tag(head_html, r'<link rel="canonical" href="(.*?)">')
        expected = canonical_url(key)
        if not c:
            problems.append(key + ": no canonical link.")
        elif c != expected:
            problems.append(key + ": canonical is " + c + ", expected " + expected)
        else:
            canons.setdefault(c, []).append(key)

        # ---- open graph and twitter ---------------------------------------
        for prop in ("og:type", "og:title", "og:description", "og:url", "og:image",
                     "og:image:alt", "og:site_name"):
            if 'property="' + prop + '"' not in head_html:
                problems.append(key + ": missing " + prop + ".")
        for name in ("twitter:card", "twitter:title", "twitter:description",
                     "twitter:image", "twitter:image:alt"):
            if 'name="' + name + '"' not in head_html:
                problems.append(key + ": missing " + name + ".")
        ogimg = _tag(head_html, r'<meta property="og:image" content="(.*?)">')
        if ogimg:
            rel = ogimg[len(SITE) + 1:] if ogimg.startswith(SITE + "/") else None
            if rel is None or not os.path.exists(os.path.join(HERE, rel)):
                problems.append(key + ": og:image points at " + str(ogimg) +
                                " which is not a file in this repo.")

        # ---- headings ------------------------------------------------------
        levels = [int(x) for x in re.findall(r"<h([1-6])\b", txt)]
        h1 = levels.count(1)
        if h1 != 1:
            problems.append(key + ": " + str(h1) + " h1 elements, there must be exactly 1.")
        prev = None
        for lv in levels:
            if prev is not None and lv > prev + 1:
                problems.append(key + ": heading level jumps h" + str(prev) + " to h" +
                                str(lv) + ". No level may be skipped.")
                break
            prev = lv

        # ---- landmarks and the skip link -----------------------------------
        for needle, why in (('<main id="main">', "no <main id=\"main\"> landmark"),
                            ('<a class="skip" href="#main">', "no skip link"),
                            ('<html lang="en">', "no lang on <html>"),
                            ("<footer>", "no footer landmark"),
                            ('<nav class="nav"', "no primary nav landmark")):
            if needle not in txt:
                problems.append(key + ": " + why + ".")

        # ---- images --------------------------------------------------------
        for m in re.finditer(r"<img\b[^>]*>", txt):
            tag = m.group(0)
            if "width=" not in tag or "height=" not in tag:
                problems.append(key + ": <img> without width and height (layout shift): " +
                                tag[:110])
            alt = re.search(r'alt="([^"]*)"', tag)
            if alt is None:
                problems.append(key + ": <img> with no alt attribute: " + tag[:110])
                continue
            a = _unescape(alt.group(1))
            if not a and 'aria-hidden="true"' not in tag:
                problems.append(key + ": <img> with empty alt that is not marked decorative: " +
                                tag[:110])
            if len(a) > ALT_MAX:
                problems.append(key + ": alt text is " + str(len(a)) + " chars, max " +
                                str(ALT_MAX) + ". -> " + repr(a))
            # Keyword stuffing check: the town and the word "painter" repeated
            # inside one alt string is the classic tell.
            low = a.lower()
            for word in ("painting", "painter", "bridgeview", "contractor"):
                if low.count(word) > 1:
                    problems.append(key + ": alt text repeats " + repr(word) +
                                    ", which reads as keyword stuffing. -> " + repr(a))

        # ---- form fields ----------------------------------------------------
        for m in re.finditer(r"<(input|select|textarea)\b[^>]*>", txt):
            tag = m.group(0)
            if 'type="hidden"' in tag or 'type="submit"' in tag:
                continue
            fid = re.search(r'id="([^"]+)"', tag)
            if not fid:
                problems.append(key + ": form control with no id, so it cannot be labelled: " +
                                tag[:110])
                continue
            if ('for="' + fid.group(1) + '"') not in txt and "aria-label" not in tag:
                problems.append(key + ": form control " + fid.group(1) + " has no <label for>.")

        # ---- lazy loading ---------------------------------------------------
        imgs = re.findall(r"<img\b[^>]*>", txt)
        eager = [i for i in imgs if 'loading="lazy"' not in i and 'aria-hidden' not in i]
        if len(eager) > 1:
            problems.append(key + ": " + str(len(eager)) + " images load eagerly. Only the LCP "
                            "hero should. Everything below the fold takes loading=\"lazy\".")

    for t, where in titles.items():
        if len(where) > 1:
            problems.append("duplicate <title> on " + ", ".join(where) + ": " + repr(t))
    for d, where in descs.items():
        if len(where) > 1:
            problems.append("duplicate meta description on " + ", ".join(where) + ": " + repr(d))
    for c, where in canons.items():
        if len(where) > 1:
            problems.append("duplicate canonical " + c + " on " + ", ".join(where))

    # ---- pillar and cluster, both directions --------------------------------
    for s in SERVICES:
        fn = s["slug"] + ".html"
        if fn not in [f.replace(os.sep, "/") for f in files]:
            continue
        txt = io.open(os.path.join(HERE, fn), encoding="utf-8").read()
        if 'href="areas/index.html' not in txt:
            problems.append(fn + ": does not link to the areas hub.")
        n = len(set(re.findall(r'href="blog/([a-z0-9-]+)\.html"', txt)))
        if n < MIN_POSTS_PER_SERVICE:
            problems.append(fn + ": links to " + str(n) + " blog post(s). Every service page "
                            "must link to at least " + str(MIN_POSTS_PER_SERVICE) +
                            ". See SERVICE_POSTS in build.py.")

    for f in files:
        key = f.replace(os.sep, "/")
        if not key.startswith("blog/") or key == "blog/index.html":
            continue
        txt = io.open(os.path.join(HERE, f), encoding="utf-8").read()
        prose = txt.split('class="wrap narrow prose"', 1)[-1]
        hits = set(re.findall(r'href="\.\./([a-z0-9-]+)\.html"', prose))
        if not (hits & set(SERVICE_BY_SLUG)):
            problems.append(key + ": does not link back to any service page. Every post needs a "
                            "`service_page` in its front matter.")

    return problems


# =============================================================================
# CITY PAGES: THE PLACE TABLE
# =============================================================================
# Programmatic location pages are the single easiest way to get a small site
# penalized. Google's spam policy names them directly: pages generated for many
# cities that differ only by the place name are doorway pages, and the action is
# taken against the whole site, not the folder. So the rule enforced below is
# not a style preference, it is the condition on which this section is allowed
# to exist at all.
#
#   Every city page must carry something TRUE and SPECIFIC to that place, and
#   the build must FAIL if two of them read the same.
#
# The honest differentiators for a painting contractor are the age and the shape
# of the housing, because they change the actual job:
#
#   - median year built, which decides whether the walls are plaster or drywall
#     and how many coats of old paint are already on the trim
#   - share built before 1980, which is the closest published proxy for the
#     pre-1978 stock the federal lead-safe renovation rule covers
#   - the split between detached houses, attached townhomes and buildings of two
#     or more units, which decides whether the work is homeowner work, board and
#     association work, or unit turnover
#   - median rooms, which is a better proxy for interior trim footage than
#     square feet, and interior trim footage is what actually makes an interior
#     job long
#   - straight-line distance from the Bridgeview shop, which is the honest
#     answer to "do you even come out here"
#
# All of it is real, published, and cited on the page. Where the data does not
# exist it is not invented. See launch/12-CITY-PAGE-DATA.md sections 6 and 7 for
# the full research file, the may-say and may-not-say table on the lead-safe
# rule, and the list of things the Census does NOT collect.
#
# WHAT THE CENSUS DOES NOT COLLECT: exterior wall material. There is no brick
# versus frame variable in ACS and none in the CMAP community-area data either.
# Every sentence below that describes construction type is inference from era
# and structure mix, it is labeled as inference on the page, and no percentage
# is ever attached to it. Do not "improve" that by attaching a number.

# ---- SOURCES ---------------------------------------------------------------
# Suburbs and towns: U.S. Census Bureau, American Community Survey 5-year
# estimates 2019-2023, tables B01003, B25003, B25018, B25024, B25034, B25035 and
# B25077, pulled from the Census API on 2026-08-31. Distances are straight-line
# from the shop, computed from the 2023 Gazetteer place centroids.
#
# Chicago community areas: CMAP Community Data Snapshots 2026, whose underlying
# source is ACS 2024. Community areas are used INSTEAD of ZIP code tabulation
# areas because ZIPs do not respect neighborhood lines: 60629 alone covers West
# Lawn, Chicago Lawn and Gage Park, so three ZIP-based pages would have shipped
# with three identical sets of numbers. That is the doorway failure mode
# arriving through the back door of a data choice.
#
# The community-area year-built buckets are coarser than the ACS place buckets.
# They stop at 1970, so a pre-1980 or pre-1978 share CANNOT be derived for a
# Chicago neighborhood. Interpolating one would be inventing a number. The
# neighborhood pages therefore quote the pre-1970 share as a floor and say so.

CENSUS_CITE_PLACES = ("U.S. Census Bureau, American Community Survey 5-year estimates, "
                      "2019-2023 (tables B25003, B25024, B25034, B25035, B25077).")
CENSUS_CITE_CCA = ("Chicago Metropolitan Agency for Planning, Community Data Snapshots 2026, "
                   "drawing on American Community Survey 2024 estimates.")

# The one sentence that keeps a Census median home value from reading as a price
# for work. audit() requires it on every page under areas/ that shows a dollar
# figure, so removing it fails the build rather than quietly shipping a page
# where a $300,000 median sits next to a phone number.
CENSUS_MARK = ("Every dollar figure on this page is a published Census estimate of what homes "
               "in the area are worth. None of it is a price for work.")

# ---- THE GATE --------------------------------------------------------------
# The west and near-west suburbs were researched in full and are in the table
# below with status GATE-WEST. They are NOT generated, and the flag is off on
# purpose.
#
# Mike confirmed Chicago plus the south and southwest suburbs on 2026-08-31. He
# did not confirm the west suburbs and said he does not work them. Generating a
# page that says "painting in Oak Park" is a coverage claim, and a coverage
# claim the owner has not made is exactly the class of thing this build does not
# ship, the same rule that keeps roofing off the site.
#
# Berwyn, Cicero, Riverside, Brookfield, La Grange and Oak Park are the ones
# worth asking him about: close in, old stock, and the strongest lead-safe angle
# on the entire researched list. Flipping this to True generates all 33.
INCLUDE_WEST_SUBURBS = False

# Joliet is band D, 23.4 straight-line miles, and the second largest owner
# market in the whole research file at 37,015 owner households. Size says build
# it, distance says do not. That is an owner decision and not a build decision.
INCLUDE_FLAG_SIZE_FAR = False

# slug|name|status|band|county|mi|lat|lon|pop|own|rent|own_pct|medval|medyr|era|
# hu|pre1980|pre1970|pre1940|sfd|sfa|multi|mobile|rooms|rrp
PLACE_TOWNS = """
justice|Justice|LIVE|A|Cook|1.4|41.7534|-87.8269|12372|2475|2329|51.5|235200|1976|70s-early-80s|5203|63.4|30.9|1.3|36.4|11.5|49.1|3.0|4.8|MAJORITY
hickory-hills|Hickory Hills|LIVE|A|Cook|1.5|41.7248|-87.8280|14718|4025|1585|71.7|278400|1970|60s-early-70s|5761|71.4|50.1|2.8|59.6|5.6|33.8|1.1|5.5|MAJORITY
burbank|Burbank|LIVE|A|Cook|2.0|41.7444|-87.7685|28822|7761|1913|80.2|258900|1965|60s-early-70s|10012|76.9|62.3|2.1|80.1|1.5|17.9|0.5|5.9|HIGH
bedford-park|Bedford Park|LIVE|A|Cook|2.6|41.7678|-87.7726|594|161|35|82.1|266800|1947|postwar-50s|200|92.0|92.0|42.0|98.0|0.0|2.0|0.0|6.1|HIGH
chicago-ridge|Chicago Ridge|LIVE|A|Cook|2.9|41.7034|-87.7795|14147|2918|2391|55.0|217800|1973|70s-early-80s|5840|64.0|44.8|1.1|33.8|2.3|63.5|0.5|4.8|MAJORITY
palos-hills|Palos Hills|LIVE|A|Cook|2.9|41.7007|-87.8253|18139|5831|1496|79.6|259200|1977|70s-early-80s|7885|63.3|19.8|0.2|42.4|11.8|45.8|0.0|5.3|MAJORITY
summit|Summit|LIVE|A|Cook|3.3|41.7885|-87.8139|10896|2229|1388|61.6|224800|1958|postwar-50s|3934|87.6|73.6|21.1|53.7|4.0|41.9|0.5|5.1|HIGH
oak-lawn|Oak Lawn|LIVE|A|Cook|3.3|41.7139|-87.7528|57098|17940|3805|82.5|267900|1967|60s-early-70s|23115|78.3|58.4|3.3|67.6|1.8|29.8|0.8|5.9|HIGH
hodgkins|Hodgkins|GATE-WEST|A|Cook|3.4|41.7661|-87.8619|1766|572|78|88.0|39200|1994|late-80s-90s|702|21.2|12.8|3.4|19.4|0.0|6.1|74.5|4.4|LOW
worth|Worth|LIVE|A|Cook|3.7|41.6882|-87.7926|10731|2835|1517|65.1|220200|1967|60s-early-70s|4558|77.7|56.1|3.2|54.0|0.2|39.8|6.0|5.0|HIGH
hometown|Hometown|LIVE|A|Cook|3.9|41.7312|-87.7311|4244|1393|523|72.7|152000|1955|postwar-50s|1916|98.5|97.0|1.1|11.8|65.4|22.8|0.0|4.8|HIGH
willow-springs|Willow Springs|LIVE|A|Cook|4.0|41.7341|-87.8840|5871|2261|350|86.6|370900|1977|70s-early-80s|2654|55.5|37.2|9.9|62.5|17.4|19.7|0.4|6.2|MAJORITY
countryside|Countryside|GATE-WEST|A|Cook|4.2|41.7742|-87.8752|6294|1948|781|71.4|330700|1975|70s-early-80s|2939|65.2|37.5|2.9|43.2|2.5|45.0|9.3|5.4|MAJORITY
indian-head-park|Indian Head Park|GATE-WEST|B|Cook|5.1|41.7684|-87.8974|3992|1569|210|88.2|337700|1978|70s-early-80s|1838|58.9|17.7|2.0|31.0|31.1|37.1|0.8|6.1|MAJORITY
palos-heights|Palos Heights|LIVE|B|Cook|5.3|41.6634|-87.7960|11817|4280|215|95.2|350000|1976|70s-early-80s|4762|58.1|35.9|2.5|60.8|22.6|16.5|0.0|6.5|MAJORITY
palos-park|Palos Park|LIVE|B|Cook|5.3|41.6662|-87.8296|4832|1846|206|90.0|469900|1974|70s-early-80s|2208|57.3|44.3|10.4|70.4|15.1|14.4|0.0|7.0|MAJORITY
evergreen-park|Evergreen Park|LIVE|B|Cook|5.6|41.7213|-87.7013|19498|6109|1219|83.4|255700|1955|postwar-50s|7707|93.2|87.7|11.2|85.8|1.4|12.9|0.0|6.1|HIGH
la-grange|La Grange|GATE-WEST|B|Cook|5.8|41.8072|-87.8741|15999|4680|1133|80.5|582600|1951|postwar-50s|6111|80.4|73.5|37.6|67.8|2.2|29.7|0.3|6.9|HIGH
burr-ridge|Burr Ridge|GATE-WEST|B|DuPage|5.9|41.7479|-87.9201|11119|4295|254|94.4|694800|1989|late-80s-90s|4909|29.2|16.0|0.7|74.4|9.5|16.1|0.0|7.9|MIXED
alsip|Alsip|LIVE|B|Cook|6.0|41.6703|-87.7371|18650|5071|2709|65.2|208700|1974|70s-early-80s|8076|65.2|37.6|2.5|54.1|4.5|41.1|0.2|5.4|MAJORITY
brookfield|Brookfield|GATE-WEST|B|Cook|6.2|41.8251|-87.8475|19235|6078|1570|79.5|314000|1952|postwar-50s|8010|93.3|78.5|31.8|74.3|3.0|22.5|0.2|6.0|HIGH
riverside|Riverside|GATE-WEST|B|Cook|6.3|41.8310|-87.8159|9079|2998|536|84.8|460500|1938|prewar|3831|94.8|90.2|61.7|71.9|3.1|24.0|1.0|6.9|HIGH
western-springs|Western Springs|GATE-WEST|B|Cook|6.5|41.8023|-87.9006|13353|4274|201|95.5|691300|1960|60s-early-70s|4568|77.1|72.1|23.2|88.7|5.5|5.2|0.6|8.1|HIGH
merrionette-park|Merrionette Park|LIVE|B|Cook|6.8|41.6811|-87.7012|2144|786|213|78.7|152600|1961|60s-early-70s|1026|77.4|67.4|6.7|64.7|0.0|13.2|22.1|4.7|HIGH
la-grange-park|La Grange Park|GATE-WEST|B|Cook|7.1|41.8308|-87.8723|13227|3766|1273|74.7|427800|1956|postwar-50s|5439|88.5|81.4|14.3|67.9|1.3|30.7|0.1|5.9|HIGH
berwyn|Berwyn|GATE-WEST|B|Cook|7.2|41.8433|-87.7909|55888|12356|7866|61.1|286000|1938|prewar|21987|95.0|90.0|62.1|52.0|0.6|47.0|0.5|5.4|HIGH
willowbrook|Willowbrook|GATE-WEST|B|DuPage|7.2|41.7673|-87.9421|9138|2893|1017|74.0|367000|1980|70s-early-80s|4472|51.7|16.6|0.6|36.6|6.0|57.4|0.0|5.3|MAJORITY
crestwood|Crestwood|LIVE|B|Cook|7.4|41.6456|-87.7401|10622|3877|1143|77.2|187700|1975|70s-early-80s|5348|64.2|33.8|2.7|42.5|1.4|56.1|0.0|5.1|MAJORITY
north-riverside|North Riverside|GATE-WEST|B|Cook|7.4|41.8461|-87.8263|7495|1963|978|66.7|295100|1955|postwar-50s|3078|92.1|85.0|11.7|70.8|1.6|27.6|0.0|5.3|HIGH
hinsdale|Hinsdale|GATE-WEST|B|DuPage|7.5|41.8007|-87.9282|17155|5111|529|90.6|999100|1979|70s-early-80s|6156|50.7|41.8|16.0|83.0|7.8|9.0|0.3|10.0|MAJORITY
cicero|Cicero|GATE-WEST|B|Cook|7.6|41.8445|-87.7593|83223|13667|11364|54.6|236000|1938|prewar|26738|93.9|90.2|66.8|41.8|2.5|55.5|0.2|5.3|HIGH
robbins|Robbins|LIVE|B|Cook|8.4|41.6431|-87.7081|4956|1011|544|65.0|114200|1962|60s-early-70s|2016|72.8|65.0|4.8|70.6|6.0|23.4|0.0|5.7|MAJORITY
broadview|Broadview|GATE-WEST|B|Cook|8.5|41.8584|-87.8562|7898|1993|1122|64.0|240600|1954|postwar-50s|3223|92.6|78.2|19.5|60.0|1.6|37.9|0.5|4.7|HIGH
blue-island|Blue Island|LIVE|B|Cook|8.6|41.6576|-87.6811|23416|4250|4412|49.1|169800|1961|60s-early-70s|9340|71.9|59.8|26.7|44.1|3.8|47.6|4.5|5.1|MAJORITY
clarendon-hills|Clarendon Hills|GATE-WEST|B|DuPage|8.7|41.7984|-87.9572|8642|2748|565|82.9|595500|1981|70s-early-80s|3417|48.6|44.0|2.9|69.4|4.9|25.8|0.0|7.3|MIXED
westchester|Westchester|GATE-WEST|B|Cook|8.7|41.8492|-87.8906|16524|6473|611|91.4|297400|1957|postwar-50s|7376|87.8|80.3|6.0|83.4|7.7|8.7|0.2|5.9|HIGH
forest-park|Forest Park|GATE-WEST|B|Cook|8.9|41.8684|-87.8157|14000|3773|3262|53.6|293800|1949|postwar-50s|7777|87.6|72.5|47.6|29.5|6.2|63.7|0.2|4.9|HIGH
midlothian|Midlothian|LIVE|B|Cook|9.0|41.6254|-87.7242|14024|4503|1331|77.2|200300|1964|60s-early-70s|6045|79.9|61.4|11.0|75.8|1.8|22.4|0.0|5.7|HIGH
darien|Darien|GATE-WEST|B|DuPage|9.0|41.7457|-87.9815|21855|6933|1897|78.5|386400|1978|70s-early-80s|9101|56.1|25.0|1.4|60.8|15.6|23.2|0.4|6.6|MAJORITY
chicago|Chicago|LIVE|B|Cook|9.2|41.8370|-87.6849|2707648|522179|624368|45.5|315200|1952|postwar-50s|1268199|76.5|68.6|39.1|25.6|3.6|70.5|0.3|4.7|HIGH
westmont|Westmont|GATE-WEST|B|DuPage|9.3|41.7944|-87.9729|24201|5823|4776|54.9|369100|1976|70s-early-80s|11312|60.0|33.3|4.9|41.0|9.6|49.4|0.0|5.0|MAJORITY
orland-park|Orland Park|LIVE|B|Cook|9.5|41.6081|-87.8593|57961|20139|3214|86.2|349400|1988|late-80s-90s|24626|31.5|11.8|1.9|57.5|21.1|21.3|0.0|6.5|MIXED
oak-forest|Oak Forest|LIVE|B|Cook|9.6|41.6067|-87.7533|26888|8242|2115|79.6|247800|1975|70s-early-80s|10732|62.4|35.4|2.2|68.3|4.5|27.2|0.0|6.1|MAJORITY
maywood|Maywood|GATE-WEST|B|Cook|9.8|41.8798|-87.8442|23173|4434|2899|60.5|212600|1938|prewar|8385|91.6|85.8|58.3|65.0|1.3|33.4|0.2|5.6|HIGH
posen|Posen|LIVE|B|Cook|9.9|41.6291|-87.6858|5331|1172|464|71.6|172800|1960|60s-early-70s|1721|71.8|65.9|10.6|87.7|0.0|12.3|0.0|6.0|MAJORITY
oak-brook|Oak Brook|GATE-WEST|C|DuPage|10.1|41.8364|-87.9532|8028|2682|181|93.7|867900|1978|70s-early-80s|3151|57.4|23.4|0.4|84.1|6.1|9.5|0.3|8.4|MAJORITY
hillside|Hillside|GATE-WEST|C|Cook|10.1|41.8675|-87.9018|8133|2109|941|69.1|233800|1960|60s-early-70s|3097|85.4|76.3|3.0|66.1|0.0|33.9|0.0|5.2|HIGH
oak-park|Oak Park|GATE-WEST|C|Cook|10.2|41.8872|-87.7899|53315|14128|9139|60.7|456300|1938|prewar|24673|86.6|78.6|59.1|40.0|3.6|56.4|0.0|5.4|HIGH
dixmoor|Dixmoor|LIVE|C|Cook|10.3|41.6330|-87.6672|2962|587|332|63.9|75500|1972|60s-early-70s|1188|77.8|43.1|5.9|48.3|0.0|5.8|45.9|5.4|HIGH
lemont|Lemont|LIVE|C|Cook|10.4|41.6672|-87.9820|17643|5524|810|87.2|447800|1994|late-80s-90s|6513|25.3|17.9|9.1|76.2|12.6|11.2|0.0|7.3|MIXED
orland-hills|Orland Hills|LIVE|C|Cook|10.5|41.5907|-87.8421|6758|1806|547|76.8|262600|1984|70s-early-80s|2409|38.6|13.0|2.7|77.2|1.4|21.4|0.0|6.1|MIXED
bellwood|Bellwood|GATE-WEST|C|Cook|10.5|41.8829|-87.8762|18373|4862|1241|79.7|219600|1955|postwar-50s|6475|91.1|88.3|17.7|73.9|5.0|20.3|0.8|5.6|HIGH
river-forest|River Forest|GATE-WEST|C|Cook|10.7|41.8949|-87.8191|11489|3806|469|89.0|676900|1945|prewar|4494|87.7|77.2|44.3|60.8|5.5|33.7|0.0|7.1|HIGH
riverdale|Riverdale|LIVE|C|Cook|11.1|41.6427|-87.6356|10515|2053|1819|53.0|104800|1957|postwar-50s|5225|88.8|76.6|15.4|54.3|8.2|35.9|1.7|5.0|HIGH
markham|Markham|LIVE|C|Cook|11.4|41.6000|-87.6905|11434|2701|1052|72.0|119500|1963|60s-early-70s|4257|82.3|65.6|8.1|95.0|2.9|2.1|0.0|6.0|HIGH
melrose-park|Melrose Park|GATE-WEST|C|Cook|11.6|41.9030|-87.8636|24513|4768|3553|57.3|265000|1957|postwar-50s|8947|79.5|70.6|25.2|42.6|3.3|47.2|6.9|5.1|HIGH
berkeley|Berkeley|GATE-WEST|C|Cook|11.6|41.8891|-87.9115|5222|1677|320|84.0|222400|1955|postwar-50s|2056|97.4|82.3|16.8|85.4|0.8|13.8|0.0|5.7|HIGH
downers-grove|Downers Grove|GATE-WEST|C|DuPage|11.7|41.7950|-88.0211|49867|15329|5028|75.3|439000|1974|70s-early-80s|21268|63.9|41.3|8.9|63.1|6.3|30.0|0.7|6.5|MAJORITY
tinley-park|Tinley Park|LIVE|C|Cook|11.9|41.5686|-87.8042|55007|19302|2756|87.5|289000|1987|late-80s-90s|22881|37.4|17.2|1.7|55.8|21.8|22.4|0.0|6.1|MIXED
homer-glen|Homer Glen|LIVE|C|Will|12.0|41.6052|-87.9524|24516|7480|521|93.5|400000|1988|late-80s-90s|8314|30.3|9.1|1.3|89.8|4.5|5.5|0.2|7.7|MIXED
harvey|Harvey|LIVE|C|Cook|12.2|41.6076|-87.6520|19831|3953|3192|55.3|86100|1960|60s-early-70s|9381|84.6|70.1|21.7|63.7|2.7|27.3|6.3|5.3|HIGH
woodridge|Woodridge|GATE-WEST|C|DuPage|12.2|41.7374|-88.0441|33889|8598|4521|65.5|345200|1980|70s-early-80s|13663|49.1|20.9|0.8|50.0|5.6|44.0|0.4|5.7|MIXED
country-club-hills|Country Club Hills|LIVE|C|Cook|12.9|41.5635|-87.7254|16419|4106|1247|76.7|180600|1976|70s-early-80s|5696|61.4|33.2|2.6|71.7|16.9|11.4|0.0|6.5|MAJORITY
elmhurst|Elmhurst|GATE-WEST|C|DuPage|12.9|41.8970|-87.9437|45538|13445|3418|79.7|532800|1964|60s-early-70s|17732|65.6|56.6|15.0|72.9|4.0|23.2|0.0|6.5|MAJORITY
hazel-crest|Hazel Crest|LIVE|C|Cook|13.0|41.5742|-87.6893|13493|3282|1389|70.3|181400|1970|60s-early-70s|5459|76.4|50.5|6.9|79.0|6.3|14.7|0.0|6.3|HIGH
dolton|Dolton|LIVE|C|Cook|13.2|41.6303|-87.5968|20979|5700|2219|72.0|140500|1965|60s-early-70s|9035|86.4|62.0|3.5|79.7|1.4|18.7|0.2|5.8|HIGH
villa-park|Villa Park|GATE-WEST|C|DuPage|13.4|41.8856|-87.9782|22456|6142|2261|73.1|313100|1958|postwar-50s|8841|87.0|76.0|20.2|75.0|1.8|23.3|0.0|5.8|HIGH
lombard|Lombard|GATE-WEST|C|DuPage|14.2|41.8738|-88.0155|43722|12223|5131|70.4|321200|1971|60s-early-70s|18495|67.5|48.6|8.4|54.8|6.4|38.7|0.1|5.5|MAJORITY
south-holland|South Holland|LIVE|C|Cook|14.4|41.5984|-87.6027|21016|6228|1270|83.1|201200|1967|60s-early-70s|7892|86.2|61.6|4.7|95.4|2.5|2.0|0.1|6.9|HIGH
homewood|Homewood|LIVE|C|Cook|14.6|41.5594|-87.6620|19471|5593|1449|79.4|210500|1962|60s-early-70s|7394|89.3|66.5|11.3|78.7|0.8|20.0|0.5|6.5|HIGH
mokena|Mokena|LIVE|C|Will|15.0|41.5299|-87.8777|19906|6554|673|90.7|377100|1996|late-80s-90s|7459|21.1|11.2|1.7|72.6|16.2|10.8|0.3|7.0|LOW
thornton|Thornton|LIVE|C|Cook|15.0|41.5741|-87.6193|1876|642|148|81.3|146600|1957|postwar-50s|849|90.3|82.8|21.0|85.2|0.5|14.4|0.0|5.5|HIGH
flossmoor|Flossmoor|LIVE|C|Cook|15.2|41.5391|-87.6857|9666|3473|150|95.9|309100|1967|60s-early-70s|3809|69.2|56.5|8.1|84.7|3.6|11.7|0.0|7.9|MAJORITY
lockport|Lockport|LIVE|C|Will|15.5|41.5910|-88.0297|26228|8087|1583|83.6|298800|1998|late-80s-90s|10046|31.0|25.9|11.7|66.4|20.0|13.6|0.0|6.7|MIXED
bolingbrook|Bolingbrook|LIVE|C|Will|15.6|41.6881|-88.1010|73813|18779|4987|79.0|295500|1989|late-80s-90s|24273|41.3|12.3|1.6|72.5|14.6|12.8|0.0|6.8|MIXED
olympia-fields|Olympia Fields|LIVE|D|Cook|16.2|41.5220|-87.6916|4636|1559|255|85.9|289900|1979|70s-early-80s|2013|51.0|36.1|0.0|82.7|7.7|9.6|0.0|7.7|MAJORITY
matteson|Matteson|LIVE|D|Cook|16.3|41.5089|-87.7460|18681|5747|1719|77.0|251400|1996|late-80s-90s|7737|30.9|15.7|3.1|67.5|9.7|18.0|4.8|6.5|MIXED
frankfort|Frankfort|LIVE|D|Will|16.5|41.5070|-87.8710|20417|6244|346|94.7|461600|2000|2000s-plus|6922|23.9|10.7|4.2|81.7|13.9|4.2|0.2|8.1|LOW
calumet-city|Calumet City|LIVE|D|Cook|17.0|41.5965|-87.5386|35253|8199|6479|55.9|133600|1968|60s-early-70s|16868|82.1|54.8|11.9|52.9|4.0|39.0|3.8|5.2|HIGH
romeoville|Romeoville|LIVE|D|Will|17.1|41.6279|-88.1012|40996|10748|2316|82.3|245200|1998|late-80s-90s|13662|28.1|20.6|1.1|69.2|16.9|13.8|0.0|6.0|MIXED
glenwood|Glenwood|LIVE|D|Cook|17.1|41.5410|-87.6118|8620|2368|672|77.9|182900|1968|60s-early-70s|3443|93.4|57.6|3.4|81.7|0.5|17.8|0.0|6.4|HIGH
new-lenox|New Lenox|LIVE|D|Will|18.0|41.5100|-87.9700|27456|8334|808|91.2|377500|1997|late-80s-90s|9473|19.8|7.9|2.3|81.0|10.5|8.4|0.1|7.1|LOW
lansing|Lansing|LIVE|D|Cook|18.1|41.5650|-87.5460|28415|7784|3370|69.8|168500|1966|60s-early-70s|12081|85.9|58.5|9.6|71.5|2.4|24.7|1.4|5.9|HIGH
chicago-heights|Chicago Heights|LIVE|D|Cook|18.2|41.5107|-87.6347|26938|5816|3393|63.2|149900|1958|postwar-50s|10799|86.1|74.3|15.6|69.2|3.0|27.1|0.3|5.7|HIGH
richton-park|Richton Park|LIVE|D|Cook|18.3|41.4802|-87.7425|12576|2620|2546|50.7|200400|1978|70s-early-80s|5427|59.1|21.4|1.8|54.4|8.0|37.6|0.0|5.5|MAJORITY
park-forest|Park Forest|LIVE|D|Cook|18.9|41.4817|-87.6868|20898|5296|2917|64.5|106200|1958|postwar-50s|9015|90.2|80.3|1.8|61.9|25.8|12.3|0.0|5.8|HIGH
joliet|Joliet|FLAG-SIZE-FAR|D|Will|23.4|41.5177|-88.1488|149785|37015|13633|73.1|248600|1986|late-80s-90s|53636|46.8|39.0|15.4|69.9|9.3|20.1|0.6|5.9|MIXED
bridgeview|Bridgeview|LIVE|A|Cook|0.0|41.7403|-87.8066|16721|4079|2146|65.5|234000|1975|70s-early-80s|6818|56.2|43.1|5.3|49.8|4.7|29.3|16.1|5.1|MAJORITY
"""

# slug|name|band|mi|lat|lon|pop|own|rent|own_pct|medval|medyr|era|hu|pre1970|
# pre1940|b1970_1990|sfd|sfa|multi|rooms
PLACE_NBHD = """
clearing|Clearing|A|3.2|41.7791|-87.7736|23629|6618|2405|73.3|303890|1960|60s-early-70s|9412|73.0|9.5|15.2|57.4|8.0|34.1|5.8
garfield-ridge|Garfield Ridge|A|4.6|41.8001|-87.7680|36732|10548|2109|83.3|293427|1957|postwar-50s|13108|81.0|11.6|12.5|81.6|3.2|14.9|6.1
west-lawn|West Lawn|A|4.7|41.7708|-87.7249|31942|7225|2262|76.2|259593|1954|postwar-50s|9758|82.3|20.8|10.3|70.2|2.2|26.9|6.1
ashburn|Ashburn|B|5.1|41.7447|-87.7079|42007|10967|2047|84.3|251766|1956|postwar-50s|13421|86.8|6.4|8.6|87.5|1.2|11.2|6.6
west-elsdon|West Elsdon|B|5.6|41.7930|-87.7239|17901|3996|1580|71.7|254623|1956|postwar-50s|5779|82.5|10.6|11.1|67.8|2.9|28.4|6.0
mount-greenwood|Mount Greenwood|B|5.7|41.6960|-87.7131|19059|6280|1139|84.6|317380|1955|postwar-50s|7629|77.0|9.9|12.4|84.1|1.6|12.6|6.6
chicago-lawn|Chicago Lawn|B|5.9|41.7727|-87.7000|54409|9369|8224|53.3|224494|1951|postwar-50s|19137|75.4|38.6|13.6|44.6|2.1|52.9|5.8
archer-heights|Archer Heights|B|6.3|41.8090|-87.7260|13414|2901|1606|64.4|280513|1951|postwar-50s|4795|86.9|37.1|6.2|48.6|1.7|49.8|5.4
beverly|Beverly|B|6.8|41.7126|-87.6798|19521|6220|1146|84.4|385581|1941|prewar|8074|91.8|47.6|5.1|77.8|1.8|20.2|7.4
gage-park|Gage Park|B|6.8|41.7953|-87.6977|36081|6142|4393|58.3|236361|1938|prewar|11186|84.4|52.0|9.0|46.1|2.0|50.2|5.5
auburn-gresham|Auburn Gresham|B|7.8|41.7430|-87.6550|43779|8722|8718|50.0|196978|1949|postwar-50s|20195|78.7|38.9|12.6|43.0|2.8|54.2|6.0
brighton-park|Brighton Park|B|7.8|41.8182|-87.6972|42994|7645|5919|56.4|248048|1935|prewar|14497|81.7|55.0|11.4|29.1|2.2|68.2|5.6
morgan-park|Morgan Park|B|8.0|41.6882|-87.6684|20873|6047|2430|71.3|247659|1953|postwar-50s|8987|83.4|28.2|6.8|75.0|4.6|20.4|6.6
washington-heights|Washington Heights|B|8.2|41.7195|-87.6497|24851|6945|2555|73.1|183936|1953|postwar-50s|10458|82.2|24.8|8.5|74.4|1.5|24.0|6.5
englewood|Englewood|B|8.8|41.7754|-87.6418|23195|3076|6432|32.4|152926|1942|prewar|12648|72.6|47.3|13.7|26.6|3.1|70.2|5.8
new-city|New City|B|8.9|41.8082|-87.6602|40065|5434|8394|39.3|228026|1932|prewar|15890|78.2|59.3|7.8|27.0|1.9|69.1|5.5
mckinley-park|McKinley Park|B|9.2|41.8288|-87.6742|14854|3989|1697|70.2|303496|1930|prewar|6249|77.9|62.8|6.2|37.3|6.2|56.3|5.9
roseland|Roseland|B|9.7|41.7104|-87.6232|36635|7635|6363|54.5|176214|1949|postwar-50s|17092|86.7|33.0|7.2|58.1|8.0|33.7|6.3
bridgeport|Bridgeport|C|10.6|41.8359|-87.6455|33638|7106|7007|50.4|426634|1939|prewar|15035|66.0|51.2|11.5|29.2|5.9|64.7|5.6
pullman|Pullman|C|11.0|41.7048|-87.5984|6744|1764|1318|57.2|169056|1948|postwar-50s|3746|86.5|42.7|12.2|33.7|43.6|22.7|5.9
hyde-park|Hyde Park|C|12.0|41.7941|-87.5845|30599|5182|9845|34.5|361433|1939|prewar|16523|74.4|51.5|11.3|4.9|10.1|84.7|4.5
south-shore|South Shore|C|12.8|41.7630|-87.5593|53588|6822|19648|25.8|214728|1944|prewar|30761|81.3|46.1|12.2|13.1|2.0|84.7|5.1
"""


def _f(x):
    return None if x in ("", "None") else float(x)


def _i(x):
    return None if x in ("", "None") else int(float(x))


def load_places():
    """Parse both tables into one list of dicts.

    `kind` is what stops the two geographies being confused later. A Chicago
    community area is not a municipality, its data comes from a different
    publisher with different buckets, and it must never be typed as a City in
    structured data or described with a figure the community-area table does not
    contain.
    """
    out = []
    for line in PLACE_TOWNS.strip().split("\n"):
        c = line.split("|")
        out.append(dict(
            kind="town", slug=c[0], name=c[1], status=c[2], band=c[3], county=c[4],
            mi=_f(c[5]), lat=_f(c[6]), lon=_f(c[7]), pop=_i(c[8]), own=_i(c[9]),
            rent=_i(c[10]), own_pct=_f(c[11]), medval=_i(c[12]), medyr=_i(c[13]),
            era=c[14], hu=_i(c[15]), pre1980=_f(c[16]), pre1970=_f(c[17]),
            pre1940=_f(c[18]), sfd=_f(c[19]), sfa=_f(c[20]), multi=_f(c[21]),
            mobile=_f(c[22]), rooms=_f(c[23]), rrp=c[24]))
    for line in PLACE_NBHD.strip().split("\n"):
        c = line.split("|")
        p = dict(
            kind="nbhd", slug=c[0], name=c[1], status="LIVE", band=c[2], county="Cook",
            mi=_f(c[3]), lat=_f(c[4]), lon=_f(c[5]), pop=_i(c[6]), own=_i(c[7]),
            rent=_i(c[8]), own_pct=_f(c[9]), medval=_i(c[10]), medyr=_i(c[11]),
            era=c[12], hu=_i(c[13]), pre1970=_f(c[14]), pre1940=_f(c[15]),
            b7090=_f(c[16]), sfd=_f(c[17]), sfa=_f(c[18]), multi=_f(c[19]),
            rooms=_f(c[20]), pre1980=None, mobile=None)
        # The community-area buckets stop at 1970, so the pre-1978 share is not
        # derivable. Grade the lead-safe exposure off the pre-1970 floor only,
        # and the page says "before 1970" everywhere, never "before 1978".
        p["rrp"] = "HIGH" if p["pre1970"] >= 70 else ("MAJORITY" if p["pre1970"] >= 50 else "MIXED")
        out.append(p)
    return out


PLACES = load_places()
PLACE_BY_SLUG = dict((p["slug"], p) for p in PLACES)


def built_places():
    """The places that actually get a page, in a stable order.

    Ordering is by straight-line distance from the shop. That is not cosmetic:
    the hub groups by distance band and the footer takes the close ring off the
    front of this list, so the geography has to sort itself rather than being
    maintained by hand in three places.
    """
    keep = []
    for p in PLACES:
        if p["status"] == "LIVE":
            keep.append(p)
        elif p["status"] == "GATE-WEST" and INCLUDE_WEST_SUBURBS:
            keep.append(p)
        elif p["status"] == "FLAG-SIZE-FAR" and INCLUDE_FLAG_SIZE_FAR:
            keep.append(p)
    return sorted(keep, key=lambda x: (x["mi"], x["name"]))


# ---- THE HOME TOWN ----------------------------------------------------------
# launch/08-SEO-AND-KEYWORD-RESEARCH.md rule 13.2.1, rewritten 2026-08-31.
#
# The OLD rule said the home page IS the Bridgeview page: it carried "House
# Painters in Bridgeview, IL", so areas/bridgeview.html had to be pushed off the
# head term onto a housing-data long tail to avoid two pages competing for it.
#
# That was solving the wrong problem. Bridgeview is a village of 16,721 people
# and it was the scope of the entire site while 76 city pages underneath it
# covered all of Chicagoland. The home page and the service pages now carry the
# REGIONAL head terms, which is where the volume is, so nothing on this site is
# chasing "house painters Bridgeview" any more except the Bridgeview city page.
#
# The conflict is therefore gone and the special case with it. areas/bridgeview
# .html is a normal city page: normal title pattern, normal h1, normal anchor
# text, exactly like the other 75. The slug is still named here because two
# things genuinely differ for the town the shop sits in: the distance is 0.0
# miles, which makes the generic "X miles from the Bridgeview shop" fragment
# nonsense in a meta description, and the page can say something no other page
# on the site can say, which is that this is where the shop actually is.
HOME_TOWN_SLUG = "bridgeview"


def home_town_desc(p):
    """Meta description for the town the shop is in.

    Same shape as every other city page, minus the distance fragment, which
    would read "0.0 miles from the Bridgeview shop" on the Bridgeview page.
    Length-checked at build time by seo_audit(): DESC_MIN/MAX 140 to 160, and
    assembled from the row rather than typed so it cannot drift from the table.
    """
    return ("Interior and exterior painting in Bridgeview, IL, where our shop is. Median build "
            "year " + str(p["medyr"]) + ", " + _pc(p["pre1980"]) + "% built before 1980, " +
            _n(p["own"]) + " owner households. Call " + PHONE_DISPLAY + ".")


def city_anchor(q):
    """Anchor text for an internal link to a city page.

    The place name, on every page including Bridgeview. This used to rename the
    Bridgeview link to "Bridgeview housing data" so it would stop competing with
    the home page for the head term. The home page is regional now, so the town
    link says the town name like all 75 others.
    """
    return q["name"]


# ---- REGION GROUPS ----------------------------------------------------------
# The hub groups by distance band, with Chicago and its community areas pulled
# out into their own group. Distance is the only grouping a visitor can check
# against their own address, and it is the same fact the travel section on each
# page is built from.
REGIONS = [
    ("close-ring", "Right around the shop, within five miles",
     "Our own neighborhood, ten or fifteen minutes away. Mostly houses from the 1950s "
     "through the 1970s, which means real wood trim and paint that has been on there a "
     "long time. Close enough that one room or one small repair is worth a trip on its "
     "own."),
    ("chicago", "Chicago, the south and southwest sides",
     "Our city work is the south and southwest sides. Bungalows, plaster walls, deep "
     "window casings and front porches. This is the oldest housing we paint and the most "
     "detailed. The pages below are neighborhoods rather than ZIP codes, because a ZIP "
     "code cuts straight through three neighborhoods that have nothing in common."),
    ("five-to-ten", "The near south and southwest suburbs, five to ten miles",
     "Twenty minutes or so. The near end of this ring is postwar bungalows and 1960s "
     "ranches, and the far end is late 1980s subdivisions. Very different houses, so the "
     "quotes come out looking very different too."),
    ("ten-to-sixteen", "Further out, ten to sixteen miles",
     "A real drive, and worth it for a whole interior or a full exterior. For one room or "
     "a patch, call and ask first rather than counting on it."),
    ("outer", "The outer edge, sixteen miles and beyond",
     "These towns are on the list because we do work out here, not because it is a short "
     "drive. Ask about scheduling before you plan anything around a date."),
]


def region_of(p):
    if p["kind"] == "nbhd" or p["slug"] == "chicago":
        return "chicago"
    if p["mi"] < 5:
        return "close-ring"
    if p["mi"] < 10:
        return "five-to-ten"
    if p["mi"] < 16:
        return "ten-to-sixteen"
    return "outer"


def places_in_region(key):
    return [p for p in built_places() if region_of(p) == key]


# =============================================================================
# CITY PAGES: DERIVED FACTS
# =============================================================================
# Everything below is computed from the table, never typed by hand. A hand-typed
# ranking goes stale the moment a town is added or the ACS vintage rolls, and a
# stale ranking on a live page is a false statement.

def _hav(a, b):
    """Great-circle miles between two places. Used for real adjacency.

    Nearby-town links have to be genuinely nearby. A random four-town link block
    is the tell that a set of location pages was generated rather than written,
    and it is also useless to the visitor.
    """
    r = 3958.8
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp = p2 - p1
    dl = math.radians(b["lon"] - a["lon"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


_NEIGHBOR_CACHE = {}


def neighbors(p, n=4):
    """The n nearest built places, excluding Chicago-the-whole-city.

    Chicago is excluded from adjacency because its centroid sits nowhere useful
    and "nearest place to Evergreen Park: Chicago" is true and worthless. The
    community areas carry the city adjacency properly.
    """
    key = (p["slug"], n)
    if key in _NEIGHBOR_CACHE:
        return _NEIGHBOR_CACHE[key]
    pool = [q for q in built_places() if q["slug"] not in (p["slug"], "chicago")]
    ranked = sorted(pool, key=lambda q: _hav(p, q))
    _NEIGHBOR_CACHE[key] = ranked[:n]
    return _NEIGHBOR_CACHE[key]


def scope_stats():
    """Averages and ranks across the places that are actually built.

    Computed over the built set rather than the full research table on purpose.
    A page that says "highest rental share of the 87 places we looked at" when
    only 76 are on the site is describing a document the reader cannot see.
    """
    b = built_places()
    towns = [p for p in b if p["kind"] == "town"]
    st = {"n": len(b), "n_towns": len(towns)}
    for f in ("own_pct", "sfd", "sfa", "multi", "rooms", "pre1940", "pre1970"):
        vals = [p[f] for p in b if p.get(f) is not None]
        st["avg_" + f] = sum(vals) / float(len(vals))
    vals = [p["pre1980"] for p in towns if p["pre1980"] is not None]
    st["avg_pre1980"] = sum(vals) / float(len(vals))
    return st


_SCOPE = None


def scope():
    global _SCOPE
    if _SCOPE is None:
        _SCOPE = scope_stats()
    return _SCOPE


def rank_of(p, field, biggest_first=True, same_kind=True):
    """1-based rank of a place on one field, within its own geography type.

    same_kind matters. Ranking a Chicago community area against a suburb on
    year-built share compares an ACS 2024 community-area estimate with an ACS
    2023 place estimate from a different publisher with different buckets. That
    is not a ranking, it is two different rulers held next to each other.
    """
    pool = [q for q in built_places()
            if q.get(field) is not None and (q["kind"] == p["kind"] or not same_kind)]
    pool.sort(key=lambda q: q[field], reverse=biggest_first)
    for i, q in enumerate(pool):
        if q["slug"] == p["slug"]:
            return i + 1, len(pool)
    return None, len(pool)


# ---- number and phrase helpers ---------------------------------------------

def _n(x):
    return format(int(x), ",")


def _pc(x):
    """A percentage as published. No rounding: the published estimate is the
    published estimate, and rounding it and then citing the table is a small
    lie that is very easy to write."""
    s = "%.1f" % float(x)
    return s[:-2] if s.endswith(".0") else s


def _money(x):
    return "$" + format(int(x), ",")


def in_ten(p):
    """A share said in words, so a page can state the same fact twice without
    reading like a spreadsheet. The digits are always given somewhere on the
    page as well: the words are the second reference, never the only one."""
    n = int(round(float(p) / 10.0))
    return {0: "almost none of it", 1: "about one home in ten", 2: "about two in ten",
            3: "about three in ten", 4: "about four in ten", 5: "about half",
            6: "about six in ten", 7: "about seven in ten", 8: "about eight in ten",
            9: "about nine in ten", 10: "very nearly all of it"}[max(0, min(10, n))]


def hnum(key, slot=""):
    """A stable number for one place and one slot on the page.

    Stable so the same town produces the same page on every build, and a diff
    shows real content changes rather than reshuffled prose.

    The SLOT is what makes this work and it was not obvious. The first version
    used one number per town and added a fixed offset per slot, which meant two
    towns whose numbers were congruent modulo the pool sizes drew the SAME
    variant in every slot at once, and produced two pages that read identically
    all the way down. Hashing the slot name in makes each slot an independent
    draw, so two towns colliding on the age paragraph almost never also collide
    on the trade paragraph, the headings and the section order.
    """
    return int(hashlib.md5((str(key) + "|" + str(slot)).encode("utf-8")).hexdigest()[:8], 16)


def pick(options, key, slot):
    return options[hnum(key, slot) % len(options)]


def _an(name):
    """"a" or "an" in front of a place name.

    Needed because the generated prose says things like "a Justice house", and
    the same template produced "a Orland Park quote". A vowel test is enough for
    every name in the table: none of them start with a silent H or with a vowel
    that sounds like a consonant.
    """
    return "an" if name[:1].upper() in "AEIOU" else "a"


def _join(items):
    """Oxford-free list join. Used everywhere a computed set of facts becomes a
    sentence, so the generated prose reads like a sentence rather than a row."""
    items = list(items)
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


# ---- inference, labeled as inference ---------------------------------------
# ERA_NOTE and structure_note() are the only two places on a city page that
# describe construction rather than report a measurement. Both are rendered
# inside a block that says so. The Census does not collect wall material and
# neither does CMAP, so there is no version of this that is a citation.

ERA_LABEL = {
    "prewar": "prewar",
    "postwar-50s": "postwar, 1940s and 1950s",
    "60s-early-70s": "1960s and early 1970s",
    "70s-early-80s": "1970s and early 1980s",
    "late-80s-90s": "late 1980s and 1990s",
    "2000s-plus": "2000s and later",
}


def structure_note(p):
    """What the housing here is most likely made of and shaped like.

    Inference from era plus structure mix. Never a percentage, never a citation.
    Two readings per branch, drawn on the slug, and each one names the place in
    the middle of it. Both of those are anti-duplication measures with a reason:
    this paragraph plus the trade paragraph after it was the longest identical
    run between two pages that the doorway audit found, precisely because it was
    sixty words that never mentioned where it was talking about.
    """
    era, sfd, multi, sfa = p["era"], p["sfd"], p["multi"], p["sfa"]
    n = p["name"]
    alt = hnum(p["slug"], "structure-alt") % 2
    if era == "prewar":
        if multi >= 55:
            return ("prewar masonry, and mostly two-flats, three-flats and courtyard "
                    "buildings rather than single houses. Walls are brick, so exterior paint "
                    "in " + n + " means porches, stairs, cornice, soffit and window trim, "
                    "over interiors of plaster and deep original casing")
        if alt:
            return ("prewar brick and frame: bungalows, cottages and the larger houses that "
                    "went up on the better streets before the war. The paintable surface "
                    "outside is porch, cornice, soffit and sash rather than wall. Inside " +
                    n + " it is plaster and original millwork")
        return ("prewar brick: bungalows, workers' cottages and larger frame and stucco "
                "houses on the older streets. Masonry walls put the exterior work in porch, "
                "cornice, soffit and sash. Interiors in " + n + " are plaster with original "
                "millwork carrying a lot of coats")
    if era == "postwar-50s":
        if multi >= 45:
            return ("postwar masonry with a heavy share of two-flats and small apartment "
                    "buildings. Trim, soffit, porches and common areas are where the exterior "
                    "paint in " + n + " actually is, and unit turnover sits alongside "
                    "homeowner work")
        if alt:
            return ("postwar brick: bungalow, Cape Cod and the first generation of ranch. "
                    "Little of the outside takes paint at all, so " + _an(n) + " " + n + " exterior is "
                    "soffit, fascia, overhangs, doors and the garage. Inside it is small "
                    "rooms with a great deal of casing in them")
        return ("brick bungalow, Cape Cod and early ranch. The walls are masonry, so exterior "
                "paint concentrates in trim, soffit, fascia, garage surround and doors. " +
                n + " interiors are trim-heavy for their square footage")
    if era == "60s-early-70s":
        if multi >= 45:
            return ("1960s brick and brick-and-frame, with a large share of it in buildings "
                    "of two units or more. Association and landlord work is as much of the " +
                    n + " market as single-house work")
        if alt:
            return ("ranch, raised ranch and split-level, usually masonry to the sill line "
                    "with frame gables above. Almost all the exterior paint in " + n + " sits "
                    "above head height, which is why the work takes longer than the surface "
                    "area suggests")
        return ("brick and brick-and-frame ranch and split-level. Exterior work in " + n +
                " is fascia, soffit, gable ends and window trim, most of it off a ladder "
                "rather than off the ground")
    if era == "70s-early-80s":
        if multi >= 40 or sfa >= 15:
            return ("1970s stock with a large share of townhomes and apartment units. "
                    "Association work, matching an existing scheme exactly and painting "
                    "several identical units in a row, is as much of the " + n + " market as "
                    "single-house work")
        if alt:
            return ("1970s tri-level, raised ranch and two story, brick fronted with frame or "
                    "board returns on the sides, and enough wood above the second floor line "
                    "to make access the deciding factor on " + _an(n) + " " + n + " exterior")
        return ("1970s ranch, raised ranch and split-level, usually brick or brick front with "
                "frame gables, and a lot of the exterior wood in " + n + " sitting high")
    if era == "late-80s-90s":
        if alt:
            return ("frame with a masonry front elevation and siding on the other three, "
                    "cedar or composite trim boards, and enough two story wall in " + n +
                    " that the ladder plan matters as much as the paint plan")
        return ("frame construction with vinyl or aluminum siding over a brick or stone "
                "front, and cedar or engineered trim well past its first repaint. " + n +
                " runs to long elevations and tall interior volumes")
    if alt:
        return ("recent construction: big footprints, two story entries, open sightlines, "
                "and factory millwork in " + n + " that has never had a brush near it")
    return ("recent construction: large elevations, two story entries, and factory-finished "
            "millwork in " + n + " that was specified once and never touched since")


# ---- the differentiating paragraph -----------------------------------------
# Every sentence here contains at least one number from that place's own row.
# That is what makes the text different rather than the town name.

def age_para(p, seed):
    """Paragraph one: how old the housing is, with the figure and the source."""
    F = dict(name=p["name"], an=_an(p["name"]), medyr=p["medyr"],
             pre1940=_pc(p["pre1940"]), pre1970=_pc(p["pre1970"]), hu=_n(p["hu"]),
             rooms=_pc(p["rooms"]))
    if p["kind"] == "town":
        F["pre1980"] = _pc(p["pre1980"])
        opts = [
            "The median home in {name} was built in {medyr}. Across the {hu} housing units "
            "here, {pre1980} percent went up before 1980 and {pre1940} percent date to 1939 "
            "or earlier. That single figure decides more about a paint job than anything "
            "else anyone will ask you on the phone.",
            "Housing here runs to a median build year of {medyr}, and {pre1980} percent of "
            "the {hu} units in {name} predate 1980. {pre1940} percent are prewar. Age is the "
            "first thing worth knowing about a house before it gets quoted, and it is the "
            "thing most quotes skip.",
            "{name} has {hu} housing units and a median build year of {medyr}. {pre1980} "
            "percent of them were built before 1980, {pre1970} percent before 1970 and "
            "{pre1940} percent before 1940. Those three numbers together describe the walls, "
            "the trim and the windows better than a photograph does.",
            "Take the {hu} housing units in {name} and {pre1980} percent of them are older "
            "than 1980, with a median build year of {medyr}. {pre1940} percent go back to "
            "1939 or earlier. On stock that age the prep is the job and the paint is the "
            "easy part.",
            "Build year is the first number worth having about {an} {name} house, and the town "
            "answer is {medyr}. Behind it: {pre1980} percent of the {hu} units here predate "
            "1980, {pre1970} percent predate 1970, {pre1940} percent predate 1940. Median "
            "size is {rooms} rooms.",
            "There are {hu} housing units in {name}. {pre1970} percent were finished before "
            "1970 and {pre1980} percent before 1980, against a median build year of {medyr} "
            "and a median size of {rooms} rooms. That combination is the whole brief for a "
            "quote here.",
        ]
    else:
        opts = [
            "The median building in {name} dates to {medyr}, and {pre1970} percent of its "
            "{hu} housing units were up before 1970. {pre1940} percent are prewar. The "
            "community-area figures bucket at 1970 rather than 1978, so treat {pre1970} "
            "percent as a floor on the pre-1978 share here, not a ceiling.",
            "{name} counts {hu} housing units with a median build year of {medyr}. {pre1970} "
            "percent predate 1970 and {pre1940} percent predate 1940. The published buckets "
            "stop at 1970, so the pre-1978 share is higher than {pre1970} percent by an "
            "amount nobody publishes and this page will not guess at.",
            "Of the {hu} housing units in {name}, {pre1970} percent were built before 1970 "
            "and {pre1940} percent before 1940, against a median build year of {medyr}. "
            "This is old-city housing, and it behaves like it: plaster, deep casing and a "
            "lot of coats already on the woodwork.",
            "{name} runs to a median build year of {medyr} across {hu} housing units, "
            "{pre1970} percent of which predate 1970. Prewar stock alone is {pre1940} "
            "percent. Nothing about that mix is a fast repaint.",
            "Age is the first thing worth knowing here and the answer is {medyr}, with "
            "{pre1970} percent of the {hu} units in {name} finished before 1970 and "
            "{pre1940} percent before 1940. Median size is {rooms} rooms, and rooms are "
            "what an interior quote is really counting.",
            "The community-area figures for {name} give a median build year of {medyr}, "
            "{pre1970} percent of housing built before 1970 and {pre1940} percent before "
            "1940 across {hu} units. Those buckets stop at 1970, so nothing on this page "
            "will claim a pre-1978 percentage the source does not publish.",
        ]
    return pick(opts, seed, 0).format(**F)


def tenure_para(p, seed):
    """Paragraph two: who lives here and in what, which decides what the work is."""
    F = dict(name=p["name"], own=_n(p["own"]), rent=_n(p["rent"]),
             own_pct=_pc(p["own_pct"]), sfd=_pc(p["sfd"]), sfa=_pc(p["sfa"]),
             multi=_pc(p["multi"]), rooms=_pc(p["rooms"]),
             val=_money(p["medval"]) if p["medval"] else "")
    opts = [
        "{own} households own their home in {name} and {rent} rent, which puts owner "
        "occupancy at {own_pct} percent. {sfd} percent of the housing is single-family "
        "detached, {sfa} percent is attached and {multi} percent sits in buildings of two "
        "units or more. Median size is {rooms} rooms.",
        "The tenure split is {own} owner households against {rent} renting, or {own_pct} "
        "percent owner occupied. Structure follows it: {sfd} percent detached houses, "
        "{sfa} percent townhomes and rowhouses, {multi} percent in buildings of two or "
        "more. At {rooms} rooms a unit, that is the trim footage an interior quote is "
        "really made of.",
        "{name} is {own_pct} percent owner occupied, {own} households against {rent} "
        "renting. {multi} percent of units are in buildings of two or more, {sfa} percent "
        "are attached, and the remaining {sfd} percent are detached houses averaging "
        "{rooms} rooms.",
        "Owner households here number {own} and renter households {rent}, a {own_pct} "
        "percent owner-occupied place. The stock behind those households is {sfd} percent "
        "detached, {sfa} percent attached and {multi} percent multi-unit, at a median of "
        "{rooms} rooms.",
        "Behind the housing are {own} owner households and {rent} renter households, "
        "{own_pct} percent owner occupied. Of the units themselves, {multi} percent are in "
        "buildings of two or more, {sfa} percent share a party wall as townhomes or "
        "rowhouses, and {sfd} percent stand on their own at a median {rooms} rooms.",
        "Count it by household and {name} is {own} owning against {rent} renting, {own_pct} "
        "percent owner occupied. Count it by building and it is {sfd} percent detached, "
        "{sfa} percent attached, {multi} percent in twos or more. Median unit: {rooms} "
        "rooms.",
    ]
    out = pick(opts, seed, 1).format(**F)
    if p["medval"]:
        vopts = [
            " Median home value is {val}.",
            " The Census puts the median home value at {val}.",
            " Median value across that stock is {val}.",
        ]
        out += pick(vopts, seed, 2).format(**F)
    return out


def outlier_sentences(p, seed):
    """The sentences that exist on exactly one page.

    Two kinds. RANKS, where this place is at or near the top or the bottom of the
    built set on something, and TRAPS, where a figure on this page would mislead
    if it were left to stand on its own.

    Ranks are collapsed into one or two sentences rather than emitted one per
    line. The first version wrote them out separately and produced three
    consecutive sentences all opening "Of the 22 Chicago community areas on this
    site", which reads like a spreadsheet with a comma key.

    Comparisons are always within one geography type. Ranking a Chicago
    community area against a suburb means comparing a 2024 community-area
    estimate from one publisher with a 2023 place estimate from another, on
    different year-built buckets. That is two rulers held next to each other, not
    a ranking.
    """
    out = []
    facts = []
    kindword = ("Chicago community areas covered here" if p["kind"] == "nbhd"
                else "suburbs and towns covered here")

    def rank(field, biggest, label, val):
        r, n = rank_of(p, field, biggest)
        if r and r <= 4:
            facts.append((r, n, label, val))

    rank("own", True, "the largest owner-occupied market", _n(p["own"]) + " households")
    rank("own", False, "the smallest owner-occupied market", _n(p["own"]) + " households")
    rank("own_pct", True, "the highest owner-occupied share", _pc(p["own_pct"]) + " percent")
    rank("own_pct", False, "the highest renter share",
         _pc(100.0 - p["own_pct"]) + " percent renting")
    rank("pre1940", True, "the largest prewar share", _pc(p["pre1940"]) + " percent")
    rank("multi", True, "the most housing in buildings of two or more",
         _pc(p["multi"]) + " percent")
    rank("sfd", True, "the highest detached-house share", _pc(p["sfd"]) + " percent")
    rank("sfa", True, "the largest townhome and rowhouse share", _pc(p["sfa"]) + " percent")
    rank("rooms", True, "the largest homes by room count", _pc(p["rooms"]) + " rooms")
    rank("rooms", False, "the smallest homes by room count", _pc(p["rooms"]) + " rooms")
    rank("hu", True, "the largest housing stock overall", _n(p["hu"]) + " units")
    rank("hu", False, "the smallest housing stock overall", _n(p["hu"]) + " units")
    rank("medyr", False, "the oldest housing by median build year", str(p["medyr"]))
    rank("medyr", True, "the newest housing by median build year", str(p["medyr"]))
    rank("pre1970", True, "the largest share built before 1970", _pc(p["pre1970"]) + " percent")
    rank("pre1970", False, "the smallest share built before 1970",
         _pc(p["pre1970"]) + " percent")
    if p["medval"]:
        rank("medval", True, "the highest median home value", _money(p["medval"]))
        rank("medval", False, "the lowest median home value", _money(p["medval"]))
    if p["kind"] == "town" and p["pre1980"] is not None:
        rank("pre1980", True, "the oldest housing stock overall",
             _pc(p["pre1980"]) + " percent built before 1980")
        rank("pre1980", False, "the newest housing stock overall",
             _pc(p["pre1980"]) + " percent built before 1980")

    facts.sort()
    if facts:
        n = facts[0][1]
        bits = [label + " (" + val + ")" if r > 1
                else label + " (" + val + ", first of them all)"
                for r, _, label, val in facts[:3]]
        out.append(pick([
            p["name"] + " is in the top four of the " + str(n) + " " + kindword + " for " +
            _join(bits) + ".",
            "Against the other " + str(n) + " " + kindword + ", " + p["name"] +
            " sits in the top four for " + _join(bits) + ".",
            "Ranked against the " + str(n) + " " + kindword + ", " + p["name"] +
            " lands in the top four on " + _join(bits) + ".",
        ], seed, "ranks"))
    if len(facts) > 3:
        bits2 = [label + " (" + val + ")" for r, _, label, val in facts[3:6]]
        out.append("It is also near the top for " + _join(bits2) + ".")

    # The traps. Not colour: corrections. Quoting a median value in Hodgkins or
    # Bridgeview without saying what the stock is would be quoting a number that
    # describes a different kind of building entirely.
    if p.get("mobile") and p["mobile"] >= 15:
        out.append("Manufactured housing is " + _pc(p["mobile"]) + " percent of the stock in " +
                   p["name"] + ", which is a different structure and a different job from a "
                   "site-built house. It is also why the median value here is not comparable "
                   "to the town next door.")
    if p["hu"] and p["hu"] < 1200:
        out.append("This is a very small market: " + _n(p["hu"]) + " housing units in total, "
                   "so every estimate on this page is a thin one and should be read as a "
                   "direction rather than a measurement.")
    if p["kind"] == "nbhd" and p["sfa"] and p["sfa"] >= 20:
        out.append("Attached housing is " + _pc(p["sfa"]) + " percent of " + p["name"] +
                   ", far more than anywhere else on the south side pages here, which makes "
                   "party-wall and shared-elevation work a normal part of the job.")
    return out


def divergence_sentences(p, seed):
    """The three figures on which this place is furthest from the service-area
    average, stated with both numbers.

    This exists because of a thin page. Robbins has 1,011 owner households, few
    rank positions and no traps, so it drew almost nothing from
    outlier_sentences() and the doorway audit correctly reported that half its
    body also appeared on the Midlothian page. Rank sentences only fire for
    places that are near the top or the bottom of something. This fires for every
    place, because every place is furthest from the mean on SOMETHING, and it
    prints two numbers per clause so the sentence cannot match another page's.
    """
    st = scope()
    fields = [
        ("own_pct", st["avg_own_pct"], "owner occupancy", "percent"),
        ("sfd", st["avg_sfd"], "detached houses", "percent"),
        ("sfa", st["avg_sfa"], "townhomes and rowhouses", "percent"),
        ("multi", st["avg_multi"], "housing in buildings of two or more", "percent"),
        ("rooms", st["avg_rooms"], "rooms per unit", "rooms"),
        ("pre1940", st["avg_pre1940"], "prewar housing", "percent"),
        ("pre1970", st["avg_pre1970"], "housing built before 1970", "percent"),
    ]
    scored = []
    for f, avg, label, unit in fields:
        v = p.get(f)
        if v is None or not avg:
            continue
        scored.append((abs(v - avg) / float(avg), f, avg, label, unit, v))
    scored.sort(reverse=True)
    bits = []
    for _, f, avg, label, unit, v in scored[:3]:
        word = "against" if v > avg else "against"
        bits.append(label + " at " + _pc(v) + " " + unit + " " + word + " a " + _pc(avg) +
                    " " + unit + " average")
    n = str(st["n"])
    return pick([
        "Set against the other places covered here, " + p["name"] + " is furthest from the "
        "middle on three things: " + _join(bits) + ".",
        "Three figures put " + p["name"] + " a long way from the average of the " + n +
        " places on this site: " + _join(bits) + ".",
        "Where " + p["name"] + " departs most from the " + n + " place average: " +
        _join(bits) + ".",
        "Compared with the " + n + " place average behind this site, " + p["name"] +
        " is unusual for " + _join(bits) + ".",
    ], seed, "divergence")


def contrast_para(p, seed):
    """{Place} against its nearest built neighbor, on whichever figures actually
    diverge. Unique by construction: it names a specific place and prints the
    specific numbers that differ."""
    nb = neighbors(p, 1)
    if not nb:
        return ""
    q = nb[0]
    fields = [("own", "owner households", _n),
              ("own_pct", "owner-occupied share", lambda v: _pc(v) + " percent"),
              ("medyr", "median build year", lambda v: str(int(v))),
              ("multi", "share of units in buildings of two or more",
               lambda v: _pc(v) + " percent"),
              ("sfd", "detached-house share", lambda v: _pc(v) + " percent"),
              ("pre1940", "prewar share", lambda v: _pc(v) + " percent"),
              ("rooms", "median rooms", _pc)]
    if p["medval"] and q["medval"]:
        fields.append(("medval", "median home value", _money))
    scored = []
    for f, label, fmt in fields:
        a, b = p.get(f), q.get(f)
        if a is None or b is None or not b:
            continue
        scored.append((abs(a - b) / float(max(abs(b), 1)), f, label, fmt, a, b))
    scored.sort(reverse=True)
    if not scored:
        return ""
    bits = ["" + label + " (" + fmt(a) + " against " + fmt(b) + ")"
            for _, f, label, fmt, a, b in scored[:3]]
    d = _hav(p, q)
    lead = pick([
        "{a} and {b} are {d} miles apart and are quoted differently, which is the whole "
        "argument for reading a page about your own town rather than a page about the "
        "region. They part company on ",
        "The nearest place on this site to {a} is {b}, {d} miles away. Same drive, "
        "different job. The figures that separate them are ",
        "{b} is {d} miles from {a} and is the closest comparison there is. It is not a "
        "close one. The two differ on ",
        "Put {a} next to {b}, {d} miles away, and the housing does not match. The gaps "
        "are ",
    ], seed, 3).format(a=p["name"], b=q["name"], d="%.1f" % d)
    return lead + "; ".join(bits) + "."


# ---- what it means for the work --------------------------------------------

def trade_para(p, seed):
    """The consequence paragraph. Era plus structure mix decides what the work
    actually is, and every branch says something a homeowner can check against
    their own house."""
    F = dict(name=p["name"], medyr=p["medyr"], rooms=_pc(p["rooms"]),
             multi=_pc(p["multi"]), sfd=_pc(p["sfd"]), sfa=_pc(p["sfa"]),
             own_pct=_pc(p["own_pct"]), pre1940=_pc(p["pre1940"]),
             rent=_n(p["rent"]), own=_n(p["own"]))
    era = p["era"]
    if era in ("prewar", "postwar-50s"):
        opts = [
            "On stock with a {medyr} median, the interior quote is decided by trim footage "
            "and not by wall area. {rooms} rooms is a lot of door casing, window casing and "
            "baseboard for the square footage, and every run of it is already carrying "
            "decades of paint. Original casing with sixty years on it prices very "
            "differently from casing that was stripped or replaced, which is the first "
            "thing worth establishing before anybody gives you a number.",
            "A {medyr} median build year means plaster as well as drywall, and the two do "
            "not take a repair the same way. Plaster cracks along the lath and comes back "
            "if it is only filled, so the honest version of a wall repair here is longer "
            "than a drywall patch and should read that way on the quote. With {rooms} rooms "
            "on the median unit, the trim is the other half of the job.",
            "Masonry walls change the exterior job completely. On {pre1940} percent prewar "
            "stock and a {medyr} median, there is very little painted wall outside: the "
            "work is the porch, the cornice, the soffit, the fascia, the garage surround "
            "and the sash. All of it is detail, most of it is off a ladder, and none of it "
            "is quotable from a photograph.",
            "Windows are the tell on housing this age. A {medyr} median means original or "
            "early-replacement sash, painted-shut uppers, and storm windows that have been "
            "painted over more than once. That is prep work rather than paint work, and it "
            "is the line that separates a quote that holds from one that grows.",
            "With {pre1940} percent of {name} prewar and a {medyr} median, the ceilings are "
            "the part people forget. Old plaster ceilings move, they have usually been "
            "patched at least once, and a flat white over the top of that shows every "
            "previous repair the moment the light comes across it. They are worth pricing "
            "as their own line.",
            "Housing with a {medyr} median has been painted a lot of times, and each of "
            "those coats is now a surface the next one has to hold on to. On {rooms} rooms "
            "of trim that is where the hours go. Anyone who quotes {name} interiors off a "
            "room count without asking what is already on the woodwork is guessing.",
        ]
    elif era in ("60s-early-70s", "70s-early-80s"):
        opts = [
            "A {medyr} median puts most of {name} in ranch, raised ranch and split-level "
            "shapes, and those have a specific exterior problem: a lot of wood in high "
            "places. Soffit, fascia, gable ends and the trim over a split entry all sit "
            "above reach and all fail first, while the brick below them is fine. The "
            "elevations that need pricing carefully are the ones nobody looks at.",
            "On a {medyr} house the wall area outside is usually small and the detail is "
            "not. Fascia, soffit, the garage door surround, the front entry and the window "
            "trim is a narrow band of work that adds up, and it is exactly what gets "
            "underestimated by anyone quoting off photographs instead of standing there.",
            "Interiors from around {medyr} run to lower ceilings and more doors than a "
            "modern plan, and {name} averages {rooms} rooms a unit. Six-panel doors, full "
            "baseboard runs and heavy casing: trim is where an interior job gets long. It is "
            "also the line most quotes leave vague, so ask for it on its own.",
            "Housing built around {medyr} is now on its second or third full repaint, which "
            "matters more than the first one did. Each earlier coat is a surface the new one "
            "has to bond to, and where the old work was done fast the new work has to "
            "undo it first. That is prep, it is most of the labor, and it is the honest "
            "reason two quotes for the same house can differ by a lot.",
            "Aluminum and steel are the surprise on {medyr}-era houses: soffit, fascia "
            "wrap, gutters and often the garage door. They take paint perfectly well and "
            "they take it badly if nobody cleans the chalk off first. On the {sfd} percent "
            "of {name} that is detached houses, that one step is the difference between an "
            "exterior that lasts and one that comes off in sheets.",
            "The garage is half the exterior on a lot of {medyr} plans and it is routinely "
            "left off the quote. Overhead door, jamb, the trim above it and the service "
            "door add up to a real piece of work on the {sfd} percent of {name} that is "
            "detached houses. Ask whether it is in or out before you compare two numbers.",
        ]
    else:
        opts = [
            "Later construction is not less work, it is different work. A {medyr} median "
            "means long elevations, two story walls and cedar or engineered trim that has "
            "been carrying the builder finish right up until it stopped. The second "
            "exterior on a house like this is the one that has to be prepped honestly, "
            "because the first one was riding on a factory coat.",
            "Newer stock brings height rather than age. Two story entries, vaulted rooms "
            "and stair walls are not room-rate work, and quoting them as if they were is "
            "how a job runs over. With {rooms} rooms on the median unit here and a {medyr} "
            "median build year, most of the interior conversation is about access and "
            "setup rather than about paint.",
            "The failure points on {medyr} construction are predictable: south and west "
            "elevations first, then the trim boards at the top of a two story wall, then "
            "the garage and entry doors. Knowing that changes the sequence of what gets "
            "done this year and what genuinely waits, which is worth more than a discount.",
            "On housing built around {medyr}, the original finish was sprayed once at the "
            "factory or once on site and has never been touched. That gives a very "
            "consistent surface and a very unforgiving one: it fails all at once across a "
            "whole elevation rather than in patches, so the work is scheduled by elevation "
            "rather than by room.",
            "Color matching is the quiet problem on {medyr} construction. The original was "
            "a builder line that has usually been discontinued, so a partial exterior on "
            "one of the {sfd} percent of {name} that is detached houses either gets matched "
            "properly or ends up as two shades of the same color on one wall. Worth "
            "raising before the work is broken into phases.",
            "Interiors from around {medyr} run to {rooms} rooms on the median unit with far "
            "less trim per room than older stock, so the wall area is the job and the trim "
            "is not. That flips the usual advice: here the number moves with ceiling "
            "height and open-plan sightlines, because a two story room has no place to stop "
            "a cut line.",
        ]
    out = pick(opts, seed, 4).format(**F)

    # A second sentence driven by the structure mix rather than the era, so two
    # towns of the same age still diverge.
    # Three readings each, drawn on the slug. A fixed sentence here appeared on
    # forty pages at once and was half of the longest identical run the doorway
    # audit found between two towns.
    if p["multi"] >= 45:
        tail = [
            " With {multi} percent of units here in buildings of two or more, a lot of the "
            "work is unit turnover and common areas rather than whole houses. That is priced "
            "per unit and scheduled around a move-out date, not around weather.",
            " {multi} percent of the housing sits in buildings of two units or more, which "
            "means hallways, stairwells and unit turnarounds are as much of the work as "
            "living rooms. Those get quoted per unit and they get done to a date.",
            " At {multi} percent multi-unit, {name} is a building market as much as a house "
            "market. Common areas take more abuse and less care than anything inside a unit, "
            "and they are usually the thing that has waited longest.",
        ]
    elif p["sfa"] >= 12:
        tail = [
            " {sfa} percent of the housing here is attached, so a fair share of the work is "
            "townhome and association work: matching an existing scheme exactly, working to "
            "a board's schedule and painting several identical units in a row.",
            " With {sfa} percent of units attached, a lot of jobs here come with a board and "
            "a color scheme already decided. That is a different kind of work: exact "
            "matching, a fixed sequence, and several identical elevations in a row.",
            " {sfa} percent attached housing means shared walls, shared elevations and often "
            "a shared decision. Association work runs to a schedule rather than to weather, "
            "and the matching has to be exact rather than close.",
        ]
    elif p["own_pct"] >= 85:
        tail = [
            " At {own_pct} percent owner occupied there is almost no turnover market here. "
            "What there is instead is repeat homeowner work on houses that have generally "
            "been kept up, and a maintained exterior is a different job from a neglected one "
            "in both directions.",
            " {own_pct} percent of households here own, which is high enough that turnover "
            "painting barely exists. The work is people maintaining their own house on a "
            "cycle, and that rewards being told honestly what can wait a year.",
            " With {own} owner households against {rent} renting, {name} is about as close to "
            "a pure homeowner market as this service area gets. People are painting to keep "
            "the house, not to let it, and the scope reflects that.",
        ]
    else:
        tail = [
            " With {own} owner households and {rent} renting, this is two markets in one "
            "place: owners doing a room or an elevation at a time, and small landlords "
            "wanting a unit turned around cleanly between tenants. They are not the same "
            "quote.",
            " {own} households own in {name} and {rent} rent, which produces two different "
            "phone calls. One wants the house to look right for ten years. The other wants a "
            "unit clean and let by the first of the month. Both are real work and neither "
            "should be quoted like the other.",
            " The {own} to {rent} split between owning and renting in {name} means the same "
            "street can want two different things. A contractor who prices both the same way "
            "is wrong about one of them.",
        ]
    out += pick(tail, p["slug"], "trade-tail").format(**F)
    return out


# ---- the lead-safe section -------------------------------------------------
# Three genuinely different sections, not one section reworded. What may and may
# not be said here is set out in launch/12-CITY-PAGE-DATA.md section 6.
#
# MAY say: the rule exists, what triggers it, what it requires in practice, and
# what this town's published pre-1980 or pre-1970 share is.
# MAY NOT say: that this business holds EPA lead-safe firm certification. It has
# not been supplied. TRUST["epa_rrp"] is None and the trust row renders it as a
# pending slot on every page, including these.
#
# PLAIN LANGUAGE FIRST, CITATION SECOND. Every branch now opens on a sentence a
# homeowner can act on: old paint may contain lead, that changes how the room is
# set up and cleaned rather than whether it can be painted. The rule's proper
# name, its thresholds and the fact that EPA administers it directly in Illinois
# all survive, one paragraph down, where somebody who wants the citation will
# find it and somebody who wants the answer has already had it.
#
# What is NOT written here, and must not be added without the owner's sign-off:
# "and we follow them". Mike has not confirmed his process, and CONFIRM already
# carries that as an open item. Claiming a compliance practice on 64 pages on
# the strength of nobody having asked him is exactly the class of invented claim
# the rest of this build refuses to make. The honest version is to say what the
# rule requires and to tell the reader to ask, which is what these paragraphs
# do.
#
# Illinois is NOT an EPA-authorized state for the RRP rule, so EPA administers
# it directly here. Do not name IDPH as the administering agency.

def rrp_section(p, seed):
    F = dict(name=p["name"], an=_an(p["name"]), dec=_decade(p),
             pre1980=_pc(p["pre1980"]) if p["pre1980"] is not None else "",
             pre1970=_pc(p["pre1970"]), medyr=p["medyr"], own=_n(p["own"]),
             rooms=_pc(p["rooms"]), hu=_n(p["hu"]))
    # The share sentence is the seam every branch below is bolted onto, so it
    # gets varied too. Written once, it was thirty-odd identical words sitting
    # immediately in front of whichever variant the branch drew, which is how a
    # run of shared text survives being split further down: two pages that
    # collide on one slot were already sharing the sentence before it.
    #
    # Both sets say exactly the same measured thing. Towns get a pre-1980 bucket
    # from the Census and it is named as the nearest published bucket to 1978.
    # Community areas have no 1978 bucket at all, so the pre-1970 figure is
    # given as a floor and the gap is stated rather than estimated.
    # Every variant ENDS on the place name. That is deliberate and it is the
    # cheapest duplication control on the page: the share sentence is glued
    # straight onto whichever rule paragraph the branch draws, so without a
    # unique token at the join the two run together as one shared block on any
    # pair of towns that collides on both draws.
    if p["kind"] == "town":
        share = pick([
            "The Census publishes a pre-1980 bucket rather than a pre-1978 one, and on "
            "that measure {pre1980} percent of the housing sits on the older side of the "
            "line in {name}",
            "{pre1980} percent of housing units were built before 1980, the nearest bucket "
            "to the 1978 line that the Census publishes, and that is the reading for {name}",
            "Of the {hu} housing units counted in {name}, {pre1980} percent went up before "
            "1980. There is no pre-1978 bucket, so 1980 is the nearest line the Census "
            "draws for {name}",
        ], seed, "rrp-share").format(**F)
    else:
        share = pick([
            "{pre1970} percent of housing units were built before 1970, and the "
            "community-area data does not publish a 1978 bucket, so the real pre-1978 "
            "share is higher than that by an amount nobody has measured in {name}",
            "The community-area tables stop at 1970 and never draw a 1978 line. What they "
            "give is {pre1970} percent built before 1970, which is a floor rather than an "
            "answer, and no source puts a number on the gap for {name}",
            "Read {pre1970} percent built before 1970 as the lower bound it is. The "
            "community-area data carries no 1978 bucket at all, so the share that actually "
            "matters is larger than the published one in {name}",
        ], seed, "rrp-share").format(**F)

    if p["rrp"] in ("HIGH", "MAJORITY"):
        h2 = pick(["Is there lead paint in my house?",
                   "Old paint in " + p["name"] + ", and how it has to be handled",
                   "What the age of " + p["name"] + " houses means for lead paint",
                   "Lead paint: the short version for " + p["name"]],
                  seed, 5)
        body = [
            # The plain answer, first. No percentage, no statute, no agency. Six
            # readings and every one of them names the town twice, because this
            # is the largest branch on the site and a fixed paragraph here would
            # be sixty-four identical copies.
            pick([
                "Most of {name} went up in the {dec}, which is well before 1978, and paint "
                "made before then can contain lead. That does not stop a house being "
                "painted. It changes how the room gets sealed off, how the dust is kept out "
                "of the rest of the house, and what the place looks like when the day ends.",
                "Paint from before 1978 can contain lead, and {dec} housing is the normal "
                "case in {name}. The practical effect is not that the work cannot be done. "
                "It is that it has to be contained and cleaned up to a standard, which is "
                "time at the start of a {name} job and time at the end of it.",
                "If your house in {name} is the usual {dec} vintage, there is very likely "
                "old paint under whatever is on the walls now, and old paint can be leaded. "
                "Nobody has to leave {an} {name} house unpainted over it. It does mean the "
                "sanding, the sealing off and the cleanup are part of the job rather than an "
                "extra.",
                "The honest answer for a {dec}-era house in {name} is probably yes, there is "
                "older paint under there, and paint that old can contain lead. What follows "
                "from that is method, not a refusal: sheeting, sealed doorways, dust kept "
                "where it is made, and a cleanup {name} homeowners should expect to see done "
                "properly.",
                "Old paint is the thing to know about here. {name} is largely {dec} housing, "
                "and anything painted before 1978 may have lead in the layers underneath. It "
                "is handled rather than avoided: the room is closed off, the dust is "
                "contained while the work happens, and the site is cleaned to a set standard "
                "before anyone leaves.",
                "Assume there is old paint under the current coat. On {dec} housing, which "
                "is most of {name}, that is the safe assumption, and paint from before 1978 "
                "can be leaded. It affects the setup of {an} {name} job at both ends, the "
                "sealing off before and the cleanup after, and not much in between.",
            ], seed, "rrp-plain").format(**F),
            pick([
                "In practice the rule is about containment and cleanup rather than about "
                "paint. In {an} {name} room it sets a threshold of roughly six square feet of "
                "disturbed interior paint, twenty square feet outside, and any window "
                "replacement or demolition is covered whatever the area. Sanding the casing "
                "on one {medyr}-median window clears that in a few minutes.",
                "The rule does not say {an} {name} house cannot be painted. It says how the "
                "area gets sealed off, how the dust is contained and how the site is left. "
                "The trigger in a {medyr}-median room is about six square feet of disturbed "
                "paint, twenty outside, and any window replacement or demolition at all.",
                "What it changes is the front and the back of {an} {name} job, not the middle: "
                "plastic and sealed openings before, a specific cleanup standard after. It "
                "starts at roughly six square feet of disturbed paint per room inside, "
                "twenty square feet outside, and always on window replacement.",
                "Read it as a method rather than a prohibition. Below roughly six square "
                "feet of disturbed paint in a room, or twenty outside, it does not bite. "
                "Above that, and on any window replacement in {name} at all, it decides how "
                "the room is sealed and how it is left. On {rooms}-room housing that "
                "threshold arrives early.",
                "The practical content of it is dust. Where paint in {an} {name} room gets "
                "disturbed past about six square feet, twenty outside, or wherever a window "
                "comes out, the work has to be contained and cleaned to a standard. That is "
                "time at both ends of the job, and it is why an honest quote on {own} homes "
                "worth of {medyr}-median housing reads longer than a fast one.",
            ], seed, "rrp-detail").format(**F),
            # Same wedge as the MIXED branch, and it ends on the town name for
            # the same reason. This is the biggest bucket on the site, so the
            # two drawn paragraphs on either side of it collide often enough to
            # matter, and the wedge is what stops a collision becoming a run.
            ("None of it is graded at the town line. The rule attaches to a build year and "
             "to the work being done, so the number worth checking is the one on your own "
             "deed in {name}").format(**F) + ".",
            # THE CITATION, DEMOTED. This used to be the first paragraph of the
            # section, which meant a homeowner met the words "federal
            # Renovation, Repair and Painting rule" and "not an authorized
            # state" before they were told what any of it meant for their
            # house. Nothing is cut: the rule's proper name, the trigger, the
            # published Census bucket and the fact that EPA administers it
            # directly in Illinois are all still here, in full, for anyone who
            # wants to check the plain-English version above against the source.
            share + ". " + pick([
                "The federal Renovation, Repair and Painting rule applies to work that "
                "disturbs paint in housing built before 1978, and in Illinois the EPA "
                "administers it directly rather than through a state program.",
                "Housing that old falls under the federal Renovation, Repair and Painting "
                "rule, which covers any work disturbing paint in a home built before 1978. "
                "Illinois is not an authorized state for it, so EPA runs it here directly.",
                "That puts most of the housing inside the federal lead-safe renovation rule, "
                "which attaches to pre-1978 homes and to work that disturbs the paint on "
                "them. In Illinois it is administered by EPA rather than by a state agency.",
                "Anything built before 1978 sits inside the federal Renovation, Repair and "
                "Painting rule the moment work disturbs its paint. Illinois never took the "
                "program on, so the agency behind it here is EPA itself.",
                "Stock of that age brings the federal lead-safe renovation rule with it. The "
                "rule turns on two things, a build year before 1978 and work that disturbs "
                "the paint, and in Illinois EPA enforces it directly instead of a state "
                "program doing it.",
            ], seed, "rrp-rule"),
            pick([
                "In {name} it is worth asking about before the work starts rather than "
                "after the sanding has. Ask whoever you hire to say, in plain terms, how "
                "they intend to handle it at your particular address.",
                "None of that is a reason to leave {an} {name} house unpainted. It is a reason "
                "to know what the setup looks like before anyone opens a sander, and to hear "
                "it from the person doing the work rather than from a website.",
                "The useful question is not whether the rule applies to your {name} house. "
                "At {pre1970} percent pre-1970 it very likely does. The useful question is "
                "what the containment and the cleanup are actually going to look like in "
                "your rooms, and it is a fair one to ask anybody.",
                "Ask about it early. It changes the sequence of a job rather than the price "
                "of the paint, and a contractor who has thought about it will tell you in "
                "plain terms what happens on day one.",
            ], seed, "rrp-close").format(**F),
        ]
    elif p["rrp"] == "LOW":
        h2 = pick(["Do I need to worry about lead paint here?",
                   p["name"] + " is newer, so the list of problems is different",
                   "What a newer " + p["name"] + " house actually needs"],
                  seed, 5)
        # Same three-slot treatment as the MIXED branch below, and for the same
        # reason. This branch also shipped as fixed prose, and once MIXED was
        # split it became the longest verbatim run in the corpus: Frankfort and
        # New Lenox shared 150 words end to end. LOW is a towns-only bucket,
        # because the community-area table stops at 1970 and can never grade a
        # place low, so `share` always ends on the 1978 line here.
        #
        # The true content every variant has to carry: the pre-1980 share is low
        # for this service area, the pre-1978 lead-safe question mostly does not
        # arise, what replaces it is scale and height over an untouched builder
        # finish, and a median is a midpoint so the reader should still confirm
        # the year on their own house.
        body = [
            # Plain answer first, same as the other two branches. On a young
            # town the answer is genuinely reassuring, and burying it under a
            # Census bucket sentence wasted the one piece of good news the
            # section had to give.
            pick([
                "Probably not, for most addresses. {name} is mostly {dec} housing, which is "
                "after the 1978 line, so the old lead paint question that hangs over most of "
                "this service area largely does not apply to {an} {name} house.",
                "For most of {name} the answer is no. The housing here mainly went up in the "
                "{dec}, after the 1978 cutoff, so the lead paint problem that shapes a job in "
                "the older towns is not usually the problem in {name}.",
                "Mostly not. {dec} housing is the normal case in {name}, and that is on the "
                "newer side of 1978, so lead in the old paint layers is not the thing that "
                "decides how {an} {name} job gets set up.",
                "Usually not here. {name} is young by the standards of everywhere else on "
                "this site, mostly {dec} construction, and past 1978 the lead paint question "
                "stops being the first thing anyone has to plan around.",
            ], seed, "rrp-low-plain").format(**F),
            pick([
                "What replaces it is scale and height. Larger elevations, taller interior "
                "volumes and a builder finish that was applied once and has been left alone "
                "since. The prep conversation on a house like that is about surface "
                "preparation and access equipment, not about old paint.",
                "The work is harder in a different way. Newer houses here run to bigger "
                "elevations and taller interior volumes, and most still carry the original "
                "builder finish, applied once and untouched since. That makes the "
                "conversation about access and about how the surface is prepared, not about "
                "what is underneath it.",
                "What takes its place is size. Two story entries, tall stairwells and long "
                "unbroken elevations, over a builder coat that has never been disturbed. "
                "Staging, reach and the state of the existing finish are what drive a job "
                "on stock like this.",
                "Age stops being the problem and reach starts. The stock is big: tall rooms "
                "inside, large uninterrupted walls outside, and one original coat across all "
                "of it. Surface preparation and getting safely to the work are what a quote "
                "on {name} housing turns on.",
            ], seed, "rrp-low-what").format(**F),
            # The published figure, after the plain answer rather than in front
            # of it. Same demotion as the other two branches: keep the number,
            # keep the source, stop leading with them.
            share + ". " + pick([
                "That is low for this service area, and it means the pre-1978 lead-safe "
                "question mostly does not arise here. Worth saying plainly rather than "
                "leaving as an implication.",
                "By the standards of this service area that is young housing, so the "
                "pre-1978 lead-safe question largely does not come up in {name}. It is "
                "stated rather than implied, because saying nothing about it reads like a "
                "dodge.",
                "Low, on this list. Most of {name} went up after the 1978 line, which takes "
                "the lead-safe question off the table for most addresses in town instead of "
                "leaving it hanging over the quote.",
                "That puts {name} near the young end of everywhere covered here. For most "
                "houses in town the pre-1978 lead-safe question simply does not arise, and "
                "it is more use to a reader to say so outright than to leave them guessing.",
            ], seed, "rrp-low-lead").format(**F),
            pick([
                "It also means the year on your own house is worth confirming. A median is a "
                "middle, and an older street inside a newer town is common.",
                "None of that settles your own address. A median is a midpoint rather than a "
                "floor, and an older pocket inside a newer town is ordinary. Check the year.",
                "Confirm your own build year anyway. Half the housing in {name} is older "
                "than that median by definition, and some of it is a good deal older.",
                "Worth checking for your own house regardless. The median is the middle of "
                "the range, so plenty of {name} sits behind it, and one older block does not "
                "show up in a town-wide number at all.",
            ], seed, "rrp-low-close").format(**F),
        ]
    else:
        h2 = pick(["Is there lead paint in my house? In " + p["name"] + " it depends",
                   "The lead paint answer in " + p["name"] + " depends on your street",
                   "Old paint in " + p["name"] + ": check, do not assume"],
                  seed, 5)
        # THE MIXED BRANCH IS DRAWN IN THREE INDEPENDENT PIECES.
        #
        # It used to be three fixed paragraphs with nothing selected at all, so
        # all nine MIXED towns carried the identical block. Lockport and
        # Romeoville were the measured worst case: a 109-word verbatim run,
        # the longest anywhere in the corpus. Four variants on each of three
        # slots is 64 combinations for nine towns, and the longest shared run
        # drops to a single paragraph.
        #
        # Every variant states the same four true things, and none of them may
        # drop one: the rule is the federal Renovation, Repair and Painting
        # rule; it attaches to pre-1978 housing and to work that disturbs
        # paint; EPA administers it directly in Illinois because Illinois is
        # not an authorized state; and on a town that straddles the line the
        # answer is the build year of the individual address. These are
        # rewrites, not synonym swaps.
        body = [
            # Plain answer first, as in the other two branches. A homeowner in a
            # straddling town needs to be told, before anything else, that the
            # answer is knowable and where to look it up.
            pick([
                "It depends on your own address, and that is a real answer rather than a "
                "dodge. Paint made before 1978 can contain lead, and {name} was built on "
                "both sides of that year: some streets are older, some are newer. Look up "
                "the year your house went up and you will know which one you are on.",
                "Half of {name} is old enough for lead paint to be a live question and half "
                "of it is not. Anything painted before 1978 can have lead in the layers "
                "underneath, so the thing that settles it for {an} {name} house is the build "
                "year on your own property record, not a figure for the town.",
                "Your street decides this one. Old paint can contain lead, the cutoff is "
                "1978, and {name} straddles it. Check the year on your own house before "
                "anybody prices the work, because it changes how the room gets sealed off "
                "and how it gets cleaned at the end.",
                "The answer for {name} as a whole is both, which is why it is worth checking "
                "for your own house. Paint from before 1978 can be leaded. On one side of "
                "that year {an} {name} job needs containment and a specific cleanup, and on "
                "the other side it does not.",
            ], seed, "rrp-mixed-plain").format(**F),
            share + ". " + pick([
                "That is close enough to the middle that the town as a whole does not "
                "answer the question. Your own house does.",
                "A number that close to half says something about {name} and nothing at all "
                "about your address. The town is split. The answer is at street level.",
                "Split near enough down the middle that the town figure is the wrong figure "
                "to plan from. The year on your own deed is the one that decides anything.",
                "So {name} sits on both sides of the line at once. That is useful for "
                "describing the town and useless for deciding what happens in your rooms.",
            ], seed, "rrp-mixed-lead").format(**F),
            # Wedged between the two drawn paragraphs on purpose, same device as
            # the scale sentence in the travel section. It ENDS on the town name,
            # which is the part that matters: a shared run cannot cross a token
            # that exists on no other page, so two towns that collide on both
            # draws still cannot produce one long block of identical text.
            ("Neither of the town-wide numbers is your address. They are a median build "
             "year of {medyr} and {pre1970} percent of the housing built before 1970, and "
             "both of them describe {name}").format(**F) + ".",
            pick([
                "The federal Renovation, Repair and Painting rule covers work that disturbs "
                "paint in housing built before 1978, and EPA administers it directly in "
                "Illinois. On a mixed-age town the useful move is to check the build year on "
                "your own address before anybody starts, because the setup, the containment "
                "and the cleanup are different on either side of it.",
                "Pre-1978 homes fall under the federal Renovation, Repair and Painting rule "
                "wherever the work disturbs paint. Illinois never took the program over, so "
                "EPA runs it here itself. Look up the year your own place went up before a "
                "quote gets written: either side of 1978 changes how the area is sealed, how "
                "the dust is handled and what the site looks like at the end.",
                "What sits behind the line is worth knowing. The federal lead-safe "
                "renovation rule attaches to housing built before 1978 and to any work that "
                "disturbs the paint on it, and in Illinois it is enforced by EPA rather than "
                "by a state agency. In {name} the only way to know which side you are on is "
                "to check the year on your own address.",
                "One address at a time is the honest way to handle a town like this. The "
                "federal Renovation, Repair and Painting rule applies to pre-1978 housing "
                "once paint gets disturbed, EPA administers it directly here because "
                "Illinois is not an authorized state, and what it requires by way of "
                "containment and cleanup is a real difference in how a job is set up and "
                "finished. Find the build year first.",
            ], seed, "rrp-mixed-rule").format(**F),
            pick([
                "It is a five-minute check and it changes what a fair quote looks like.",
                "The lookup is quick, and it is the difference between a quote you can read "
                "and one you cannot.",
                "Settle it off the property record before anyone prices the work, rather "
                "than after the third number comes in.",
                "Ask the question early. It costs nothing, and it decides whether day one "
                "starts with a drop cloth or with a sealed room.",
            ], seed, "rrp-mixed-close").format(**F),
        ]
    return h2, body


def travel_section(p, seed):
    """Distance and honest coverage language.

    Straight-line miles are stated as straight-line miles. No drive time is
    given anywhere, because a drive time would be an invented number and this
    build does not ship those: the honest version is the distance plus a
    sentence telling you to ask.
    """
    mi = "%.1f" % p["mi"]
    n = p["name"]
    if p["kind"] == "nbhd":
        band = [
            ("The shop is at " + STREET + " in Bridgeview, " + mi + " straight-line miles "
             "from " + n + ". The south and southwest sides are the city work this business "
             "actually does, and that stock is the same brick and plaster as the inner "
             "suburbs, so it is the same job rather than a different one.",
             "What will not be pretended here is coverage of the whole city. Chicago is "
             "enormous and heavily contested, and a north side call is better served by "
             "somebody on the north side. Ask, and you will be told which one you are before "
             "anything gets scheduled."),
            (n + " is " + mi + " straight-line miles from " + STREET + " in Bridgeview, which "
             "is the south side end of the city rather than the middle of it. That is the "
             "part of Chicago this business works.",
             "It is worth being blunt about the rest: no contractor this size covers Chicago "
             "well, and a page claiming the whole city would be a page claiming something it "
             "cannot do. South and southwest is the real answer, and you will get it on the "
             "phone rather than after a missed appointment."),
            ("From the Bridgeview shop at " + STREET + " it is " + mi + " straight-line miles "
             "to " + n + ". The city work here is the south and southwest sides and it is "
             "genuine work, not a list of neighborhood names bolted onto a suburban site.",
             "Anything materially north of that is better handled by somebody based up "
             "there, and saying so costs nothing. Ask before you plan around a date."),
            ("It is " + mi + " straight-line miles between " + STREET + " in Bridgeview and " +
             n + ". Southwest of the Loop is the half of Chicago this shop treats as normal "
             "working distance, and the housing on that side goes up the same way the inner "
             "suburbs did.",
             "The whole city is not on offer and there is no point pretending otherwise. "
             "Chicago is too big and too well covered for one small shop to claim all of it, "
             "so anything well north of here gets an early no rather than a late one."),
        ]
    elif p["mi"] < 0.05:
        # The home town is zero miles from itself, and the close-ring band below
        # rendered that literally: "Bridgeview is 0.0 straight-line miles from
        # the shop". True, and it reads like a machine wrote it, which on the
        # one page where proximity is the whole argument is the worst place on
        # the site to sound generated.
        band = [
            ("The shop is at " + STREET + ", in " + n + ". There is no drive: this is the "
             "one place on this site where the work and the workshop share a village.",
             "That is not a marketing line, it is a scheduling fact. A single ceiling, one "
             "bad wall or a door that needs stripping is worth a trip here on its own, and "
             "in most towns it is not."),
            ("There is no distance to quote for " + n + ". The shop is on " + STREET +
             ", inside the village, and every other page on this site measures itself "
             "against this address.",
             "The practical effect is at the small end of the work. Little jobs fit into "
             "gaps in the week rather than waiting for a day long enough to justify the "
             "driving, so you get a date sooner than the size of the job suggests."),
            (n + " is where the shop is. " + STREET + ", not a franchise office in another "
             "county and not a service-area pin dropped on a map.",
             "Which mostly matters for the jobs that are too small to travel for. A repair "
             "that is worth doing gets looked at here instead of being folded into "
             "something bigger next month."),
        ]
    elif p["mi"] < 5:
        band = [
            ("The shop is at " + STREET + " in Bridgeview, " + mi + " straight-line miles "
             "from " + n + ". This is the close ring.",
             "Being this close is not a marketing line, it is the reason one small repair is "
             "worth looking at on its own here instead of being bundled into something "
             "bigger next month."),
            (n + " is " + mi + " straight-line miles from the shop, which puts it inside the "
             "ring where distance stops being a factor in what gets quoted.",
             "That matters most at the small end. A single ceiling, one bad wall or a door "
             "that needs stripping is worth a trip here, and elsewhere it often is not."),
            ("At " + mi + " straight-line miles from " + STREET + ", " + n + " is about as "
             "close to the shop as anywhere gets.",
             "The practical effect is scheduling. Small jobs fit into gaps in a week instead "
             "of waiting for a day that can absorb the driving, so you get a date sooner "
             "than the size of the job would suggest."),
        ]
    elif p["mi"] < 10:
        band = [
            (n + " is " + mi + " straight-line miles from the Bridgeview shop at " + STREET +
             ". Door to door is longer than that, and it is worth asking rather than "
             "assuming.",
             "At this range a walk-through and the work itself do not have to be the same "
             "trip, so getting it looked at properly costs nothing but a visit."),
            ("From the shop to " + n + " is " + mi + " straight-line miles. That is the "
             "middle ring: not next door, not a trek.",
             "Most jobs of any size are straightforward to schedule from here. The one thing "
             "worth flagging on the call is whether the work is a single small item, because "
             "that changes the answer."),
            ("The distance from " + STREET + " in Bridgeview to " + n + " is " + mi + " miles "
             "in a straight line, and a bit more on the road.",
             "Nothing about that range rules anything out. It does mean a small job is "
             "better combined with something else, and it is easier to say that up front "
             "than to work it into a number afterwards."),
        ]
    elif p["mi"] < 16:
        band = [
            (n + " sits " + mi + " straight-line miles out from Bridgeview. That is a real "
             "drive rather than a short run.",
             "Whole interiors, full exteriors and kitchens are the jobs that make the "
             "distance make sense. One small patch on its own probably does not, and you "
             "will be told that rather than quoted a number that quietly covers the "
             "travel."),
            ("It is " + mi + " straight-line miles from the shop at " + STREET + " to " + n +
             ", which is far enough that the size of the job decides the answer.",
             "The honest split: full interiors, complete exteriors and remodeling work are "
             "worth the trip. A single repair usually is not, and being told that is more "
             "useful than a padded quote."),
            ("The shop is " + mi + " straight-line miles from " + n + ". Call it a genuine "
             "drive.",
             "Distance gets handled by being straight about it rather than by pricing it in "
             "quietly. Larger jobs make sense from here. For anything small, ask first and "
             "expect a real answer."),
        ]
    else:
        band = [
            (n + " is " + mi + " straight-line miles from the shop, which is the outer edge "
             "of where this business works.",
             "Ask about scheduling before you count on a date. The answer is sometimes no, "
             "and no in advance is worth more than a yes that turns into a missed "
             "appointment."),
            ("At " + mi + " straight-line miles, " + n + " is at the far end of the area, and "
             "the page says so rather than pretending otherwise.",
             "That does not mean the work does not happen. It means the size and the timing "
             "have to make sense together, and that is a two-minute conversation on the "
             "phone rather than a guess off a website."),
            ("From Bridgeview to " + n + " is " + mi + " straight-line miles. This is the "
             "boundary of the service area, not the middle of it.",
             "Whether it works depends on the job and on the week. Ask, and you will get a "
             "yes or a no rather than a maybe that turns into a cancelled appointment."),
        ]
    # The two halves are drawn INDEPENDENTLY, and that is the whole point.
    #
    # The first version picked a (lead, tail) pair as one unit, which meant two
    # towns that drew the same pair carried the same ninety-odd words end to
    # end. Morgan Park and West Elsdon were the measured worst case: one
    # unbroken 93-word run, and the sentence build_city() appends after it made
    # the run longer still. Drawing the lead on one slot and the tail on
    # another turns three pairs into nine combinations, four into sixteen for
    # the neighborhood band, and caps the longest verbatim run at one paragraph
    # instead of two.
    #
    # Every lead in every band ends on the distance and the character of the
    # range, and every tail opens on what that means, so the halves compose in
    # any combination. Check that by hand if you add one: a tail that refers
    # back to a specific phrase in a specific lead will read as a non sequitur
    # against the other three.
    return pick([b[0] for b in band], seed, "travel"), pick([b[1] for b in band], seed,
                                                            "travel-tail")


# ---- services, weighted by what the town actually is ------------------------

def estimate_notes(p, seed):
    """Four lines saying what an estimate on THIS housing has to account for.

    Every line fires on a predicate about this place and carries a figure from
    its own row, so the set a town draws is a function of its housing rather than
    of a template. It is also the most directly useful block on the page: it is
    the list a homeowner can hold a written quote up against.
    """
    n = p["name"]
    pool = []
    # Local defaults, because add() builds every candidate string before the
    # condition is tested. Neighborhoods carry no manufactured-housing figure and
    # Bedford Park carried no median value in the old table, so reading either
    # one unguarded is a crash rather than a missing bullet.
    mob = p.get("mobile") or 0.0
    val = p["medval"] or 0

    def add(cond, head, text):
        if cond:
            pool.append((head, text))

    old_share = p["pre1980"] if p["pre1980"] is not None else p["pre1970"]
    old_word = "before 1980" if p["pre1980"] is not None else "before 1970"
    add(old_share >= 55,
        "Containment, not just paint.",
        " " + _pc(old_share) + " percent of housing in " + n + " was built " + old_word +
        ", so on most addresses here the lead-safe setup and the cleanup are part of the job "
        "and part of the hours.")
    add(p["pre1940"] >= 12,
        "Plaster as well as drywall.",
        " " + _pc(p["pre1940"]) + " percent of " + n + " is prewar. Plaster cracks along the "
        "lath and comes back if it is only filled, so wall repair is a different line from "
        "wall painting.")
    add(p["rooms"] >= 6.0,
        "Trim, counted separately.",
        " At a median of " + _pc(p["rooms"]) + " rooms, casing, baseboard and doors are the "
        "half of an interior that actually varies. A single number for the whole house hides "
        "it.")
    add(p["rooms"] < 5.6,
        "Setup does not shrink with the room.",
        " The median unit here is " + _pc(p["rooms"]) + " rooms. Masking, cutting in and "
        "cleanup cost the same in a small room as a large one, so a flat per-room rate is "
        "usually wrong in one direction or the other.")
    add(p["multi"] >= 35,
        "Per unit, to a date.",
        " " + _pc(p["multi"]) + " percent of units here are in buildings of two or more. "
        "Turnover work is priced per unit and scheduled to a move-out, not to the weather.")
    add(p["sfd"] >= 70,
        "Whole elevations.",
        " " + _pc(p["sfd"]) + " percent of the housing is detached, so an exterior here is "
        "four sides and a garage rather than one face of a shared building.")
    add(p["sfa"] >= 10,
        "Matching, exactly.",
        " " + _pc(p["sfa"]) + " percent of units are attached, and on a shared elevation "
        "close is not good enough. Existing color has to be matched rather than approximated.")
    add(p["era"] in ("late-80s-90s", "2000s-plus"),
        "Access, and what it costs.",
        " A " + str(p["medyr"]) + " median build year means two story walls outside and two "
        "story spaces inside. Staging and ladder work belong on the quote as their own line.")
    add(val >= 330000,
        "Finish level.",
        " With a median home value of " + _money(val or 1) + ", the finish standard people "
        "expect here is higher than the standard a fast quote is priced at. Worth agreeing "
        "before rather than after.")
    add(mob >= 10,
        "Not all of it is site built.",
        " " + _pc(mob) + " percent of housing here is manufactured. Different "
        "substrate, different primer, different price, and it should be said out loud rather "
        "than discovered on the day.")
    add(p["own_pct"] < 62,
        "Two different customers.",
        " " + _pc(p["own_pct"]) + " percent owner occupancy means homeowner work and landlord "
        "work sit side by side here, and they want opposite things from a schedule.")
    add(p["mi"] >= 0.05,
        "Distance, stated.",
        " " + n + " is " + ("%.1f" % p["mi"]) + " straight-line miles from the shop. Travel "
        "to " + n + " is not a hidden line item on this site and it should not be one on a "
        "written quote either.")
    # The home town would otherwise read "Bridgeview is 0.0 straight-line miles
    # from the shop", which is true and reads like a template that was never
    # looked at. Same fact, said the way a person says it. Guarded on distance
    # rather than on the slug so it stays right if the shop ever moves.
    add(p["mi"] < 0.05,
        "No travel line at all.",
        " The shop is in " + n + ". Nothing on a quote here is covering a drive, which is "
        "worth checking against any other number you are given for the same work.")

    start = hnum(p["slug"], "estimate") % max(1, len(pool))
    ordered = pool[start:] + pool[:start]
    return ordered[:4]


def service_order(p):
    """Which service pages lead on this town's page.

    Ordered by what the housing says the work is, so a rental-heavy town leads
    with turnover and drywall and a large newer town leads with exteriors. The
    full set is always linked: this decides sequence, not inclusion.
    """
    score = dict((s["slug"], 0.0) for s in SERVICES)
    score["interior-painting"] += 3
    score["exterior-painting"] += 2
    if p["multi"] >= 40 or p["own_pct"] < 60:
        score["drywall-and-repair"] += 4
        score["interior-painting"] += 2
    if p["sfd"] >= 70:
        score["exterior-painting"] += 3
    if p["era"] in ("late-80s-90s", "2000s-plus"):
        score["exterior-painting"] += 3
        score["remodeling"] += 2
    if p["era"] in ("prewar", "postwar-50s"):
        score["drywall-and-repair"] += 2
        score["cabinet-refinishing"] += 1
    if p["medval"] and p["medval"] >= 320000:
        score["cabinet-refinishing"] += 3
        score["remodeling"] += 3
    if p["rooms"] and p["rooms"] >= 6.2:
        score["interior-painting"] += 1
    return sorted(SERVICES, key=lambda s: (-score[s["slug"]], s["slug"]))


def service_reason(p, s):
    """One honest sentence saying why this service leads on this page.

    Three readings per service, drawn independently per place, and every one of
    them carries a figure from this place's own row. A five-line service block
    that is word for word identical on 76 pages is most of what makes a
    location-page set look generated, so it is not allowed to be.
    """
    F = dict(name=p["name"], multi=_pc(p["multi"]), sfd=_pc(p["sfd"]), sfa=_pc(p["sfa"]),
             own_pct=_pc(p["own_pct"]), rooms=_pc(p["rooms"]), medyr=p["medyr"],
             own=_n(p["own"]), rent=_n(p["rent"]), hu=_n(p["hu"]),
             pre1970=_pc(p["pre1970"]),
             val=_money(p["medval"]) if p["medval"] else "")
    m = {
        "interior-painting": [
            "With a median of {rooms} rooms per unit, the interior number in {name} is "
            "decided by trim runs more than by wall area.",
            "{own} owner households and a median {rooms} rooms: interiors are the steadiest "
            "work in {name} and the easiest to get quoted vaguely.",
            "On {medyr}-median stock at {rooms} rooms a unit, what varies inside is the "
            "condition of the woodwork, not the square footage.",
        ],
        "exterior-painting": [
            "{sfd} percent of {name} is detached houses, so exterior work here is whole "
            "elevations rather than a shared wall.",
            "Exteriors on {medyr}-median housing fail at the top first, and {sfd} percent of "
            "{name} is detached, so there is a lot of top.",
            "With {sfd} percent of the {hu} units here standing on their own, the exterior "
            "is the whole envelope and it gets priced by elevation.",
        ],
        "drywall-and-repair": [
            "{multi} percent of units in {name} are in buildings of two or more, which is "
            "where patching, turnover and ceiling repair live.",
            "Repair comes before paint on {pre1970} percent pre-1970 stock, and in {name} "
            "that is most of it.",
            "{rent} renter households in {name} means turnover, and turnover means patching "
            "and ceilings before anything else happens.",
        ],
        "cabinet-refinishing": [
            "On {medyr}-median kitchens the boxes are usually sound and the finish is not, "
            "which is the case refinishing is for.",
            "Kitchens in {medyr}-era {name} houses were built to last and finished to a "
            "budget, which is exactly the gap refinishing closes.",
            "At {rooms} median rooms the kitchen is the room that decides how the house "
            "feels, and refinishing changes it without moving a cabinet.",
        ],
        "remodeling": [
            "Carpentry, tile and flooring come up on the same visit often enough in {name} "
            "that pretending they are separate trades wastes everyone's time.",
            "On {medyr}-median housing the thing behind the paint is usually the thing that "
            "actually needs doing, and in {name} that is trim, subfloor and tile.",
            "{own_pct} percent owner occupied means people fix things to keep them, not to "
            "flip them, and that is a different scope of remodeling work.",
        ],
    }
    opts = m.get(s["slug"])
    if not opts:
        return ""
    return pick(opts, p["slug"], "svc-" + s["slug"]).format(**F)


# ---- blog posts, chosen by profile -----------------------------------------

def post_reason(p, slug):
    """Why this post, for this place, in this place's own numbers."""
    old_share = p["pre1980"] if p["pre1980"] is not None else p["pre1970"]
    old_word = "1980" if p["pre1980"] is not None else "1970"
    m = {
        "rental-turnover-painting-southwest-suburbs":
            "Relevant here because " + p["name"] + " has " + _n(p["rent"]) + " renter "
            "households and " + _pc(p["multi"]) + " percent of its units in buildings of two "
            "or more.",
        "best-time-to-paint-house-exterior-chicago":
            "Relevant here because " + _pc(p["sfd"]) + " percent of " + p["name"] + " is "
            "detached houses, on a " + str(p["medyr"]) + " median build year, so the exterior "
            "is the whole envelope and the window for doing it is short.",
        "choosing-paint-colors-older-southwest-suburb-homes":
            "Relevant here because the median build year is " + str(p["medyr"]) + " and " +
            _pc(p["pre1940"]) + " percent of the housing is prewar, which narrows what "
            "actually looks right on it.",
        "cabinet-refinishing-vs-replacing":
            "Relevant here because kitchens on " + str(p["medyr"]) + "-median housing at " +
            _pc(p["rooms"]) + " median rooms usually have sound boxes and a tired finish.",
        "how-to-tell-good-prep-from-a-fast-cheap-job":
            "Relevant here because " + _pc(old_share) + " percent of " + p["name"] + " was "
            "built before " + old_word + ", and on stock that age prep is most of the labor "
            "and most of the difference between two quotes.",
        "interior-painting-cost-southwest-chicago-suburbs":
            "Relevant here because " + _n(p["own"]) + " owner households at a median of " +
            _pc(p["rooms"]) + " rooms is a lot of trim, and trim is the part of an interior "
            "price that moves.",
    }
    return m.get(slug, "Relevant to housing of this age in " + p["name"] + ".")


def city_posts(p, posts, seed):
    if not posts:
        return []
    by_slug = dict((x["slug"], x) for x in posts)
    want = []
    if p["multi"] >= 40 or p["own_pct"] < 60:
        want.append("rental-turnover-painting-southwest-suburbs")
    if p["era"] in ("late-80s-90s", "2000s-plus"):
        want.append("best-time-to-paint-house-exterior-chicago")
    if p["era"] in ("prewar", "postwar-50s", "60s-early-70s"):
        want.append("choosing-paint-colors-older-southwest-suburb-homes")
    if p["medval"] and p["medval"] >= 320000:
        want.append("cabinet-refinishing-vs-replacing")
    filler = ["how-to-tell-good-prep-from-a-fast-cheap-job",
              "interior-painting-cost-southwest-chicago-suburbs",
              "best-time-to-paint-house-exterior-chicago",
              "choosing-paint-colors-older-southwest-suburb-homes"]
    i = hnum(seed, "posts") % len(filler)
    while len(want) < 2:
        cand = filler[i % len(filler)]
        if cand not in want:
            want.append(cand)
        i += 1
    want = want[:2]
    missing = [w for w in want if w not in by_slug]
    if missing:
        sys.exit("BUILD FAILED: city page for " + p["name"] + " wants blog post(s) " +
                 ", ".join(missing) + " which do not exist in blog/. Fix city_posts() in "
                 "build.py or add the post.")
    return [by_slug[w] for w in want]


# ---- FAQ, selected by what is true of the place ----------------------------

def city_faq(p, seed):
    """Four questions, chosen by predicate rather than pasted.

    Every answer contains at least one figure from this place's own row, which
    is what stops the FAQ block being the identical two hundred words on every
    page that most programmatic location sets ship.
    """
    F = dict(name=p["name"], mi="%.1f" % p["mi"], own=_n(p["own"]), rent=_n(p["rent"]),
             own_pct=_pc(p["own_pct"]), medyr=p["medyr"], rooms=_pc(p["rooms"]),
             multi=_pc(p["multi"]), sfd=_pc(p["sfd"]), sfa=_pc(p["sfa"]),
             pre1970=_pc(p["pre1970"]), pre1940=_pc(p["pre1940"]), hu=_n(p["hu"]),
             pre1980=_pc(p["pre1980"]) if p["pre1980"] is not None else "",
             val=_money(p["medval"]) if p["medval"] else "",
             phone=PHONE_DISPLAY, owner=OWNER)
    pool = []

    def add(cond, q, a):
        if cond:
            pool.append((q.format(**F), a.format(**F)))

    def addv(cond, q, answers):
        """Same question, one of several answers, drawn independently per place.

        The FAQ block is the single largest run of text on a city page, so a
        fixed answer to a question that fires on forty towns is forty copies of
        the same two hundred words. The draw is on the place slug plus the
        question, so two towns that ask the same thing usually answer it
        differently, and both answers carry that town's own figures.
        """
        if cond:
            pool.append((q.format(**F),
                         pick(answers, p["slug"], "faq-" + q[:24]).format(**F)))

    add(p["kind"] == "town" and p["pre1980"] is not None and p["pre1980"] >= 60,
        "Does the lead-safe rule apply to my house in {name}?",
        "Probably, and the honest answer is that your build year decides it rather than the "
        "town. {pre1980} percent of housing units in {name} went up before 1980, so most "
        "addresses here land on the pre-1978 side of the federal Renovation, Repair and "
        "Painting rule. It applies to work that disturbs paint, at roughly six square feet "
        "per room inside or twenty square feet outside, and to any window replacement. Check "
        "the year on your own address and ask whoever quotes you how they handle it.")
    add(p["kind"] == "nbhd",
        "Why do these figures cover the community area rather than my ZIP code?",
        "Because ZIP codes cut through neighborhood lines and community areas do not. One "
        "ZIP on the southwest side covers three different neighborhoods with three different "
        "kinds of housing, so a page built on it would be describing an average of places "
        "that have nothing to do with each other. The {hu} housing units counted here are "
        "the ones inside {name}, and the source is named at the bottom of the page.")
    add(p["multi"] >= 35,
        "Do you paint rental units and common areas in {name}?",
        "Yes, and it is a real part of the work here rather than an afterthought. {multi} "
        "percent of housing units in {name} sit in buildings of two or more, and {rent} "
        "households rent. Turnover repaints get priced per unit and scheduled around a "
        "move-out date. Ask for it that way and you will get a number that fits the "
        "deadline.")
    add(p["own_pct"] >= 80,
        "Most of {name} is owner occupied. Does that change anything?",
        "It changes what the work usually is. At {own_pct} percent owner occupied, with "
        "{own} owner households, there is very little turnover painting here and a lot of "
        "repeat maintenance: exteriors on a cycle, one room at a time inside, trim and doors "
        "when they finally go. A maintained house and a neglected one are different jobs and "
        "should be different numbers, in both directions.")
    add(p["era"] in ("prewar", "postwar-50s"),
        "My house in {name} is plaster, not drywall. Is that a problem?",
        "It is not a problem, it is a different repair. Plaster cracks along the lath and "
        "comes back if it is only filled, so the fix has to address the movement rather than "
        "the line. With a {medyr} median build year most of {name} is plaster over lath on at "
        "least some walls and ceilings. Say so when you call, because it changes the time "
        "estimate and it is better said before the quote than after.")
    add(p["era"] in ("late-80s-90s", "2000s-plus"),
        "My house in {name} is not old. Why does the quote still take so long?",
        "Height and area, mostly. Housing here runs to a {medyr} median build year, which "
        "means two story elevations outside and two story entries and stair walls inside. "
        "That is access equipment and setup time rather than paint, and it is the part that "
        "gets left out of a fast number. It is worth having it itemized so you can see what "
        "you are paying for.")
    add(p["rooms"] is not None and p["rooms"] >= 6.2,
        "How is an interior price worked out for a house this size?",
        "By trim, mostly. The median home in {name} runs {rooms} rooms, and rooms bring door "
        "casing, window casing and baseboard with them. Wall area is the fast part of an "
        "interior job and trim is the slow part, so a quote that gives one number for the "
        "whole house is hiding the half of it that actually varies. Ask for the trim "
        "separately.")
    add(p["rooms"] is not None and p["rooms"] <= 5.2,
        "Is a smaller place cheaper to paint per room?",
        "Not proportionally, no. The median unit in {name} is {rooms} rooms, and a small "
        "room still needs the same masking, the same cutting in and the same cleanup as a "
        "large one. What falls is the roller time, which is the cheapest part of the day. "
        "Anyone quoting a flat per-room rate on small rooms is either guessing high or about "
        "to be disappointed.")
    add(p["mi"] >= 10,
        "Do you actually come out to {name}, or is this just a page?",
        "It is {mi} straight-line miles from the shop in Bridgeview, so it is a genuine "
        "drive and the answer depends on the job. A full exterior or a whole interior is "
        "worth the trip. One small patch on its own usually is not, and you will be told "
        "that rather than quoted a number that quietly covers the travel. Call {phone} and "
        "ask before you plan around it.")
    add(p["mi"] < 10,
        "How quickly can somebody look at it?",
        "{name} is {mi} straight-line miles from the shop, which is close enough that "
        "looking at the work and doing the work do not have to be the same trip. That "
        "matters most on small jobs, because a repair that is worth doing gets seen instead "
        "of being pushed into a bigger job later. Call {phone}.")
    addv(p["medval"] is not None,
         "Is the {val} median home value in {name} what a job here costs?",
         ["No, and the two are unrelated. {val} is the Census estimate of what homes in "
          "{name} are worth, and it is on this page because the age and the size of the "
          "housing describe the work. No price for painting or remodeling appears anywhere "
          "on this site, because no local range has been established that would survive "
          "being checked. Every job is quoted after we stand in it.",
          "No. That figure describes the houses, not the work. {val} is what the Census "
          "estimates a home in {name} is worth, and it earns its place on this page because "
          "value tracks size and age, which is what a painter is actually pricing. There is "
          "no price list on this site because there is no honest local one to publish yet.",
          "They are two different things. {val} is a published estimate of home value in "
          "{name} and nothing more. Cost of work depends on what is on the walls now, how "
          "much trim there is and what has to come off before anything goes on, and none of "
          "that is knowable from a median."])
    addv(True,
         "Who actually shows up in {name}?",
         ["Our crew, with {owner} running it. He owns the company, and every job is quoted "
          "after we walk it. Tell us the town, the room and roughly what you want, and you "
          "will know what happens next on the same call. {phone}.",
          "Our painters do the work and the owner runs the job, so the person who priced it is "
          "still the person answerable for it. Call {phone}, say where in {name} you are and "
          "what needs doing, and you will get an answer rather than a callback from an office.",
          "{owner} owns the company, walks the job and stays on it while our crew works. Call "
          "{phone}. It is worth saying because on a job this size the gap between whoever "
          "measured it and whoever turns up is where most of the disappointment comes from."])
    addv(True,
         "Can it be done a room at a time?",
         ["Yes, and on {rooms}-room housing it is often the right call. Doing one room "
          "properly beats doing four at a pace that shows, and it spreads the cost across "
          "seasons rather than across a credit card. Say that is what you want when you "
          "call, because it changes how the work is sequenced.",
          "Yes. With a median of {rooms} rooms in {name} a full interior is a real "
          "commitment, and there is nothing wrong with taking it in pieces. The one thing "
          "worth planning is the order, so that the rooms that get used most are not the "
          "ones sitting under plastic in December.",
          "It can. Splitting a {rooms}-room house into phases is normal and it is priced as "
          "phases rather than as a discount on the whole. The trade-off is setup time, "
          "because masking and protecting a room costs the same whether it is one room or "
          "the fourth."])
    addv(True,
         "What changes the price most on a house here?",
         ["Condition, not size. On {medyr}-median stock in {name} what varies is how much "
          "has to come off or be made good before anything goes on: loose paint, failed "
          "caulk, damaged trim, ceilings that have been patched before. Two houses on the "
          "same street can differ by a lot on that alone.",
          "Prep. Housing here runs to a {medyr} median, which means several coats are "
          "already on the woodwork and some of them were put on badly. Undoing that is the "
          "expensive part, and it is the part that a fast number leaves out and a slow one "
          "explains.",
          "The state of the trim and the ceilings. Wall area is predictable, and with "
          "{rooms} median rooms and a {medyr} median build year in {name} the woodwork is "
          "where the hours actually go. Ask for it as its own line and the differences "
          "between two quotes stop being mysterious."])

    # Take the first four that fit, rotated so two towns with identical
    # predicates still lead on different questions.
    n = len(pool)
    start = hnum(seed, "faq-start") % max(1, n)
    ordered = pool[start:] + pool[:start]
    out, seen = [], set()
    for q, a in ordered:
        if q in seen:
            continue
        seen.add(q)
        out.append((q, a))
        if len(out) == 4:
            break
    return out


# ---- the homeowner opening --------------------------------------------------
# Everything above this comment measures a town. This block is the only part of
# a city page written for the person who lives in one.
#
# WHY IT EXISTS. The page used to open on the Census and put the answer
# underneath it: one lede literally read "Numbers first, sales second". That was
# a deliberate anti-doorway decision and it worked, but it optimized for an
# analyst. Somebody who has just searched "painters near me" wants four things,
# in this order: can you do my job, roughly what will it cost, are you any good,
# and when can you come. A median build year answers none of them. So the answer
# comes first now and the figures moved down the page to support it. Nothing was
# deleted. Every number and every citation is still on the page, lower, in a
# block that says what it is.
#
# TWO RULES FOR ANYTHING ADDED HERE, both load-bearing:
#
#   1. No percentages and no citations above the fold. Plain consequence only.
#      "Most houses around here went up in the 1950s, so the trim is original and
#      has had a few coats" is the same fact as "median year built 1954, 71.2
#      percent pre-1980" and one of them is readable on a phone. The figure and
#      the source still exist, in the data block at the foot of the page.
#
#   2. Every variant names the town at least twice and the two halves are drawn
#      on INDEPENDENT slots. This block is 76 pages wide, so a fixed paragraph
#      in it is 76 identical copies and doorway_audit() counts every one of them.
#      The decade word varies with the town's own median year, which is a second
#      differentiator inside a single era bucket.


def _decade(p):
    """The median build year as a decade word. 1954 becomes "1950s"."""
    return str(p["medyr"])[:3] + "0s"


# Card names are headings and read fine as headings. Two of them carry an "and"
# inside, and dropping those into a running sentence produced "drywall and
# repair and interior painting", which is the tell of a string that was written
# for a nav bar and reused in prose. These are the prose forms, and they are the
# only ones any sentence on a city page is allowed to use.
SERVICE_PROSE = {
    "interior-painting": "interior painting",
    "exterior-painting": "exterior painting",
    "cabinet-refinishing": "cabinet refinishing",
    "drywall-and-repair": "drywall repair",
    "remodeling": "remodeling",
}


def service_prose(s):
    return SERVICE_PROSE.get(s["slug"], s["card"].lower())


def plain_age_line(p, seed):
    """How old the housing is, said the way a neighbor would say it.

    Two halves, drawn independently: what the houses are, then what that changes
    about the work. Sixteen combinations per era bucket, times the decade word,
    which is what keeps twenty-one towns of the same era from opening the same
    way. No number appears in either half on purpose. The numbers are downstairs.
    """
    F = dict(name=p["name"], an=_an(p["name"]), dec=_decade(p))
    era = p["era"]
    if era in ("prewar", "postwar-50s"):
        first = [
            "Most houses around {name} went up in the {dec}. Housing that age normally "
            "still has its original trim, and that trim is already carrying a lot of paint.",
            "The bulk of {name} is {dec} housing. That usually means plaster on at least "
            "some walls and ceilings, deep original woodwork, and several coats of paint "
            "already sitting on it.",
            "{name} is mostly {dec} housing and it behaves like it: original casing and "
            "baseboard, plaster in the older rooms, and windows that have been painted over "
            "more than once.",
            "If your house is typical for {name} it dates from the {dec}. Old trim, plaster "
            "walls in at least part of it, and a surface somebody has already painted, well "
            "or badly.",
        ]
        second = [
            "That changes the prep far more than it changes the paint. Getting {an} {name} "
            "house right is mostly about what comes off and what gets made good before "
            "anything goes on.",
            "It is the reason two painters can look at the same {name} house and hand you "
            "very different numbers. One of them has priced the preparation and one of them "
            "has not.",
            "So on {an} {name} house the preparation is the job. Paint over a wall that was "
            "not made ready looks right for a season and then tells on you.",
            "Which means the hours go into stripping, filling, sanding and sealing rather "
            "than into rolling. On {name} housing that is where a fair quote and a cheap one "
            "part company.",
        ]
    elif era in ("60s-early-70s", "70s-early-80s"):
        first = [
            "Most of {name} is {dec} housing: ranches, raised ranches and split levels, "
            "masonry at the bottom and painted wood up top.",
            "{name} runs to {dec} construction. Brick or brick fronted, with the wood that "
            "actually needs painting up on the gables, the soffit and the fascia.",
            "The typical house in {name} was built in the {dec}. Not much of the outside "
            "takes paint at all, and what does is mostly above head height.",
            "{dec} housing is the normal case in {name}. Masonry walls, wood trim, and most "
            "of that wood somewhere you need a ladder to reach.",
        ]
        second = [
            "That is why an exterior here takes longer than the size of the house suggests. "
            "The work on {an} {name} elevation is all detail and most of it is off a ladder.",
            "So the outside number is set by access rather than by wall area, and the inside "
            "one by how many doors and how much casing {an} {name} house turns out to have.",
            "It also means the parts that fail first are the parts nobody looks at. On {an} "
            "{name} exterior the brick is usually fine and the wood above it is not.",
            "Which puts most of the cost in reach and in preparation. Painting {an} {name} "
            "house is not a wall-area job, it is a trim and access job.",
        ]
    else:
        first = [
            "{name} is largely {dec} housing, newer than most of what we work on. Big "
            "elevations, two story entries, and whatever finish the builder put on.",
            "Most of {name} was built in the {dec}. The houses are large rather than old: "
            "long walls outside, tall rooms and stair walls inside.",
            "The typical {name} house dates from the {dec}. Siding with a masonry front, "
            "cedar or composite trim, and an original builder finish that has never been "
            "touched.",
            # No lead-paint claim in here. The RRP section owns that question and
            # grades it per town, and a MIXED town like Lockport would have this
            # paragraph waving the question away two screens above a section
            # telling the reader to go and check their own build year.
            "{name} is newer stock, mostly {dec}. The problem on housing like that is not "
            "what is under the paint, it is the size of what has to be covered.",
        ]
        second = [
            "So the question on {an} {name} house is not what is underneath. It is how you "
            "reach the work safely, and what the original coat is doing now that it has "
            "stopped holding.",
            "That makes staging and setup a real line on the quote rather than an "
            "afterthought, and it is the part a fast number for {name} quietly leaves out.",
            "Which means the job gets planned by elevation rather than by room. A builder "
            "finish on {an} {name} house lets go across a whole wall at once instead of in "
            "patches.",
            "It means the first repaint is the one that has to be prepped honestly, because "
            "the coat under it in {name} was sprayed once and never disturbed since.",
        ]
    return (pick(first, seed, "plain-age-a").format(**F) + " " +
            pick(second, seed, "plain-age-b").format(**F))


def plain_do_line(p, seed):
    """What we do, in the order this town actually needs it, plus the distance.

    The service list is real: it comes off service_order(), which is weighted by
    the housing. A rental-heavy town leads on repair and turnover, a large newer
    town leads on exteriors. The distance carries a decimal that exists on no
    other page, which is what stops this paragraph running together with the
    same paragraph on a town that drew the same phrasing.
    """
    ordered = service_order(p)
    top = [service_prose(s) for s in ordered[:3]]
    F = dict(name=p["name"], mi="%.1f" % p["mi"], street=STREET,
             a=top[0], b=top[1], c=top[2])
    # The home town is 0.0 miles from itself, and "our shop is 0.0 miles away"
    # is the kind of sentence a generator writes and a person never does.
    if p["mi"] < 0.05:
        return pick([
            "We do {a}, {b} and {c} in {name}, plus the repairs that have to happen before "
            "any of it. The shop is here, at {street}, so this is the one town on the site "
            "with no drive at all.",
            "In {name} that mostly means {a} and {b}, with {c} on the same visit often "
            "enough that splitting them wastes everyone's time. Our shop is on {street}, in "
            "the village.",
            # Not "service-area pin on a map": the home-town callout further
            # down this same page already uses that phrase, and this is the one
            # page where both blocks render.
            "The work we get called out to in {name} is {a}, {b} and {c}. We are based here, "
            "on {street}, so the village is not a place we drive out to.",
            "{a}, {b}, {c} and the making-good that comes first: that is the list in {name}. "
            "The shop is at {street}, in the village itself.",
        ], seed, "plain-do").format(**F)
    return pick([
        "We do {a}, {b} and {c} in {name}, plus the repairs that have to happen before any "
        "of it. Our shop is {mi} straight-line miles away, at {street} in Bridgeview.",
        "In {name} that mostly means {a} and {b}, with {c} on the same visit often enough "
        "that splitting them wastes everyone's time. We are {mi} straight-line miles away at "
        "{street} in Bridgeview.",
        "The work we get called out to in {name} is {a}, {b} and {c}. Our own shop is at "
        "{street} in Bridgeview, {mi} straight-line miles from you, not a franchise desk in "
        "another county.",
        "{a}, {b}, {c} and the making-good that comes first: that is the list in {name}. The "
        "shop is {mi} straight-line miles away at {street} in Bridgeview.",
    ], seed, "plain-do").format(**F)


def quick_answers(p, seed):
    """The four questions a homeowner actually arrived with, answered in one
    line each, in a list they can scan on a phone instead of a paragraph they
    have to read.

    THE ORDER IS FIXED AND IT IS NOT ROTATED. Every other selected block on a
    city page rotates on the slug, because rotation is cheap differentiation.
    This one must not. The order is the order somebody arrives in: can you do my
    job, what will it cost, what needs doing first, when can you come. The first
    build of this block did rotate it, and Brighton Park came out leading on
    "what usually needs doing first" above "can we do your job", which is
    answering the fourth question before the first. Differentiation is worth
    paying for, but not out of the reader's first ten seconds.

    The four bold labels are therefore identical on all 76 pages. That is about
    twenty words of shared text and the similarity audit swallows it without
    noticing. Every ANSWER carries something true of this town: the service
    order, the distance to the decimal, or the era.
    """
    ordered = service_order(p)
    n = p["name"]
    mi = "%.1f" % p["mi"]
    era = p["era"]
    # Three readings on each branch rather than one, each naming the town. The
    # single-reading version of this block cost two points of measured
    # similarity on its own, because "Usually the repairs. Cracked plaster,
    # failed caulk and loose paint..." was thirty identical words on all thirty
    # prewar and postwar towns at once. Variants are the price of a block that
    # appears on every page.
    if era in ("prewar", "postwar-50s"):
        driver = pick([
            "the state of the woodwork and the ceilings, because on housing this age that "
            "is where the hours go",
            "how much has already been painted onto the trim, because taking that back is "
            "most of the labor on " + _an(n) + " " + n + " interior",
            "condition rather than size: what has to come off or be made good in " + n +
            " before anything new goes on",
        ], seed, "qa-driver")
        firstjob = pick([
            "Usually the repairs. Cracked plaster, failed caulk and loose paint have to be "
            "sorted before anything gets a topcoat.",
            "In " + n + " it is normally the making-good: plaster that has opened up, "
            "windows painted shut, and trim that has lost its edge under old coats.",
            "The prep, almost always. On housing this age in " + n + " the ceilings and the "
            "woodwork decide the job, and both of them come before the first finish coat.",
        ], seed, "qa-first")
    elif era in ("60s-early-70s", "70s-early-80s"):
        driver = pick([
            "how much of the painted wood is up high, because reach costs more than wall "
            "area does",
            # These three say what the COST turns on. They deliberately do not
            # restate the fact that the wood is high up: plain_age_line() has
            # already said that one screen above, and a driver that repeats it
            # reads like the page forgot it had.
            "the ladder plan. Two " + n + " exteriors with the same square footage price "
            "differently depending on how the ground sits under them and what has to be "
            "reached from where",
            "the condition of the trim rather than the size of the house, because in " + n +
            " it is the wood that has been weathering and the masonry that has not",
        ], seed, "qa-driver")
        firstjob = pick([
            "Usually the soffit, fascia and gable ends. They fail years before the brick "
            "underneath them needs anything.",
            "In " + n + " it is the high trim: soffit, fascia, the gable and whatever sits "
            "over a split entry. That is what goes first and it is what nobody looks at.",
            "The wood above the masonry. On " + n + " houses the walls outlast the trim by "
            "a long way, so the trim is the job and the brick is not.",
        ], seed, "qa-first")
    else:
        driver = pick([
            "access and setup, because tall walls and two story entries are not room-rate "
            "work",
            # Deliberately NOT phrased as "staging is a real line on the quote".
            # plain_age_line() has a variant that says exactly that, and the two
            # blocks sit one screen apart, so Frankfort shipped the same
            # sentence twice inside ten lines.
            "height. Two story walls and open stair volumes take equipment and time to "
            "reach, and in " + n + " that is a bigger share of the day than the painting",
            "the state of the original builder finish, and how much staging it takes to "
            "reach it on " + _an(n) + " " + n + " house",
        ], seed, "qa-driver")
        firstjob = pick([
            "Usually the south and west elevations and the trim boards at the top of a two "
            "story wall. Those go first.",
            "In " + n + " it is the sun-facing walls and the high trim boards. A builder "
            "finish lets go there before it lets go anywhere else.",
            "The elevations that take the weather, then the entry and garage doors. On " +
            n + " housing that order is predictable enough to plan around.",
        ], seed, "qa-first")
    if p["mi"] < 0.05:
        # Does not restate where the shop is. `far` above has just said it, and
        # the first version put "The shop is in Bridgeview itself" twice inside
        # one bullet.
        when = ("Faster than anywhere else on this site, and it shows most on small work: "
                "a single wall or one bad ceiling is worth a look on its own here rather "
                "than being bundled into something bigger next month.")
    elif p["mi"] < 5:
        when = pick([
            "Quickly. " + n + " is inside the close ring, so a small job can fit into a gap "
            "in the week instead of waiting for a day big enough to absorb the driving.",
            "Soon. At this range " + n + " is close enough that one room, one ceiling or one "
            "bad door is worth a trip on its own, which is not true further out.",
            "Sooner than the size of the job would suggest. Nothing about the drive to " + n +
            " has to be scheduled around, so small work gets seen rather than deferred.",
        ], seed, "qa-when")
    elif p["mi"] < 10:
        when = pick([
            "Soon enough that looking at the work and doing the work do not have to be the "
            "same trip. Ask on the call and you will get a real date rather than a maybe.",
            "Straightforwardly, for most jobs. " + n + " is in the middle ring, so a "
            "walk-through costs nothing but a visit and the date comes off the call.",
            "Without much fuss. From here " + n + " is a normal run rather than an "
            "expedition, and the only thing worth flagging is whether the job is a single "
            "small item.",
        ], seed, "qa-when")
    else:
        when = pick([
            "Depends on the job. " + n + " is a genuine drive, so a full interior or a whole "
            "exterior is straightforward to schedule and one small patch on its own may not "
            "be. You will be told which.",
            "Ask before you plan around a date. " + n + " is out at the range where the size "
            "of the work and the week have to make sense together, and a straight no in "
            "advance beats a missed appointment.",
            "It depends on what the work is. At this distance " + n + " suits whole "
            "interiors, complete exteriors and remodeling. A single small repair usually "
            "does not justify the trip, and we will say so rather than pad the number.",
        ], seed, "qa-when")
    # Distance rides inside "when can you come", because a homeowner asking how
    # far away we are is really asking whether we will turn up. Splitting it
    # into its own row spent a line of a four-line block restating a mile
    # figure that is already in the paragraph above and in the chips below.
    # The street address is deliberately NOT repeated here. plain_do_line() gives
    # it one paragraph above and travel_section() gives it again further down,
    # and printing it a third time inside a four-line answer block made two
    # pages carry the same twelve-word run twice within a screen.
    if p["mi"] < 0.05:
        far = "The shop is in " + n + " itself, so there is no travel to price at all. "
    else:
        far = ("We are " + mi + " straight-line miles out, and travel is not a hidden line "
               "on a quote from us. ")
    rows = [
        ("Can we do your job?",
         " Almost certainly. In " + n + " it is " + service_prose(ordered[0]) + " and " +
         service_prose(ordered[1]) + " most weeks, plus the drywall, plaster and carpentry "
         "that goes underneath both."),
        ("What will it cost?",
         " There is no price list on this site, because there is no honest local one to "
         "publish yet. Every job is quoted after we walk it. What moves the number on " +
         _an(n) + " " + n + " house is " + driver + "."),
        ("What usually needs doing first?", " " + firstjob),
        ("When can you come?", " " + far + when),
    ]
    return "".join("<li><strong>" + h + "</strong>" + t + "</li>" for h, t in rows)


def next_step(p, seed, up):
    """The next step, high on the page instead of at the bottom of it.

    The hero form is above this and the CTA band is below it, but neither is
    inside the reading flow. Somebody who has just read two paragraphs and a
    list of answers is at the exact point of deciding, and the thing to do next
    should be in front of them there and not four screens down.
    """
    n = p["name"]
    # Short on purpose. There are two buttons directly underneath it and a form
    # at the top of the page, so this is a prompt, not a pitch.
    line = pick([
        "Call or text " + PHONE_DISPLAY + ", say where in " + n + " you are and what needs "
        "doing. Photos to the same number help.",
        "Quickest route to a real number: " + PHONE_DISPLAY + ". Tell us the rooms or the "
        "elevation and roughly what you want.",
        "Ring or text " + PHONE_DISPLAY + " and we will tell you what the job involves and "
        "when somebody can be in " + n + " to look at it.",
        "Say the room and roughly what you want on " + PHONE_DISPLAY + ". Every " + n +
        " job is quoted after we have stood in it, never off a website.",
    ], seed, "next-step")
    return ('<div class="callout"><h3>' +
            pick(["What to do next", "The next step", "How to get this looked at"],
                 seed, "next-step-h3") + '</h3><p>' + line + '</p>'
            '<div class="btnrow" style="margin-top:14px">'
            '<a class="btn" href="tel:' + PHONE_E164 + '">Call or text ' + PHONE_DISPLAY +
            '</a>'
            '<a class="btn btn-b" href="' + up + 'contact.html#quote">Send the details</a>'
            '</div></div>\n')


# ---- title and meta description --------------------------------------------

# Titles already spoken for by pages outside areas/. Two identical title tags
# on one site is a duplicate-content signal and seo_audit() fails on it,
# correctly. The set is filled in by main() rather than typed, so it cannot go
# stale. Bridgeview used to be carved out of this pool because the home page
# held "House Painters in Bridgeview, IL"; the home page is regional now, so
# the town draws from the pool like every other place.
TITLES_TAKEN = set()


def city_title(p, seed):
    """First pattern that fits inside TITLE_MAX and is not already in use.

    Uniqueness across the city pages comes from the place name, which is unique
    by definition. This only has to solve length and collisions with the rest of
    the site.
    """
    n = p["name"]
    where = n + ", IL" if p["kind"] == "town" else n + ", Chicago"
    cands = [
        "Painting Contractor in " + where + " | Colors Your Way",
        "House Painters in " + where + " | Colors Your Way USA",
        where + " Painting and Remodeling | Colors Your Way",
        "Painters in " + where + " | Colors Your Way USA",
        where + " Painters | Colors Your Way USA",
        where + " Painters | Colors Your Way",
    ]
    r = hnum(seed, "title") % 4
    ordered = cands[r:] + cands[:r]
    for c in ordered:
        if len(c) <= TITLE_MAX and c not in TITLES_TAKEN:
            TITLES_TAKEN.add(c)
            return c
    sys.exit("BUILD FAILED: no title pattern fits under " + str(TITLE_MAX) +
             " characters for " + n + ". Add a shorter pattern in city_title().")


def fit_desc(core, extras):
    """Pack a meta description into the DESC_MIN to DESC_MAX window.

    Greedy rather than clever: start with the sentences that have to be there,
    add optional ones while they fit, and fail the build loudly if the result
    lands outside the window. seo_audit() would catch it anyway, but failing
    here names the town instead of naming the file.
    """
    s = " ".join(core).strip()
    for e in extras:
        if len(s) >= DESC_MIN:
            break
        if len(s) + 1 + len(e) <= DESC_MAX:
            s = s + " " + e
    return s


def city_desc(p, seed):
    if p["slug"] == HOME_TOWN_SLUG:
        s = home_town_desc(p)
        if len(s) < DESC_MIN or len(s) > DESC_MAX:
            sys.exit("BUILD FAILED: the home town meta description came out " + str(len(s)) +
                     " chars, outside " + str(DESC_MIN) + " to " + str(DESC_MAX) +
                     ". Edit home_town_desc(). -> " + repr(s))
        return s
    n = p["name"]
    where = n + ", IL" if p["kind"] == "town" else n + " on Chicago's south side"
    age = (_pc(p["pre1980"]) + "% built before 1980" if p["pre1980"] is not None
           else _pc(p["pre1970"]) + "% built before 1970")
    lead = pick([
        "Interior and exterior painting in " + where + ".",
        "Painting and remodeling in " + where + ".",
        "House painting in " + where + ".",
        "Painting contractor covering " + where + ".",
    ], seed, 7)
    core = [lead, "Median build year " + str(p["medyr"]) + ", " + age + "."]
    # Ordered longest and most informative first, shortest filler last. fit_desc
    # walks the whole list and takes anything that still fits, so the tail exists
    # purely to close a gap of ten or twenty characters. Without short fragments
    # at the end a town like Justice lands at 137 and fails the window.
    # Reordered so the fragments a homeowner reads in a search result come
    # before the ones an analyst reads. Uniqueness is unaffected: it comes from
    # the town name in `lead` and the median build year in `core`, both of which
    # are always present.
    extras = [
        "%.1f" % p["mi"] + " miles from the Bridgeview shop.",
        "Owner run, not a franchise. Call " + PHONE_DISPLAY + ".",
        _n(p["own"]) + " owner households.",
        "Median " + _pc(p["rooms"]) + " rooms.",
        "Census sourced, no invented figures.",
        "Owner run, not a franchise.",
        "Call " + PHONE_DISPLAY + ".",
        _pc(p["own_pct"]) + "% owner occupied.",
        "Bridgeview based.",
    ]
    s = fit_desc(core, extras)
    if len(s) < DESC_MIN or len(s) > DESC_MAX:
        sys.exit("BUILD FAILED: meta description for " + n + " came out " + str(len(s)) +
                 " chars, outside " + str(DESC_MIN) + " to " + str(DESC_MAX) +
                 ". Adjust the fragments in city_desc(). -> " + repr(s))
    return s


def city_h1(p, seed):
    where = p["name"] + ", IL" if p["kind"] == "town" else p["name"] + ", Chicago"
    return pick([
        "Painting and remodeling in " + where + ".",
        "Owner run house painting in " + where + ".",
        "Interior and exterior painting in " + where + ".",
        "Painting contractor for " + where + ".",
    ], seed, 8)


# =============================================================================
# CITY PAGES: THE BUILDERS
# =============================================================================

CITY_DIR = "areas"
CITY_HERO_KEYS = ["hero-interior", "hero-exterior", "hero-service-area", "hero-home",
                  "hero-drywall", "hero-remodeling", "hero-cabinets"]

# The wrapper the similarity audit measures. Only the town-specific prose is
# inside it. The header, the quote form, the CTA and the footer are identical on
# every page of the site by design and measuring them would hide exactly the
# duplication this check exists to find.
#
# The markers are HTML COMMENTS, not the div tags themselves. The first version
# split the page on '</div>' and silently stopped at the first callout box
# inside the body, so roughly half of every city page was never audited at all.
# A check that quietly measures the wrong region is worse than no check, because
# it reports a pass. These comments cannot nest and no other part of the page
# emits them.
BODY_MARK_OPEN = "<!-- city-body: the region the anti-doorway audit measures -->"
BODY_MARK_CLOSE = "<!-- /city-body -->"
BODY_OPEN = BODY_MARK_OPEN + '\n<div class="city-body">\n'
BODY_CLOSE = '</div>\n' + BODY_MARK_CLOSE + '\n'


def city_url(p):
    return CITY_DIR + "/" + p["slug"] + ".html"


def build_city(p, posts=()):
    fn = city_url(p)
    up = "../"
    seed = p["slug"]
    F = dict(name=p["name"], mi="%.1f" % p["mi"])
    where = p["name"] + ", IL" if p["kind"] == "town" else p["name"] + ", Chicago"
    cite = CENSUS_CITE_PLACES if p["kind"] == "town" else CENSUS_CITE_CCA

    # ---- fact chips, straight off the row ---------------------------------
    chips = ['<li><span class="k">Median build year</span><span class="v">' +
             str(p["medyr"]) + "</span></li>"]
    if p["kind"] == "town":
        chips.append('<li><span class="k">Built before 1980</span><span class="v">' +
                     _pc(p["pre1980"]) + "%</span></li>")
    chips.append('<li><span class="k">Built before 1970</span><span class="v">' +
                 _pc(p["pre1970"]) + "%</span></li>")
    chips.append('<li><span class="k">Owner households</span><span class="v">' +
                 _n(p["own"]) + "</span></li>")
    chips.append('<li><span class="k">Renter households</span><span class="v">' +
                 _n(p["rent"]) + "</span></li>")
    chips.append('<li><span class="k">Owner occupied</span><span class="v">' +
                 _pc(p["own_pct"]) + "%</span></li>")
    if p["medval"]:
        chips.append('<li><span class="k">Median home value</span><span class="v">' +
                     _money(p["medval"]) + "</span></li>")
    chips.append('<li><span class="k">Median rooms</span><span class="v">' +
                 _pc(p["rooms"]) + "</span></li>")
    chips.append('<li><span class="k">Detached houses</span><span class="v">' +
                 _pc(p["sfd"]) + "%</span></li>")
    chips.append('<li><span class="k">In buildings of 2+</span><span class="v">' +
                 _pc(p["multi"]) + "%</span></li>")
    chips.append('<li><span class="k">Straight-line from the shop</span><span class="v">' +
                 ("in town" if p["mi"] < 0.05 else F["mi"] + " mi") + "</span></li>")

    # ---- section: the homeowner opening -----------------------------------
    # This block did not exist before. It is the answer, in plain English, and
    # it is first. The measured material that used to occupy this position is
    # unchanged and now sits under "the numbers behind this page" at the foot.
    # Kept deliberately clear of the services H2 pool below, which owns "What we
    # do in {name}". The first draft had both, and Brighton Park shipped with
    # "What we do for houses in Brighton Park" and "What we do in Brighton Park"
    # two screens apart, which reads like a page that lost its place.
    open_h2 = pick(["Start here if you own a house in " + p["name"],
                    "Your house in " + p["name"] + ", and what we would do with it",
                    "The short version for " + p["name"] + " homeowners",
                    "What we can do at your place in " + p["name"]], seed, "open-h2")
    opener = ('<h2>' + open_h2 + '</h2>\n'
              '<p>' + plain_age_line(p, seed) + "</p>\n"
              '<p>' + plain_do_line(p, seed) + "</p>\n"
              '<h3>' + pick(["The four questions people actually call about",
                             "Answered before you have to ask",
                             "The short answers"], seed, "quick-h3") + '</h3>\n'
              '<ul class="notes">' + quick_answers(p, seed) + "</ul>\n" +
              next_step(p, seed, up))

    # The home town's page says the one thing no other page on this site can
    # say: the shop is in this town. It used to sit inside the Census block at
    # the top of the page, which is the wrong place for it now that the top of
    # the page belongs to the homeowner. It is proximity, so it goes with the
    # opening.
    if p["slug"] == HOME_TOWN_SLUG:
        opener += ('<div class="callout"><h3>This is the town the shop is in</h3>'
                   '<p>' + STREET + ', Bridgeview. It is a working address, not a franchise '
                   'office in another county and not a service-area pin dropped on a map, and '
                   'it is the reason a small repair in the village is worth looking at the '
                   'same week rather than being bundled into next month. Every other page on '
                   'this site measures its distance from this one place.</p>'
                   '<p>Being based here does not make the housing simple. More of Bridgeview '
                   'is manufactured housing than any other place on this site, and that is a '
                   'genuinely different job from a site-built house: different substrate, '
                   'different primer, different price. Ask any contractor quoting you here '
                   'which of the two they are pricing. The share, the median build year and '
                   'the pre-1980 figure behind that are all further down this page.</p>'
                   '</div>\n')

    # ---- section: the numbers, moved down ---------------------------------
    # NOTHING WAS REMOVED HERE. Every chip, every paragraph and every citation
    # that used to open the page is still on it, in the same words, in this
    # block. What changed is its position and the heading over it. It is the
    # evidence for the plain-English claims above, and that is where evidence
    # belongs on a page a homeowner is reading on a phone.
    outliers = outlier_sentences(p, seed)
    stock_h2 = pick(["Where these figures come from",
                     "The housing in " + p["name"] + ", in numbers",
                     "The data behind everything above",
                     p["name"] + " housing, by the published figures"], seed, 9)
    stock = ('<h2>' + stock_h2 + '</h2>\n'
             # One short line, not a paragraph. The first draft explained at
             # length why the data had moved down the page, which is a note to
             # whoever edits this file dressed up as copy. The reader needs to
             # know these are the receipts and nothing else.
             '<p class="src">' + pick([
                 "The working behind everything above, with the source named at the "
                 "bottom.",
                 "Every claim higher up this " + p["name"] + " page comes out of these "
                 "figures.",
                 "The published numbers behind all of that, and where they came from.",
             ], seed, "stock-intro") + "</p>\n"
             '<ul class="chips">' + "".join(chips) + "</ul>\n"
             '<p>' + age_para(p, seed) + "</p>\n"
             '<p>' + tenure_para(p, seed) + "</p>\n")
    if outliers:
        stock += '<p>' + " ".join(outliers[:3]) + "</p>\n"
    stock += "<p>" + divergence_sentences(p, seed) + "</p>\n"
    stock += ('<p class="src">Source: ' + cite + ' ' + CENSUS_MARK + '</p>\n')

    # ---- section: what that means for the work ----------------------------
    # H2s are written as questions a homeowner would type or ask out loud. The
    # old set was descriptive and analytical ("How the age of the stock changes
    # the work here"), which is a heading for somebody studying the town rather
    # than somebody who owns a house in it.
    means_h2 = pick(["What decides the price of a job in " + p["name"],
                     "Why two quotes for the same " + p["name"] + " house come out different",
                     "What we look at before we price the work",
                     "The parts of " + _an(p["name"]) + " " + p["name"] +
                     " quote that actually move"], seed, 10)
    notes = "".join("<li><strong>" + h + "</strong>" + t + "</li>"
                    for h, t in estimate_notes(p, seed))
    means = ('<h2>' + means_h2 + '</h2>\n'
             '<p>' + trade_para(p, seed) + "</p>\n"
             '<h3>' + pick(["What an estimate here has to account for",
                            "What should be on a written quote in " + p["name"],
                            "The lines a quote for " + p["name"] + " needs to show"],
                           seed, "notes-h3") + '</h3>\n'
             '<ul class="notes">' + notes + "</ul>\n"
             '<div class="callout"><h3>What the housing here is likely made of</h3>'
             '<p>Most of it is ' + structure_note(p) + '.</p>'
             '<p>' + pick([
                 "That reading comes from two numbers on this page and nothing else: a "
                 "median build year of " + str(p["medyr"]) + " and a structure split of " +
                 _pc(p["sfd"]) + " percent detached, " + _pc(p["sfa"]) + " percent attached "
                 "and " + _pc(p["multi"]) + " percent in buildings of two or more.",
                 "It is read off exactly two things: the " + str(p["medyr"]) + " median "
                 "build year, and the split between " + _pc(p["sfd"]) + " percent detached "
                 "houses, " + _pc(p["sfa"]) + " percent attached homes and " +
                 _pc(p["multi"]) + " percent in buildings of two units or more.",
                 "Two figures produce that sentence and no others: build year " +
                 str(p["medyr"]) + ", and a stock that is " + _pc(p["sfd"]) + " percent "
                 "detached, " + _pc(p["sfa"]) + " percent attached and " + _pc(p["multi"]) +
                 " percent in buildings of two or more.",
             ], seed, "structure-basis") + '</p>'
             '<p class="ph-note">' + pick([
                 "An inference, not a measurement. Neither the Census nor the regional "
                 "housing data records what a wall in " + p["name"] + " is made from, so no "
                 "percentage is attached to it and none should be. Your own elevation "
                 "settles it in four seconds from the sidewalk.",
                 "That is inference and it is labeled as one. Wall material in " + p["name"] +
                 " is not collected by any source behind this page, so there is no honest "
                 "figure to put on it. Look at your own house and you will know more than "
                 "this paragraph does.",
                 "Read it as a starting assumption rather than a finding. No public dataset "
                 "records what the walls in " + p["name"] + " are made from, so attaching a number to "
                 "it would mean inventing one. The house itself answers faster than any "
                 "table can.",
                 "Inference, and worth saying so. Wall material in " + p["name"] + " is not "
                 "in the Census tables or the regional data, which is why that sentence "
                 "carries no number when everything else here does.",
             ], seed, "structure-note") + '</p></div>\n')

    # ---- section: lead-safe ------------------------------------------------
    rrp_h2, rrp_body = rrp_section(p, seed)
    rrp = '<h2>' + rrp_h2 + '</h2>\n' + "".join("<p>" + b + "</p>\n" for b in rrp_body)
    rrp += ('<p class="ph-note">' + pick([
        "This site does not claim EPA lead-safe firm certification. No number has been "
        "supplied, so the trust panel below shows it as pending. Ask for it directly, from "
        "anyone quoting work in " + p["name"] + ".",
        "No lead-safe certification is claimed anywhere on this site, because no number has "
        "been provided to put here. The panel below leaves the slot open on purpose, in " +
        p["name"] + " and everywhere else. Ask any contractor for theirs.",
        "Nothing on this page should be read as a certification claim. The slot for it below "
        "is empty because it has not been supplied, and an empty slot is more use to "
        "a homeowner in " + p["name"] + " than a filled-in one nobody checked.",
        "Certification is a document, not a sentence on a website. It shows as pending below "
        "because no number has been supplied. Ask to see it, in " + p["name"] + " and "
        "everywhere else.",
    ], seed, "rrp-note") + "</p>\n")

    # ---- section: contrast with the nearest place --------------------------
    cp = contrast_para(p, seed)
    contrast = ""
    if cp:
        c_h2 = pick(["The next town over is not the same job",
                     "Why we do not quote " + p["name"] + " off a regional average",
                     "Why the town line matters here",
                     "The place closest to " + p["name"] + ", and how it differs"], seed, 11)
        contrast = '<h2>' + c_h2 + '</h2>\n<p>' + cp + "</p>\n"
        if len(outliers) > 3:
            contrast += "<p>" + " ".join(outliers[3:9]) + "</p>\n"

    # ---- section: services -------------------------------------------------
    ordered = service_order(p)
    svc_rows = ""
    for s in ordered:
        why = service_reason(p, s)
        svc_rows += ('<li><h3><a href="' + up + s["slug"] + '.html">' + s["card"] +
                     ' in ' + p["name"] + "</a></h3><p>" + why + "</p></li>")
    svc_h2 = pick(["What we do in " + p["name"],
                   "The jobs we get called out to here, most first",
                   "Work we take on in " + p["name"],
                   "What houses in " + p["name"] + " usually need"], seed, 12)
    services = ('<h2>' + svc_h2 + '</h2>\n<ul class="reads">' + svc_rows + "</ul>\n")

    # ---- section: travel ---------------------------------------------------
    # The scale sentence used to hang off the END of the tail. It sits BETWEEN
    # the two paragraphs now, and the position is doing real work: it names the
    # nearest place, the distance to it and the county, so it is unique to this
    # town by construction. Two towns that happen to draw the same lead AND the
    # same tail therefore still cannot produce one long shared run, because a
    # sentence that exists on no other page is wedged in the middle of it.
    t_lead, t_tail = travel_section(p, seed)
    nb1 = neighbors(p, 1)
    t_mid = ""
    if nb1:
        t_mid = ("For scale, the nearest other place on this site is " + nb1[0]["name"] +
                 ", " + ("%.1f" % _hav(p, nb1[0])) + " miles from " + p["name"] + ", and "
                 + p["name"] + " sits in " + p["county"] + " County.")
    t_h2 = pick(["How soon can we get to " + p["name"] + "?",
                 "Do you actually come out to " + p["name"] + "?",
                 "Scheduling, and how far " + p["name"] + " really is",
                 "The drive, and what it means for a small job"], seed, 13)
    travel = ('<h2>' + t_h2 + '</h2>\n<p>' + t_lead + "</p>\n" +
              ("<p>" + t_mid + "</p>\n" if t_mid else "") +
              "<p>" + t_tail + "</p>\n")

    # ---- order the page ----------------------------------------------------
    # THE INVERSION. The old page ran: Census block, then five sections in one of
    # six orders. A homeowner therefore met a median build year before they met
    # a service. The new order answers the four questions somebody actually
    # arrives with, then shows the working:
    #
    #   opener    can you do my job, what moves the cost, how far, when   (new)
    #   services  what we do here, ordered by what this housing needs
    #   means     what decides the price on a house this age
    #   rrp       the lead-paint question, in plain English
    #   travel    how soon we can get there
    #   stock     the figures and the citation, as supporting evidence
    #   contrast  how the nearest place differs, on the numbers
    #
    # The six orderings survive, because varying the structure is one of the
    # anti-doorway requirements and dropping it would cost real differentiation.
    # What is constrained now is the top: `services` is always first or second,
    # so the answer to "can you do my job" is never below the fold. The data
    # block is always last, because that is the point of the rewrite.
    parts = dict(means=means, rrp=rrp, services=services, travel=travel)
    orders = [
        ["services", "means", "rrp", "travel"],
        ["services", "rrp", "means", "travel"],
        ["means", "services", "rrp", "travel"],
        ["services", "means", "travel", "rrp"],
        ["rrp", "services", "means", "travel"],
        ["services", "travel", "means", "rrp"],
    ]
    body = opener + "".join(parts[k] for k in pick(orders, seed, 14)) + stock + contrast

    # ---- the hand-written note, where one exists ---------------------------
    ed = EDITORIAL.get(p["slug"])
    if ed:
        body += ('<div class="callout"><h3>From the shop</h3><p>' + ed + "</p></div>\n")

    # ---- nearby places and further reading ---------------------------------
    nb = neighbors(p, 4)
    nb_links = "".join('<a class="pill" href="' + q["slug"] + '.html">' + city_anchor(q) +
                       ' <span class="mi">' + ("%.1f" % _hav(p, q)) + ' mi</span></a>'
                       for q in nb)
    near_h2 = pick(["Nearby, and genuinely nearby",
                    "Places next to " + p["name"],
                    "The towns and neighborhoods around " + p["name"]], seed, 15)
    body += ('<h2>' + near_h2 + '</h2>\n'
             '<p>' + pick([
                 "The four closest places on this site to " + p["name"] + ", at " +
                 ", ".join("%.1f" % _hav(p, q) for q in nb) + " miles, measured from the "
                 "same centroids the distance column uses. They are here because they are "
                 "next door, not because a list needed filling.",
                 "Nearest to " + p["name"] + " on this site, in order: " +
                 ", ".join(q["name"] + " at " + ("%.1f" % _hav(p, q)) + " miles"
                           for q in nb) + ". Real adjacency, computed from centroids rather "
                 "than chosen to fill a row.",
                 "Inside " + ("%.1f" % _hav(p, nb[-1])) + " miles of " + p["name"] +
                 " there are four other places covered here: " +
                 ", ".join(q["name"] for q in nb) + ". Each of them reads differently, "
                 "because each of them was built differently.",
             ], seed, "nearby") + "</p>\n"
             '<div class="pills">' + nb_links + "</div>\n")

    # The two posts get a reason written from THIS town's figures rather than the
    # post's own summary. Printing the summary meant any two towns that picked the
    # same two posts carried an identical eighty-word block, which is real shared
    # mass and the doorway audit counted it, correctly. The reason is also more
    # use to the reader: it says why this post and this town.
    cp_posts = city_posts(p, posts, seed)
    if cp_posts:
        rows = ""
        for post in cp_posts:
            rows += ('<li><h3><a href="' + up + "blog/" + post["slug"] + '.html">' +
                     esc(str(post["title"])) + "</a></h3><p>" +
                     post_reason(p, post["slug"]) + "</p></li>")
        body += ('<h2>' + pick(["Worth reading before you call",
                                "Written with housing like this in mind",
                                "Before you get anything quoted"], seed, "reads-h2") +
                 '</h2>\n<ul class="reads">' + rows + "</ul>\n")

    body += ('<p class="src"><a href="index.html">All ' + str(len(built_places())) +
             ' places we cover</a> &middot; <a href="' + up + 'contact.html#quote">Send the '
             'details for ' + p["name"] + "</a></p>\n")

    # ---- assemble ----------------------------------------------------------
    title = city_title(p, seed)
    desc = city_desc(p, seed)
    faqrows, faqld = faq(city_faq(p, seed))
    crumb_html, crumb_ld = breadcrumbs(
        [("Home", "index.html"), ("Areas", CITY_DIR + "/index.html"), (where, fn)], up)
    herokey = pick(CITY_HERO_KEYS, seed, 16)

    html = head(title, desc, fn, herokey, up=up)
    html += header(CITY_DIR + "/index.html", up)
    html += '<main id="main">\n' + crumb_html
    # The lede is the first sentence a homeowner reads, and it used to be
    # written for somebody auditing the page. One variant said "Numbers first,
    # sales second" out loud. It is the answer first now. The lede sits OUTSIDE
    # the region doorway_audit() measures, so these are free to be plain.
    html += hero(city_h1(p, seed),
                 pick(["Inside, outside, cabinets, drywall and the repairs that come first, "
                       "for houses in " + where + ". Owner run, quoted after we walk the "
                       "job, and you get a real answer on the call.",
                       "We paint houses in " + p["name"] + " and fix what has to be fixed "
                       "before the paint goes on. Tell us the rooms and roughly what you "
                       "want, and you will know what happens next.",
                       "Painting and remodeling for " + where + ": what we do, what it "
                       "usually takes on a house around here, and how soon somebody can come "
                       "and look at it.",
                       "House painting and repair in " + where + ", from an owner-run shop "
                       "in Bridgeview. What we do, what moves the price, and how to get "
                       "a number without a sales visit."],
                      seed, 17),
                 "Service area &middot; " + where, herokey,
                 "Get " + p["name"] + " looked at",
                 "Tell us the address, the rooms and roughly what you want.",
                 page=where + " (" + fn + ")", up=up)

    html += ('<section>\n  <div class="wrap narrow">\n' + BODY_OPEN + body + BODY_CLOSE +
             '  </div>\n</section>\n')
    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Questions</p>\n    <h2>Asked about ' + p["name"] +
             '</h2>\n    ' + faqrows +
             '    <p class="eyebrow" style="margin-top:2rem">What is confirmed, and what is '
             'not</p>\n    ' + trust_row(up) + "\n  </div>\n</section>\n")
    html += cta(up)
    html += "</main>\n" + footer(up)

    svc_ld = {
        "@type": "Service",
        "@id": canonical_url(fn) + "#service",
        "name": "Painting and remodeling in " + where,
        "description": ("Interior and exterior painting, cabinet refinishing, drywall repair "
                        "and remodeling in " + where + ", from a Bridgeview based contractor."),
        "serviceType": "House painting",
        "url": canonical_url(fn),
        "provider": {"@id": SITE + "/#business"},
        "areaServed": ({"@type": "City", "name": p["name"] + ", IL"} if p["kind"] == "town"
                       else {"@type": "Place", "name": p["name"] + ", Chicago, IL",
                             "containedInPlace": {"@type": "City", "name": "Chicago, IL"}}),
        "audience": {"@type": "Audience",
                     "audienceType": "Homeowners, landlords and property managers"},
    }
    html += ld_json([webpage_ld(fn, title, desc), svc_ld, faqld, crumb_ld])
    html += confirm_comment() + "</body>\n</html>\n"
    write(fn, html)
    return fn


def build_areas_hub():
    """The hub. Groups every built place by distance band and links all of them.

    This replaces the old single service-area.html, which carried 27 towns as
    accordion blocks on one page. That page could not grow: at 76 places it
    would have been a 40,000 word scroll with one title tag, competing with
    itself for every town name on it.
    """
    fn = CITY_DIR + "/index.html"
    up = "../"
    places = built_places()
    groups = ""
    for key, label, blurb in REGIONS:
        rows = places_in_region(key)
        if not rows:
            continue
        cards = ""
        for q in rows:
            # One plain sentence per town, not a row of statistics. The figures
            # are still real and still on the town's own page. What this line
            # has to do is answer "is my town on here and how far away are
            # they", which is the only question anybody brings to a hub page.
            age = (_pc(q["pre1980"]) + " percent of it before 1980" if q["pre1980"] is not None
                   else _pc(q["pre1970"]) + " percent of it before 1970")
            where = ("This is where our shop is." if q["slug"] == HOME_TOWN_SLUG
                     else ("%.1f" % q["mi"]) + " miles from the shop.")
            cards += ('<li><h4><a href="' + q["slug"] + '.html">' + city_anchor(q) + "</a></h4>"
                      "<p>" + where + " Most of it went up around " + str(q["medyr"]) +
                      ", and " + age + ".</p></li>")
        groups += ('<h3 id="' + key + '">' + label + "</h3>\n<p>" + blurb + "</p>\n"
                   '<ul class="reads areas-list">' + cards + "</ul>\n")

    faqrows, faqld = faq([
      ("My town is not on the list. Does that mean no?",
       "It means ask. The list is the service area the owner has confirmed, and no town goes "
       "on this site as a promise before he makes it. If you are just outside it, call "
       + PHONE_DISPLAY + " and you will get a straight yes or no on the phone rather than a "
       "salesman driving out to find out."),
      ("Do you actually work in Chicago, or is that just on the website?",
       "The city is real work and it is the south and southwest sides. Bridgeview is a short "
       "run from Garfield Ridge, Clearing, Ashburn, Beverly and Mount Greenwood, and that "
       "housing is the same brick and plaster as the inner suburbs, so it is the same job. "
       "What we will not pretend is that we cover the whole city. A north side call is better "
       "served by somebody on the north side, and you will hear that on the phone rather than "
       "after a missed appointment."),
      ("Why does every town page talk about how old the houses are?",
       "Because it is the most useful thing to know before anybody quotes, and it is the thing "
       "most quotes skip. Around here, older usually means plaster instead of drywall, deeper "
       "trim to cut in, windows that have been painted a dozen times, and paint from before "
       "1978 underneath it all. Newer usually means big two story walls and tall entries that "
       "need staging. Same word, painting, and completely different jobs."),
      ("Where do the numbers on these pages come from?",
       "Suburbs and towns come from the U.S. Census Bureau American Community Survey 5-year "
       "estimates for 2019 to 2023. Chicago neighborhoods come from the Chicago Metropolitan "
       "Agency for Planning Community Data Snapshots, which draw on the 2024 survey. "
       "Community areas are used rather than ZIP codes because a single southwest side ZIP "
       "covers three different neighborhoods, and a page built on it would be describing an "
       "average of places that have nothing in common. Every figure is a fact about the "
       "place, not a price for work."),
      ("Do you cover the west suburbs?",
       "Not on this site, and that is deliberate rather than an oversight. The confirmed "
       "service area is Chicago plus the south and southwest suburbs. Berwyn, Cicero, "
       "Riverside, Brookfield, La Grange and Oak Park have been researched and are ready to "
       "add, but a page claiming coverage of a town is a promise, and no promise goes on "
       "this site before the owner makes it. If you are west and want the work looked at, "
       "call and ask."),
    ])
    crumb_html, crumb_ld = breadcrumbs([("Home", "index.html"), ("Areas", fn)], up)
    n = len(places)
    title = "Service Areas, Chicago South and Southwest | Colors Your Way"
    desc = ("Painting and remodeling across " + str(n) + " towns and Chicago neighborhoods, "
            "south and southwest of the shop. Each read off its own published housing data.")
    html = head(title, desc, fn, "hero-service-area", up=up)
    html += header(fn, up)
    html += '<main id="main">\n' + crumb_html
    html += hero("Find your town. We cover Chicago and the south suburbs.",
                 "We paint and remodel across Chicago and the south and southwest suburbs, "
                 + str(n) + " towns and neighborhoods in all. They are grouped below by how far "
                 "they are from our shop in Bridgeview, so start with the group yours is in. If "
                 "you cannot find it, call " + PHONE_DISPLAY + " and ask rather than assuming.",
                 "Service area &middot; Chicago and the south suburbs", "hero-service-area",
                 "Check your town", "Tell us where you are and what needs doing.",
                 page="Service areas (" + fn + ")", up=up)
    html += ('<section>\n  <div class="wrap">\n'
             '    <div class="callout" style="margin-top:0"><h2>How to use this page</h2>'
             '<p>Everything below is sorted by distance from our shop at ' + STREET + ' in '
             'Bridgeview, which sits about where the city stops and the southwest suburbs '
             'start. The closer you are, the easier it is to get a small job looked at on its '
             'own. Further out, a whole interior or a full exterior is straightforward and '
             'anything smaller is worth a quick phone call first.</p>'
             '<p>Every town has its own page, and it says what the houses there are usually '
             'like: how old they are, what that means for the trim and the windows, and what '
             'tends to push a quote up or down. A 1941 street in Beverly and a 2000 '
             'subdivision in Frankfort are not the same job, and treating them as one is how '
             'quotes go wrong.</p></div>\n'
             + BODY_OPEN + groups + BODY_CLOSE +
             '    <p class="src">Housing figures on this page and on every town page are '
             'from two sources, named on each page: the ' + CENSUS_CITE_PLACES +
             ' for suburbs and towns, and the ' + CENSUS_CITE_CCA + ' for Chicago community '
             'areas. ' + CENSUS_MARK + "</p>\n"
             '  </div>\n</section>\n')
    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Questions</p>\n'
             '    <h2>About where we work</h2>\n    '
             + faqrows + "  </div>\n</section>\n")
    html += cta(up)
    html += "</main>\n" + footer(up)
    html += ld_json([webpage_ld(fn, "Service areas, " + BRAND, desc), faqld, crumb_ld])
    html += confirm_comment() + "</body>\n</html>\n"
    write(fn, html)
    return fn


# =============================================================================
# ANTI-DOORWAY AUDIT
# =============================================================================
# The check that decides whether this section of the site is allowed to exist.
#
# Google's spam policy on doorways is about pages "created to rank for similar
# search queries" that lead users "to intermediate pages that are not as useful
# as the final destination". In practice the machine-detectable version is
# near-duplicate body text across a set of URLs that differ by one noun. So that
# is what is measured, on the town-specific prose only, and it FAILS the build.
#
# Two independent measures, because they catch different failures:
#
#   1. Jaccard similarity over 8-word shingles. Catches two pages that are
#      broadly the same text. Symmetric, so it is fair between pages of
#      different length.
#   2. Containment: the share of one page's shingles that also appear on
#      another. Catches a short page that is entirely a subset of a long one,
#      which Jaccard scores low and Google does not.
#
# Plus the floor: every city page must contain at least one full sentence that
# appears on no other city page. A page with nothing of its own has no reason
# to exist as a separate URL, and that is the honest test, not a percentage.

SIM_SHINGLE = 8
SIM_JACCARD_MAX = 0.28
SIM_CONTAIN_MAX = 0.42

_TAGSTRIP = re.compile(r"<(script|style)\b.*?</\1>|<[^>]+>", re.S | re.I)


def _body_region(html):
    """The measured region, or "" when the markers are missing.

    Missing markers are reported as a failure by doorway_audit() rather than
    silently treated as an empty page: "no body found" and "body is empty" are
    the same value here and only one of them is safe to pass.
    """
    if BODY_MARK_OPEN not in html or BODY_MARK_CLOSE not in html:
        return ""
    return html.split(BODY_MARK_OPEN, 1)[1].split(BODY_MARK_CLOSE, 1)[0]


def _visible(html):
    body = _body_region(html)
    if not body:
        return ""
    txt = _TAGSTRIP.sub(" ", body)
    txt = _unescape(txt).lower()
    txt = re.sub(r"[^a-z0-9 ]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _shingles(txt, n=SIM_SHINGLE):
    w = txt.split()
    return set(tuple(w[i:i + n]) for i in range(max(0, len(w) - n + 1)))


def _sentences(html):
    body = _body_region(html)
    if not body:
        return []
    txt = _unescape(_TAGSTRIP.sub(" ", body))
    txt = re.sub(r"\s+", " ", txt)
    out = []
    for s in re.split(r"(?<=[.?!])\s+", txt):
        s = s.strip().lower()
        if len(s.split()) >= 8:
            out.append(re.sub(r"[^a-z0-9 ]+", "", s))
    return out


def doorway_audit(city_files):
    """Returns (problems, worst_jaccard, worst_containment)."""
    problems = []
    docs = {}
    sents = {}
    for f in city_files:
        html = io.open(os.path.join(HERE, f), encoding="utf-8").read()
        key = f.replace(os.sep, "/")
        txt = _visible(html)
        if not txt:
            problems.append(key + ": no measurable body text. The similarity audit could not "
                                  "find the city-body wrapper, so it cannot certify this page "
                                  "is not a duplicate.")
            continue
        docs[key] = _shingles(txt)
        sents[key] = set(_sentences(html))

    keys = sorted(docs)
    worst_j = (0.0, "", "")
    worst_c = (0.0, "", "")
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = docs[keys[i]], docs[keys[j]]
            inter = len(a & b)
            if not inter:
                continue
            jac = inter / float(len(a | b))
            if jac > worst_j[0]:
                worst_j = (jac, keys[i], keys[j])
            for x, y in ((a, keys[i]), (b, keys[j])):
                con = inter / float(len(x))
                if con > worst_c[0]:
                    other = keys[j] if y == keys[i] else keys[i]
                    worst_c = (con, y, other)
            if jac > SIM_JACCARD_MAX:
                problems.append("DOORWAY RISK: " + keys[i] + " and " + keys[j] + " share " +
                                ("%.0f%%" % (jac * 100)) + " of their body text (limit " +
                                ("%.0f%%" % (SIM_JACCARD_MAX * 100)) + "). Two location "
                                "pages this alike are a doorway pair. Give one of them "
                                "genuinely different material.")

    for k in keys:
        others = set()
        for o in keys:
            if o != k:
                others |= sents[o]
        unique = sents[k] - others
        if not unique:
            problems.append(k + ": not one sentence on this page is absent from every other "
                                "city page. A page with nothing of its own does not need to "
                                "be its own URL.")

    if worst_c[0] > SIM_CONTAIN_MAX:
        problems.append("DOORWAY RISK: " + ("%.0f%%" % (worst_c[0] * 100)) + " of " +
                        worst_c[1] + " also appears on " + worst_c[2] + " (limit " +
                        ("%.0f%%" % (SIM_CONTAIN_MAX * 100)) + "). One page being a subset "
                        "of another is the version of this Google catches and Jaccard "
                        "does not.")
    return problems, worst_j, worst_c


# =============================================================================
# MAIN
# =============================================================================

def main():
    os.chdir(HERE)
    write("style.css",
          "/* Generated by build.py. Do not hand-edit. */\n"
          "/* The critical subset of this file is inlined in every page head, so\n"
          "   the fold renders without waiting on this request. */\n"
          + CRITICAL_CSS + REST_CSS)
    write("app.js", "/* Generated by build.py. Do not hand-edit. */\n" + APP_JS)
    write("logo.svg", LOGO_SVG)
    write(".nojekyll", "")

    posts = discover_posts()
    pages = [build_home(posts)]
    pages += [build_service(s, posts) for s in SERVICES]
    pages += [build_areas_hub()]
    # Claim the title tags already in use before generating 76 more. Read back
    # from the files rather than from a hand-kept list, so a title edited on a
    # service page cannot silently collide with a town page six months later.
    for f in pages:
        head_html = io.open(os.path.join(HERE, f), encoding="utf-8").read().split("</head>", 1)[0]
        t = _tag(head_html, r"<title>(.*?)</title>")
        if t:
            TITLES_TAKEN.add(_unescape(t))
    city_pages = [build_city(p, posts) for p in built_places()]
    pages += city_pages
    pages += [build_service_area(), build_contact()]
    pages += [build_blog(posts)] + [build_post(p, posts) for p in posts]

    # Built and audited like every other page, but kept out of the sitemap.
    # It is permanently noindex, so listing it would be telling Google to crawl
    # a URL we have already told Google to drop.
    pages.append(build_thankyou())

    build_sitemap([p for p in pages if p != "thank-you.html"], posts)
    build_robots()

    print("built %d pages:" % len(pages))
    for p in pages:
        if p.replace(os.sep, "/").startswith(CITY_DIR + "/" ) and p != CITY_DIR + "/index.html":
            continue
        print("  %-32s %6d bytes" % (p, os.path.getsize(os.path.join(HERE, p))))
    city_bytes = sum(os.path.getsize(os.path.join(HERE, c)) for c in city_pages)
    print("  %-32s %6d bytes  (%d pages, avg %d)"
          % (CITY_DIR + "/<place>.html", city_bytes, len(city_pages),
             city_bytes // max(1, len(city_pages))))
    print("  %-32s %6d bytes" % ("style.css", os.path.getsize("style.css")))
    print("  %-32s %6d bytes" % ("app.js", os.path.getsize("app.js")))
    print("  blog posts found: %d" % len(posts))
    print("  places covered:   %d (%d towns, %d Chicago community areas)"
          % (len(built_places()),
             len([x for x in built_places() if x["kind"] == "town"]),
             len([x for x in built_places() if x["kind"] == "nbhd"])))

    door, worst_j, worst_c = doorway_audit(city_pages + [CITY_DIR + "/index.html"])
    problems = audit(pages) + seo_audit(pages) + door
    if problems:
        print("\nAUDIT FAILED:")
        for p in problems:
            print("  ! " + p)
        sys.exit(1)
    print("\naudit passed: no em dashes, no UK spelling, no invented credentials,")
    print("no reviews, no ratings, no prices.")
    print("seo audit passed: unique titles under %d chars, unique meta descriptions"
          % TITLE_MAX)
    print("%d to %d chars, one h1 per page, no skipped heading levels, canonical +"
          % (DESC_MIN, DESC_MAX))
    print("og + twitter on every page, width and height on every image.")
    print("anti-doorway audit passed on %d city pages: worst pair shares %.0f%% of its body"
          % (len(city_pages), worst_j[0] * 100))
    print("text (limit %.0f%%), worst containment %.0f%% (limit %.0f%%), and every page has"
          % (SIM_JACCARD_MAX * 100, worst_c[0] * 100, SIM_CONTAIN_MAX * 100))
    print("at least one sentence that appears nowhere else.")
    if worst_j[1]:
        print("  closest pair:  %s and %s" % (worst_j[1], worst_j[2]))

    if NOINDEX:
        print("\n" + "=" * 74)
        print("PREVIEW BUILD. noindex is ON and robots.txt disallows everything.")
        print("=" * 74)
        print("Needs " + OWNER + "'s sign-off before this can be indexed:")
        for c in CONFIRM:
            print("  [ ] " + re.sub(r"\s+", " ", c))
        print("\nGo-live: set NOINDEX = False, set FORM_ACCESS_KEY, fill TRUST, re-run.")

    # This one prints whether or not NOINDEX is on, and it prints LAST so it is
    # the thing still on screen when the build finishes. An unwired form on a
    # live site is not a cosmetic defect: it is every lead, silently, forever.
    if not FORM_ACCESS_KEY:
        print("\n" + "!" * 74)
        print("!!  BLOCKED: THE CONTACT FORM CANNOT DELIVER. ONE INPUT IS MISSING.")
        print("!" * 74)
        print("   WE DO NOT HAVE AN EMAIL ADDRESS FOR " + OWNER.upper() + ".")
        print("")
        print("   That is the only thing missing. Everything else is built and waiting:")
        print("   the relay, the redirect, the thank-you page, the spam trap and the")
        print("   phone-readable subject line are all in place and all inert without it.")
        print("")
        print("   Ask " + OWNER + " one question: which email address do you want new")
        print("   leads sent to? Then follow README.md, section SETTING UP THE FORM,")
        print("   steps 1 to 5. It takes about four minutes and costs nothing.")
        print("")
        print("   Until then every page renders a visible 'call or text " + PHONE_DISPLAY + "'")
        print("   notice in place of a working form, and app.js blocks the submit, so")
        print("   no visitor posts into a void. Degraded on purpose, not broken.")
        print("!" * 74)


if __name__ == "__main__":
    main()
