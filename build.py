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
import io, json, os, re, sys

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

# Preview switches. BOTH of these flip at go-live, together, and the go-live
# checklist in README.md is the gate.
NOINDEX = True        # emits robots noindex,nofollow + Disallow: / + the banner
PREVIEW_BANNER = True # the amber strip explaining what is placeholder

ASSET_V = "2"         # bump on any CSS or JS change to bust the browser cache

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
    "Service area. Mike confirmed Chicago and the south suburbs on 2026-08-31 and "
    "service-area.html now covers Chicago plus the south and southwest suburbs. "
    "The shape of the area is confirmed. The individual towns at the edge are not: "
    "walk the list with him and cut any town he will not actually drive to, "
    "particularly Frankfort, Lemont, Mokena and Homer Glen.",
    "Chicago is claimed as a service area but deliberately framed as south side "
    "first. Confirm Mike is happy taking city work at all, and how far north he "
    "will go, before the noindex comes off.",
    "Process copy. Masking, prep, cleanup and the cabinet door removal sequence "
    "are described as standard trade practice. Confirm they match how Mike "
    "actually works before this is indexed.",
    "Owner does the work. 'Mike quotes it and Mike works on it' is used as a "
    "headline claim. It is supported by the transcript and by him being a "
    "one-man-plus operation, but confirm it stays true if he puts on a crew.",
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
  "is worth looking at the same week instead of being bundled into next month. Bridgeview "
  "housing is split almost evenly between owners and renters, and the median home went up "
  "around 1975, so most of it is on its second or third repaint."),

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
  "Beverly, Chicago", "Figures are for ZIP code 60643, Beverly and Morgan Park",
  "Beverly is bungalow-belt Chicago close to its most intact, with a stretch of larger frame "
  "and stucco houses up on the ridge. The 60643 ZIP area, which covers Beverly and Morgan "
  "Park, has a median build year of 1950, and about 85 percent of its housing units went up "
  "before 1970. On stock that old the paint work is mostly exterior wood and interior trim: "
  "sash and storm windows, porch columns, soffit and fascia, and interior casing that is "
  "already carrying a lot of coats. It is also as close to a guarantee of pre-1978 paint as "
  "anywhere on this list, which changes how an interior job is contained and cleaned rather "
  "than how it is painted."),
 ("mount-greenwood", "Mount Greenwood", "chicago", 9023, 1794, "$303,300", 1954,
  "Mount Greenwood, Chicago", "Figures are for ZIP code 60655, centered on Mount Greenwood",
  "Mount Greenwood is the most owner-occupied part of the city on this list, about 83 percent, "
  "and it is a 1950s neighborhood in a literal sense: four in ten housing units in the 60655 "
  "ZIP area were built between 1950 and 1959. That is brick bungalow and Cape Cod stock, "
  "smaller rooms, a lot of door and window casing for the square footage, and very often a "
  "basement or attic that was finished later and painted to a different standard than the rest "
  "of the house. Interior quotes here are decided by trim footage far more than by wall area, "
  "which is exactly the line most quotes leave vague."),

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
  "Burbank has some of the oldest housing in the close ring, a median build year around 1965, "
  "and eight in ten households own their home. Almost all of that stock predates 1978, which "
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
  "and cleanly between tenants. Both get quoted the same way here: somebody stands in the "
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
  "Blue Island and the city of Chicago are the only two entries on this list where renters "
  "outnumber owners, and Blue Island has the lowest median home value in the service area at "
  "$169,800. Median build year is around 1961. Put those together and the realistic work here "
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
  "Lemont has the second highest median home value on this list, around $447,800, and a median "
  "build year of 1994. Newer and larger, with the problems that go with that: two story "
  "elevations, tall interior volumes, and millwork a builder specified once and nobody has "
  "touched since. A two story entry is not a room-rate job. Lemont also sits west of the rest "
  "of this list, so scheduling is a genuine conversation rather than a formality."),
]

TIER_LABEL = {
    "home":    "Where the shop is",
    "chicago": "Chicago, and the south side in particular",
    "near":    "The near southwest suburbs, roughly fifteen minutes from the shop",
    "south":   "The south suburbs",
    "far":     "Further out, south and southwest. Ask about scheduling",
}

# Pull one or more groups out of TOWNS, in list order. The footer wants the
# suburbs without the city, and the service pages want the biggest markets only.
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
    ("Areas", "service-area.html"),
]

# The footer has room for the full names, so it uses them.
FOOT_NAV = [
    ("Interior painting", "interior-painting.html"),
    ("Exterior painting", "exterior-painting.html"),
    ("Cabinet refinishing", "cabinet-refinishing.html"),
    ("Drywall and repair", "drywall-and-repair.html"),
    ("Remodeling and trades", "remodeling.html"),
    ("Service area", "service-area.html"),
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
.reads p{margin:0;font-size:.9rem;color:var(--ink-2)}
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
            '<span>Colors Your Way USA<small>Painting &amp; remodeling &middot; Bridgeview, IL</small></span></a>\n'
            '    <button class="burger" id="burger" aria-label="Menu" aria-expanded="false" '
            'aria-controls="nav"><span></span><span></span><span></span></button>\n'
            '    <nav class="nav" id="nav" aria-label="Main">' + links + '</nav>\n'
            '    <a class="hcall" href="tel:' + PHONE_E164 + '" '
            'aria-label="Call ' + PHONE_DISPLAY + '">'
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
    <label for="qf-email">Email <span class="hint">optional, the phone is faster</span></label>
    <input id="qf-email" name="email" type="email" autocomplete="email" data-label="email">
  </div>
  <div class="row">
    <label for="qf-service">What needs doing</label>
    <select id="qf-service" name="service">''' + opts + '''</select>
  </div>
  <div class="row">
    <label for="qf-town">Town <span class="hint">so we know the drive</span></label>
    <input id="qf-town" name="town" type="text" autocomplete="address-level2" required data-label="town">
  </div>
  <div class="row">
    <label for="qf-details">Anything else <span class="hint">optional</span></label>
    <textarea id="qf-details" name="details" rows="3" placeholder="How many rooms, how old the house is, whether it has been painted before"></textarea>
  </div>''' + tail + '''
  <div class="hp" aria-hidden="true">
    <label for="qf-botcheck">Leave this empty</label>
    <input id="qf-botcheck" type="checkbox" name="botcheck" tabindex="-1" autocomplete="off">
  </div>
  ''' + submit + '''
  <p class="msg" id="quote-msg" role="status" hidden></p>
  <p class="note"><strong>Photos help more than anything you can type.</strong>
  Text pictures of the room, the wall or the front of the house to
  <a href="sms:''' + PHONE_E164 + '''">''' + PHONE_DISPLAY + '''</a>. Nothing gets a final price
  without somebody standing in front of it, but photos are how we tell you what to expect
  before that visit.</p>
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
            '    <p class="eyebrow" style="color:#8fd3aa">Get it looked at</p>\n'
            '    <h2>The fastest way to a real number is a phone call.</h2>\n'
            '    <p>' + OWNER + ' quotes the work himself. Tell him the town, the room and roughly '
            'what you want, and you will know what happens next.</p>\n'
            '    <a class="big" href="tel:' + PHONE_E164 + '">' + PHONE_DISPLAY + '</a>\n'
            '    <div class="row"><a class="btn" href="tel:' + PHONE_E164 + '">Call now</a>'
            '<a class="btn btn-b" href="' + up + 'contact.html#quote">Send the details instead</a></div>\n'
            '  </div>\n</section>\n')


def footer(up=""):
    navlinks = "".join('<li><a href="' + up + h + '">' + t + '</a></li>' for t, h in FOOT_NAV)
    # The city goes in its own sentence. Running "Chicago, Beverly, Mount
    # Greenwood, Oak Lawn, ..." into one comma list reads as though Beverly and
    # Mount Greenwood are suburbs, which they are not.
    suburbs = ", ".join(t[1] for t in towns_in("home", "near", "south", "far"))
    hours = TRUST["hours"] if TRUST["hours"] else "Hours to supply"
    # Headings here are h2, not h4. They sit at the top level of the footer, so
    # h4 skipped from the last h2 on the page straight to h4 and broke the
    # heading outline on every single page. Styling comes from .fh, not the tag.
    return ('<footer>\n  <div class="wrap">\n    <div class="foot">\n'
            '      <div>\n'
            '        <h2 class="fh">' + BRAND + '</h2>\n'
            '        <address>' + STREET + '<br>' + CITY + ', ' + REGION + ' ' + POSTAL + '<br>'
            '<a href="tel:' + PHONE_E164 + '">' + PHONE_DISPLAY + '</a></address>\n'
            '        <p style="margin-top:12px">Painting and remodeling. Owned and worked by '
            + OWNER + '.</p>\n'
            '        <p style="font-size:.84rem">' + hours + '</p>\n'
            '      </div>\n'
            '      <nav aria-label="Footer">\n        <h2 class="fh">Work</h2>\n'
            '        <ul class="fl">' + navlinks +
            '<li><a href="' + up + 'blog/index.html">Notes</a></li>'
            '<li><a href="' + up + 'contact.html">Contact</a></li></ul>\n      </nav>\n'
            '      <div>\n        <h2 class="fh">Where we work</h2>\n'
            '        <p style="font-size:.86rem;line-height:1.7">Chicago, and the south side in '
            'particular, including Beverly and Mount Greenwood.</p>\n'
            '        <p style="font-size:.86rem;line-height:1.7">' + suburbs + '.</p>\n'
            '        <p style="font-size:.86rem"><a href="' + up + 'service-area.html">'
            'See what each place is like</a></p>\n      </div>\n'
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

# areaServed is built from TOWNS so the markup can never drift from the page.
# Beverly and Mount Greenwood are Chicago community areas, not municipalities, so
# they are emitted as Place rather than City. Typing a neighborhood as a City is
# the sort of small structured-data lie that is easy to write and pointless.
def area_served():
    out = []
    for t in TOWNS:
        heading = t[7]
        if heading.endswith(", IL"):
            out.append({"@type": "City", "name": heading})
        else:
            out.append({"@type": "Place", "name": heading + ", IL"})
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
      title="Interior Painting, Bridgeview IL | Colors Your Way USA",
      desc=("Interior painting on Chicago's south side and across the south and southwest "
            "suburbs. Walls, ceilings, trim and doors, prepped properly. "
            "Call " + PHONE_DISPLAY + "."),
      h1="Interior painting, prepped properly and put back together.",
      lede=("Walls, ceilings, trim, doors and the patching that has to happen first. Most of the "
            "houses around here went up between 1955 and 1977, which means plaster, heavy casing "
            "and paint that has been over-coated more than once. That changes the job."),
      formhead="Get an interior quote",
      formsub="Tell us the rooms and the town. " + OWNER + " calls you back.",
      inc=["Walls, ceilings, trim, doors and window casings, priced separately so you can see what "
           "you are paying for",
           "Patching, filling and sanding before anything is coated",
           "Masking, floor protection and putting the room back",
           "Color matching to what is already there, or a full change with the right primer under it",
           "Closets, stairwells and hallways, which are the parts that get skipped"],
      steps=[("Walk-through", "Somebody stands in the room, counts the doors and the trim runs, and "
              "looks at the condition of what is already on the wall. That is the only honest way to "
              "price it."),
             ("Prep", "Fill, patch, sand, caulk, mask. This is where the time goes on an older house "
              "and it is the part that decides whether the finish still looks right in five years."),
             ("Prime where it is needed", "Bare patches, stains, and any big color change get primed. "
              "Skipping this is how a job needs a third coat it was never priced for."),
             ("Finish coats", "Cut in, roll out, then look at it in daylight and fix what daylight "
              "shows."),
             ("Put it back", "Furniture back, hardware back, floors clear.")],
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
        ("Pre-1978 housing", "See the note below. It is a real difference in setup and cleanup on a "
         "large share of the houses in this area.")],
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
            "Yes, and it is worth understanding. The EPA lead renovation, repair and painting rule "
            "covers anyone paid to disturb painted surfaces in housing built before 1978. Median "
            "build year in Bridgeview is about 1975, Oak Lawn about 1967 and Burbank about 1965, so "
            "most of the houses here are inside it. Ask any contractor how they handle it. "
            "<a href=\"https://www.epa.gov/lead/lead-renovation-repair-and-painting-program\" "
            "rel=\"nofollow noopener\">EPA guidance is here</a>.")],
      ba=[("ba1-before", "ba1-after", "Interior repaint, walls and ceiling"),
          ("ba3-before", "ba3-after", "Kitchen, cabinets and walls")],
      related=["exterior-painting", "cabinet-refinishing", "drywall-and-repair"]),

 dict(slug="exterior-painting", nav="Exterior", card="Exterior painting", hero="hero-exterior",
      title="Exterior House Painting, Bridgeview | Colors Your Way USA",
      desc=("Exterior house painting on Chicago's south side and across the south and southwest "
            "suburbs. Siding, trim, soffit, fascia and doors. Call " + PHONE_DISPLAY + "."),
      h1="Exterior painting that has to survive a Chicago winter.",
      lede=("Siding, trim, soffit, fascia, overhangs, garage doors and front doors. An exterior in "
            "this climate is mostly a preparation job. What gets scraped, washed, primed and caulked "
            "decides how it looks in year four, not what goes on top of it."),
      formhead="Get an exterior quote",
      formsub="Exteriors book up fast in spring. Ask early.",
      inc=["Wood, aluminum, vinyl, stucco and painted brick, which all behave differently and get "
           "prepped differently",
           "Trim, soffit, fascia and gable ends, which fail long before the walls do",
           "Scraping, washing, spot priming and caulking before any finish goes on",
           "Garage doors, front doors and the metal work people forget to include",
           "Decks and fences, stained or sealed, as a separate line"],
      steps=[("Walk the whole elevation", "All four sides, plus what you can only see from a ladder. "
              "The rot at the end of a fascia board is not visible from the driveway and it is not "
              "something you want found halfway through."),
             ("Wash and scrape", "Loose and failing material comes off. Anything that is still bonded "
              "stays. What comes off decides the real size of the job."),
             ("Repair before paint", "Failed caulk, split trim, soft fascia and rotted sills get dealt "
              "with first. Painting over rot buys one season."),
             ("Prime the bare", "Every bare surface, and every knot and stain that will bleed."),
             ("Finish coats", "Applied in the right temperature window, which in this climate is a "
              "shorter list of days than people expect.")],
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
      title="Kitchen Cabinet Painting, Bridgeview | Colors Your Way USA",
      desc=("Kitchen cabinet painting and refinishing across Chicago's south side and the south "
            "suburbs. Doors off, degreased, sanded, sprayed and rehung. Call "
            + PHONE_DISPLAY + "."),
      h1="Cabinet refinishing, without buying a new kitchen.",
      lede=("If the boxes are solid and the layout works, the doors are the problem, not the kitchen. "
            "Refinishing keeps the boxes, the layout and the countertops, and changes the thing you "
            "actually look at."),
      formhead="Get a cabinet quote",
      formsub="Send a photo of the kitchen and the door style.",
      inc=["Doors and drawer fronts removed, numbered and worked off site or in a controlled space",
           "Degreasing, which is the step that decides whether the finish sticks",
           "Sanding, filling and a bonding primer made for cabinets",
           "Sprayed finish coats, not brush marks",
           "Hardware refitted, or new hardware fitted if you are changing it",
           "Boxes and face frames done in place"],
      steps=[("Look at the boxes first", "If the carcasses are sound, refinishing makes sense. If they "
              "are falling apart or the layout is wrong, you are better off being told that than being "
              "sold a finish on top of a bad box."),
             ("Doors off and labeled", "Every door and drawer front comes off and gets numbered so it "
              "goes back exactly where it came from. Hinges and hardware bagged with it."),
             ("Degrease, then sand", "A kitchen has years of cooking film on it. Skipping the "
              "degreasing is the single most common reason a cabinet job peels within a year."),
             ("Bonding primer", "Cabinets need a primer built to stick to a finished factory surface. "
              "Wall primer is not it."),
             ("Spray the finish", "Sprayed, so there is no brush texture on a surface your hand touches "
              "every day."),
             ("Cure, then rehang", "The finish needs time before it is handled. Rushing this is how "
              "fingerprints end up permanent.")],
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
      title="Drywall Repair, Bridgeview IL | Colors Your Way USA",
      desc=("Drywall and plaster repair with the painting that goes over it. Cracks, holes, "
            "water damage and texture matching, Chicago and the south suburbs. "
            + PHONE_DISPLAY + "."),
      h1="Drywall and plaster repair, and the paint that goes over it.",
      lede=("Cracks, holes, nail pops, water stains, failed tape joints and the ceiling that came "
            "down after the bathroom leaked. Repair and paint are one job here, which is not true of "
            "every company you will call."),
      formhead="Get a repair quote",
      formsub="A photo of the damage usually tells us most of it.",
      inc=["Cracks, holes, nail pops and failed tape joints",
           "Water damaged drywall and ceilings, once the leak itself is fixed",
           "Plaster repair, which is a different job from drywall and common in the older housing here",
           "Texture matching so the patch does not read as a patch",
           "Priming and painting the repair, and blending it into the rest of the wall"],
      steps=[("Find out why", "A crack that keeps coming back is telling you something. Settlement, a "
              "leak and a failed joint all look similar and need different answers."),
             ("Cut back to solid", "Damaged material comes out. Patching over soft or wet board just "
              "moves the problem a few months down the road."),
             ("Patch and tape", "New board, tape, and compound built up in coats rather than filled in "
              "one go."),
             ("Match the texture", "This is the step that decides whether the repair disappears. An "
              "unmatched texture is visible from across the room forever."),
             ("Prime and paint", "The repair gets primed, then painted, then blended out so the wall "
              "reads as one surface.")],
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
      title="Remodeling and Trades, Bridgeview IL | Colors Your Way USA",
      desc=("Carpentry, tile, flooring, subfloor repair, concrete, faux finishes and "
            "remodeling across Chicago's south side and the south suburbs. Call "
            + PHONE_DISPLAY + "."),
      h1="When the paint is not the whole problem.",
      lede=("Painting is the front door of this business and most of what we do. But a lot of jobs "
            "turn out to be something else once you look properly, and this is where that gets "
            "handled instead of handed to somebody you then have to chase."),
      formhead="Ask about a bigger job",
      formsub="Tell us what you are actually looking at.",
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
             ("One person, one schedule", "The reason this list exists is sequencing. Subfloor, then "
              "tile, then trim, then paint, in that order, without three companies coordinating "
              "diaries."),
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
            OWNER + " does. He quotes it and he works on it. That is not something a franchise office "
            "can copy, and it is the main reason people call back.")],
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
    faqrows, faqld = faq(s["faq"])
    rel = "".join('<a class="pill" href="' + r + '.html">' + SERVICE_BY_SLUG[r]["card"] + '</a>'
                  for r in s["related"])
    # Town pills are capped. The service area is being widened, and a service
    # page that dumps forty town links into one pill row is link soup, not
    # internal linking. The near ring gets named, the rest is one link to the
    # service area page, which is the hub that actually holds the town content.
    near = towns_in("home", "chicago", "near")[:10]
    towns = "".join('<a class="pill" href="service-area.html#' + t[0] + '">' + t[1] + '</a>'
                    for t in near)
    towns += ('<a class="pill" href="service-area.html"><strong>All ' + str(len(TOWNS)) +
              ' places and what is different about each &rarr;</strong></a>')
    reads = post_links(s["slug"], posts)
    crumb_html, crumb_ld = breadcrumbs([("Home", "index.html"), (s["card"], fn)])

    html = head(s["title"], s["desc"], fn, s["hero"]) + header(fn)
    html += '<main id="main">\n' + crumb_html
    html += hero(s["h1"], s["lede"], s["nav"] + " &middot; Bridgeview, IL", s["hero"],
                 s["formhead"], s["formsub"], page=s["nav"] + " (" + fn + ")")
    html += ('<div class="strip"><div class="wrap"><ul>'
             '<li>Bridgeview based</li><li>' + OWNER + ' quotes it and works on it</li>'
             '<li>Painting, carpentry, tile and flooring</li>'
             '<li>No price without a walk-through</li></ul></div></div>\n')

    html += ('<section>\n  <div class="wrap two-col">\n    <div>\n'
             '      <p class="eyebrow">What is covered</p>\n'
             '      <h2>' + s["card"] + ', in full</h2>\n'
             '      <ul class="ticks">' + inc + '</ul>\n'
             '    </div>\n    ' + img(s["ba"][0][1]) + '\n  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">How the job runs</p>\n'
             '    <h2>The order it happens in</h2>\n'
             '    <ol class="nums">' + steps + '</ol>\n  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap">\n'
             '    <p class="eyebrow">Recent work</p>\n'
             '    <h2>Before and after</h2>\n'
             '    <p class="lede">The only thing worth judging a painter on.</p>\n'
             '    ' + ba_gallery(s["ba"]) + '\n  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">What moves the number</p>\n'
             '    <h2>Why two quotes for the same room can look nothing alike</h2>\n'
             '    <p class="lede">No price is published here, because a real number needs somebody '
             'to stand in the room first. What can be published is what actually drives it, so you '
             'can read any quote you get and know what you are looking at.</p>\n'
             '    <ol class="nums">' + drivers + '</ol>\n'
             '    <div class="callout"><h3>Ask every contractor the same three questions</h3>'
             '<p>What preparation is included. How many coats. What happens to the price if the '
             'preparation turns out to be worse than it looks. The answers, more than the total, '
             'are what tell you which quote is real.</p></div>\n'
             '  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Questions</p>\n'
             '    <h2>About ' + s["card"].lower() + '</h2>\n'
             '    ' + faqrows +
             '    <p class="eyebrow" style="margin-top:2rem">Also does</p>\n'
             '    <div class="pills">' + rel + '</div>\n'
             '    <p class="eyebrow" style="margin-top:1.6rem">Working in</p>\n'
             '    <div class="pills">' + towns + '</div>\n'
             '  </div>\n</section>\n')

    if reads:
        html += ('<section class="alt">\n  <div class="wrap narrow">\n'
                 '    <p class="eyebrow">Worth reading first</p>\n'
                 '    <h2>Written out in more detail</h2>\n'
                 '    <p class="lede">The questions people ask on the phone, answered properly '
                 'and with the sources named.</p>\n'
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
    cards += ('<a class="card" href="service-area.html">' + img("hero-service-area") +
              '<div class="body"><h3>Where we work</h3><p>Chicago and the south and southwest '
              'suburbs, with what is actually different about the housing in each one.</p>'
              '<span class="more">See the towns &rarr;</span></div></a>')

    faqrows, faqld = faq([
      ("What towns do you cover?",
       "Chicago and the south and southwest suburbs. Bridgeview is the base, at " + STREET + " "
       "The close ring from there is Oak Lawn, Burbank, Evergreen Park, Palos Hills, Palos "
       "Heights, Hickory Hills, Chicago Ridge, Worth, Justice, Willow Springs, Summit and Bedford "
       "Park. On the city side it is the south side, Beverly and Mount Greenwood in particular. "
       "South of that is Oak Forest, Alsip, Midlothian, Blue Island and Crestwood, and further "
       "out again Orland Park, Tinley Park, Homer Glen, Mokena, Frankfort and Lemont, which are "
       "worth a conversation about scheduling before anybody drives. There is a page explaining "
       "what is different about each one."),
      ("Do you do more than painting?",
       "Yes, and it is unusual around here. Alongside interior and exterior painting there is "
       "carpentry, tile, flooring, subfloor repair, concrete, faux finishes and general remodeling. "
       "The point is not a longer list. It is that a job does not stop when it turns out to need "
       "more than paint."),
      ("How do you price a job?",
       "After a walk-through. No number is published on this site and no number gets given over the "
       "phone as a final price, because the two things that decide an interior job are the condition "
       "of what is already on the wall and how much trim there is, and neither shows up in a photo. "
       "Photos are still useful for telling you what to expect before the visit."),
      ("Who does the work?",
       OWNER + " does. He is a long-time tradesman, he quotes the job himself, and he is on it. "
       "There is no branch office and no salesperson."),
      ("Are you insured?",
       "Insurance and any local registration details are listed on this site as soon as the "
       "paperwork is supplied. Nothing is claimed here that has not been produced. Ask on the phone "
       "and you will get a straight answer."),
      ("Do you have reviews I can read?",
       "Not yet. This is a business that has run on word of mouth and a van, and no reviews have "
       "been collected. Rather than fill this page with something invented, the space is left "
       "empty until there are real ones to put in it."),
    ])

    html = head("House Painters in Bridgeview, IL | " + BRAND,
                "Painter and remodeler based in Bridgeview, covering Chicago and the south "
                "suburbs. Interior, exterior, cabinets, drywall, carpentry and tile. "
                "Call " + PHONE_DISPLAY + ".",
                "index.html", "og-home")
    html += header("index.html")
    html += '<main id="main">\n'
    html += hero("Bridgeview painters who can finish the whole job.",
                 "Interior and exterior painting, cabinets and drywall, plus the carpentry, tile "
                 "and flooring that usually gets handed to somebody else. " + OWNER + " quotes "
                 "the work and " + OWNER + " does the work.",
                 "Painting &amp; remodeling &middot; Bridgeview, IL", "og-home",
                 "Ask for a quote", "Tell us the town and what needs doing.",
                 page="Home (index.html)")
    html += ('<div class="strip"><div class="wrap"><ul>'
             '<li>Based at ' + STREET + ', Bridgeview</li>'
             '<li>Owner quotes it, owner works on it</li>'
             '<li>Painting, carpentry, tile, flooring, concrete</li>'
             '<li>Every job quoted after a walk-through</li></ul></div></div>\n')

    html += ('<section>\n  <div class="wrap">\n'
             '    <p class="eyebrow">What we do</p>\n'
             '    <h2>Start with what you are looking at</h2>\n'
             '    <p class="lede">Most calls are one of these five. Each page says what is '
             'included, the order the work happens in, and what makes one quote different from '
             'another.</p>\n'
             '    <div class="cards">' + cards + '</div>\n  </div>\n</section>\n')

    html += ('<section class="alt" id="work">\n  <div class="wrap">\n'
             '    <p class="eyebrow">Recent work</p>\n'
             '    <h2>Before and after</h2>\n'
             '    <p class="lede">A painter should be judged on pairs of photos of the same room, '
             'and nothing else.</p>\n'
             '    ' + ba_gallery([("ba1-before", "ba1-after", "Interior repaint"),
                                  ("ba2-before", "ba2-after", "Exterior, siding and trim"),
                                  ("ba3-before", "ba3-after", "Kitchen cabinets refinished"),
                                  ("ba4-before", "ba4-after", "Bathroom, tile and finish")]) +
             '\n  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap two-col">\n    <div>\n'
             '      <p class="eyebrow">Why people call</p>\n'
             '      <h2>Three things that are true here and are not true everywhere</h2>\n'
             '      <ul class="ticks">'
             '<li><strong>The person quoting it is the person doing it.</strong> ' + OWNER + ' '
             'walks the job, prices the job and works on the job. Nothing gets lost between a '
             'salesperson and a crew.</li>'
             '<li><strong>The trade list is deep enough to finish.</strong> Painting, carpentry, '
             'tile, flooring, subfloors, concrete and faux finishes. When a bathroom repaint turns '
             'out to be a subfloor, it does not turn into a search for a second contractor.</li>'
             '<li><strong>One geography, worked properly.</strong> The shop is in Bridgeview, '
             'about where the city stops and the southwest suburbs start, and the work is the '
             'south side of Chicago and the towns south and southwest of it. Not the whole metro, '
             'and not a franchise map running from Naperville to Joliet.</li>'
             '</ul>\n    </div>\n    ' + img("prep-tape") + '\n  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Straight answers</p>\n'
             '    <h2>License, insurance and guarantee</h2>\n'
             '    <p class="lede">Most contractor sites carry a badge claiming every credential '
             'going, with no numbers behind any of it. Here is the honest version.</p>\n'
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
             '    <h2>There are no reviews on this page yet</h2>\n'
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
             '    <p class="eyebrow">Questions</p>\n    <h2>Before you call</h2>\n'
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
                 '    <h2>What people ask before they call</h2>\n'
                 '    <p class="lede">Written out properly, with every price figure named as a '
                 'published market range and its source given.</p>\n'
                 '    <ul class="reads">' + latest + '</ul>\n' + note +
                 '    <p style="margin-top:18px"><a href="blog/index.html">All notes &rarr;</a>'
                 '</p>\n  </div>\n</section>\n')

    html += cta()
    html += "</main>\n" + footer()
    html += ld_json([website_ld(),
                     webpage_ld("index.html", BRAND + ", house painters in Bridgeview, IL",
                                "Painting and remodeling contractor serving Chicago and the "
                                "south suburbs from Bridgeview, Illinois."),
                     faqld])
    html += confirm_comment() + "</body>\n</html>\n"
    write("index.html", html)
    return "index.html"


def build_service_area():
    fn = "service-area.html"
    blocks = ""
    last_tier = None
    for slug, name, tier, own, rent, val, yr, heading, geo, copy in TOWNS:
        if tier != last_tier:
            blocks += '<p class="tier">' + TIER_LABEL[tier] + '</p>\n'
            last_tier = tier
        pct = int(round(100.0 * own / float(own + rent)))
        # val is None for Bedford Park, where the residential sample is under 200
        # households and the Census median value estimate is too thin to publish.
        # Print nothing rather than a number nobody can stand behind.
        facts = ('<li>' + format(own, ",") + ' owner-occupied homes</li>'
                 '<li>' + format(rent, ",") + ' rented</li>'
                 '<li>' + str(pct) + '% owner-occupied</li>')
        if val:
            facts += '<li>Median value ' + val + '</li>'
        facts += '<li>Median build year ' + str(yr) + '</li>'
        if geo:
            facts += '<li>' + geo + '</li>'
        blocks += ('<div class="town" id="' + slug + '">\n'
                   '  <h3>' + heading + '</h3>\n'
                   '  <ul class="facts">' + facts + '</ul>\n'
                   '  <p>' + copy + '</p>\n</div>\n')

    faqrows, faqld = faq([
      ("Do you actually work in Chicago, or is that just on the website?",
       "The city is real work, and it is mostly the south side. Bridgeview is a short run from "
       "Garfield Ridge, Clearing, Ashburn, Beverly and Mount Greenwood, and those neighborhoods "
       "are the same brick bungalow stock as the inner suburbs, so it is the same job. What will "
       "not be pretended here is coverage of the whole city. Chicago is enormous and heavily "
       "contested, and a north side call is better served by somebody on the north side. Ask, and "
       "you will be told which one you are before anyone schedules anything."),
      ("How far do you travel?",
       "The shop is in Bridgeview and the close ring is where most of the work is. Further out is "
       "possible and it depends on the size of the job, because a long drive is worth it for a full "
       "exterior and not worth it for one small repair. Ask, and you will get a straight answer "
       "rather than a yes that turns into a scheduling problem."),
      ("Why does the age of my house keep coming up?",
       "Because it is the single most useful thing to know before quoting. About 69 percent of "
       "Chicago's housing units were built before 1970, and the near southwest suburbs have median "
       "build years between 1947 and 1977. That means plaster as well as drywall, heavy trim, more "
       "coats of old paint, and the federal lead-safe rule for anything built before 1978. The far "
       "south and southwest towns are the opposite profile: Mokena, Frankfort, Lemont and Homer "
       "Glen are 1988 to 2000 construction, where the issue is not old paint but big elevations "
       "and tall interiors."),
      ("Do you work for landlords and property managers?",
       "Yes, and it is an obvious fit here that nobody local seems to advertise. Blue Island is the "
       "only suburb on this list where renters outnumber owners, Justice runs just under half "
       "rental, Chicago Ridge is not far behind, and Alsip and Bridgeview are both around a third. "
       "Turnover repaints between tenants are steady, repeatable work. The van says Maintenance "
       "Service on it, and this is what that means."),
      ("Do you do commercial work?",
       "Small local commercial, yes: offices, a retail unit, common areas in a building. Bedford "
       "Park in particular is barely residential, with fewer than 200 occupied households in the "
       "whole village, so anything there is going to be this kind of work. Large commercial "
       "contracts are a different business with different requirements and are better off with a "
       "company that only does that."),
    ])

    services = "".join('<a class="pill" href="' + s["slug"] + '.html">' + s["card"] + "</a>"
                       for s in SERVICES)
    crumb_html, crumb_ld = breadcrumbs([("Home", "index.html"), ("Service area", fn)])

    # Title is 57 characters. "and the" was dropped from it, not from the page,
    # because the full phrase pushed the tag to 65 and Google cuts around 60.
    # The h1 and the lede still say it in full. seo_audit() enforces the limit.
    html = head("Service Area, Chicago South Suburbs | " + BRAND,
                "Painting and remodeling across Chicago's south side and the south and southwest "
                "suburbs, from the Bridgeview shop. " + str(len(TOWNS)) + " places, and what "
                "each one needs.",
                fn, "hero-service-area")
    html += header(fn)
    html += '<main id="main">\n' + crumb_html
    html += hero("Where we work, and what is different about each place.",
                 "Chicago and the south and southwest suburbs, " + str(len(TOWNS)) + " of them, "
                 "and they are genuinely not the same job. The city and the inner ring are "
                 "pre-1978 brick and plaster with heavy trim. The far south and southwest are "
                 "1980s and 1990s construction with big elevations and tall interiors. Here is "
                 "the honest read on each one.",
                 "Service area &middot; Chicago and the south suburbs", "hero-service-area",
                 "Check your town", "Tell us where you are and what needs doing.",
                 page="Service area (service-area.html)")

    html += ('<section>\n  <div class="wrap">\n'
             '    <div class="callout" style="margin-top:0"><h3>South side and south suburbs, in '
             'that order of honesty</h3>'
             '<p>The shop is at ' + STREET + ' in Bridgeview, which sits about where the city '
             'stops and the southwest suburbs start. That is the whole geography of this '
             'business: the south side of Chicago and the towns south and southwest of it. '
             'Everything below is built outward from that one address.</p>'
             '<p>Chicago is on this list, and it should not be oversold. The city is a far '
             'bigger and far more competitive market than any suburb here, and no small shop '
             'covers all of it well. The realistic city work is the south side, Beverly, Mount '
             'Greenwood and the neighborhoods around them. Most of the jobs are in the suburbs. '
             'If you are on the north side, somebody closer to you will serve you better, and '
             'you will get told that on the phone rather than after a missed appointment.</p>'
             '</div>\n'
             '    <div class="towns">' + blocks + '</div>\n'
             '    <p class="src" style="font-size:.85rem;color:var(--ink-2);margin-top:26px">'
             'Housing figures on this page are from the ' + CENSUS_CITE + ' They describe the '
             'places, not this business. Beverly and Mount Greenwood are Chicago community '
             'areas and the Census has no geography that matches a Chicago neighborhood, so '
             'their figures are for the ZIP code tabulation areas that cover them, 60643 and '
             '60655, and both entries say so.</p>\n'
             '  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Questions</p>\n    <h2>About the service area</h2>\n'
             '    ' + faqrows +
             '    <p class="eyebrow" style="margin-top:2rem">What we do in these towns</p>\n'
             '    <div class="pills">' + services + '</div>\n'
             '  </div>\n</section>\n')
    html += cta()
    html += "</main>\n" + footer()
    html += ld_json([webpage_ld(fn, "Service area, " + BRAND,
                                "The towns " + BRAND + " covers and what is different about "
                                "the housing in each."), faqld, crumb_ld])
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
      ("What is the fastest way to get an answer?",
       "The phone. " + PHONE_DISPLAY + ". There is one number and it goes to " + OWNER + ". If you "
       "would rather text, texting photos of the room or the front of the house is genuinely the "
       "most useful thing you can send."),
      ("What should I have ready?",
       "The town, roughly what needs doing, and an idea of the age of the house. For an interior, "
       "how many rooms and whether you want the trim and ceilings included. For an exterior, how "
       "many stories and what the siding is. None of it has to be exact."),
      ("Will I get a price on the phone?",
       "You will get a useful idea of what is involved and what tends to move the number. You will "
       "not get a final price, because the two things that decide an interior job are the condition "
       "of what is already on the wall and how much trim there is, and neither of those is visible "
       "over the phone."),
      ("Do you charge to come out and look?",
       "Ask when you call. It is a fair question and you should get a clear answer before anybody "
       "drives out, not after."),
    ])

    crumb_html, crumb_ld = breadcrumbs([("Home", "index.html"), ("Contact", fn)])

    html = head("Contact a Bridgeview, IL Painter | " + BRAND,
                "Call " + PHONE_DISPLAY + " or text photos of the job. " + BRAND + ", "
                + STREET + ", " + CITY + ", " + REGION + " " + POSTAL + ". Painting and "
                "remodeling, Chicago and south suburbs.",
                fn, "hero-contact")
    html += header(fn)
    html += '<main id="main">\n' + crumb_html
    html += hero("Tell us what you are looking at.",
                 "One number, and it goes to " + OWNER + ". Photos help more than a long "
                 "description, so if you are texting, send pictures of the room, the wall or the "
                 "front of the house.",
                 "Contact &middot; Bridgeview, IL", "hero-contact",
                 "Send the details", "Or just call. The phone is faster.",
                 page="Contact (contact.html)")

    html += ('<section>\n  <div class="wrap two-col">\n    <div>\n'
             '      <p class="eyebrow">Reach us</p>\n      <h2>Direct</h2>\n'
             '      <p style="font-size:1.5rem;font-weight:700;margin-bottom:1.2rem">'
             '<a href="tel:' + PHONE_E164 + '">' + PHONE_DISPLAY + '</a></p>\n'
             '      <p><strong>Text photos to the same number.</strong><br>'
             '<a href="sms:' + PHONE_E164 + '">' + PHONE_DISPLAY + '</a></p>\n'
             '      <p><strong>Shop</strong><br>' + STREET + '<br>' + CITY + ', ' + REGION + ' '
             + POSTAL + '</p>\n'
             '      ' + hours_html + '\n'
             '      <p style="font-size:.88rem;color:var(--ink-2)">This is a working address, not a '
             'showroom. Call before coming by.</p>\n'
             '    </div>\n    ' + img("swatches") + '\n  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Paperwork</p>\n    <h2>What we can show you</h2>\n'
             '    ' + trust_row() + '\n'
             '    <p style="margin-top:18px;font-size:.93rem;color:var(--ink-2)">These stay marked '
             'as to supply until the real documents are handed over. Ask on the phone and you will '
             'get a straight answer either way.</p>\n  </div>\n</section>\n')

    html += ('<section>\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">Questions</p>\n    <h2>Before you call</h2>\n'
             '    ' + faqrows + '  </div>\n</section>\n')
    html += cta()
    html += "</main>\n" + footer()

    contact_ld = {"@type": "ContactPage", "@id": canonical_url(fn) + "#webpage",
                  "url": canonical_url(fn), "name": "Contact " + BRAND,
                  "description": "How to reach " + BRAND + " in Bridgeview, Illinois.",
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
             'and one person reading it, so nothing is sitting in a queue waiting to be assigned '
             'to somebody.</p>\n'
             '  </div>\n</section>\n')

    html += ('<section class="alt">\n  <div class="wrap narrow">\n'
             '    <p class="eyebrow">What happens next</p>\n'
             '    <h2>In order</h2>\n'
             '    <ol class="steps">\n'
             '      <li><strong>' + OWNER + ' calls you back.</strong> He is on a job site most '
             'of the day, so realistically that is between jobs, at lunch, or in the evening. '
             'If you need an answer sooner than that, calling is faster than waiting.</li>\n'
             '      <li><strong>A few questions on the phone.</strong> The town, roughly what '
             'needs doing, and the age of the house. You will get a useful idea of what is '
             'involved and what tends to move the number.</li>\n'
             '      <li><strong>Somebody stands in front of it.</strong> No final number gets '
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
    "interior-painting-cost-southwest-chicago-suburbs": "Interior Painting Cost, Bridgeview IL",
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
    "/service-area/": "../service-area.html",
    "/contact/": "../contact.html",
    # Not built yet. Both are on the month 2 to 3 queue in
    # 08-SEO-AND-KEYWORD-RESEARCH.md section 7. Point them at the closest real
    # page rather than shipping a 404, and re-point them when the pages exist.
    "/rental-turnover-painting/": "../service-area.html",
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
    "../service-area.html": "service area",
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
SITEMAP_EXCLUDE = ("thank-you.html",)


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
            #   service-area.html  Census median HOME values. Facts about towns,
            #                      not prices for work.
            #
            # Everywhere else, any page that shows a dollar figure must also
            # carry the market-range disclaimer and must name a source. Both
            # blocks are injected by the builders, so a page that quotes money
            # and forgets them is a build bug, not a copy decision.
            if f != "service-area.html":
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
        if 'href="service-area.html' not in txt:
            problems.append(fn + ": does not link to the service area page.")
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
        print("  %-28s %6d bytes" % (p, os.path.getsize(os.path.join(HERE, p))))
    print("  %-28s %6d bytes" % ("style.css", os.path.getsize("style.css")))
    print("  %-28s %6d bytes" % ("app.js", os.path.getsize("app.js")))
    print("  blog posts found: %d" % len(posts))

    problems = audit(pages) + seo_audit(pages)
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
