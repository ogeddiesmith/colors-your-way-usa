# Blog photo credits

**Every image in this folder is a STOCK PHOTO from Pexels. None of them are Mike Walsh's work.**

They ship as placeholders so the blog is not a wall of text at launch. Swapping them for real
before-and-after photos of Colors Your Way USA jobs is the single biggest quality and conversion
lever available on this site. Cabinets and popcorn removal produce the most persuasive
before-and-afters. Until that happens, every figure caption on the site says the photo is stock.

Downloaded 2026-08-31 from the Pexels API at 1600px wide. Pexels license: free to use, no
attribution required, but credit is given here as a matter of practice and so the originals can
be traced. See https://www.pexels.com/license/

| File | Used in | Slot | Photographer | Pexels page |
|---|---|---|---|---|
| `cabinets-hero-white-kitchen.jpg` | cabinet-refinishing-vs-replacing | hero | [Curtis Adams](https://www.pexels.com/@curtis-adams-1694007) | [7168051](https://www.pexels.com/photo/inside-of-a-clean-kitchen-7168051/) |
| `cabinets-wood-kitchen.jpg` | cabinet-refinishing-vs-replacing | in-content | [Curtis Adams](https://www.pexels.com/@curtis-adams-1694007) | [24245768](https://www.pexels.com/photo/interior-design-of-kitchen-24245768/) |
| `colors-brick-two-story.jpg` | choosing-paint-colors-older-southwest-suburb-homes | in-content | [Curtis Adams](https://www.pexels.com/@curtis-adams-1694007) | [5178060](https://www.pexels.com/photo/brown-brick-house-5178060/) |
| `colors-hero-choosing-palette.jpg` | choosing-paint-colors-older-southwest-suburb-homes | hero | [Antoni Shkraba](https://www.pexels.com/@shkrabaanthony) | [5292188](https://www.pexels.com/photo/person-holding-color-palettes-5292188/) |
| `exterior-hero-brick-facade.jpg` | best-time-to-paint-house-exterior-chicago | hero | [Valentin Ivantsov](https://www.pexels.com/@valentin-ivantsov-2154772556) | [33513858](https://www.pexels.com/photo/painters-working-on-dutch-brick-house-exterior-33513858/) |
| `exterior-ladder-roller.jpg` | best-time-to-paint-house-exterior-chicago | in-content | [Rajesh S  Balouria](https://www.pexels.com/@rajesh-s-balouria-1289088) | [31608473](https://www.pexels.com/photo/man-painting-building-wall-using-ladder-outdoors-31608473/) |
| `interior-cost-brush-trim.jpg` | interior-painting-cost-southwest-chicago-suburbs | in-content | [Sergey  Meshkov](https://www.pexels.com/@19x14) | [8481711](https://www.pexels.com/photo/person-painting-white-wall-8481711/) |
| `interior-cost-hero.jpg` | interior-painting-cost-southwest-chicago-suburbs | hero | [DΛVΞ GΛRCIΛ](https://www.pexels.com/@davegarcia) | [36153946](https://www.pexels.com/photo/construction-workers-painting-interior-walls-36153946/) |
| `prep-bare-plaster.jpg` | (unused, spare) | spare | [La Miko](https://www.pexels.com/@lamiko) | [3616762](https://www.pexels.com/photo/unfinished-painted-wall-3616762/) |
| `prep-sanding-wall.jpg` | how-to-tell-good-prep-from-a-fast-cheap-job | in-content | [Tima Miroshnichenko](https://www.pexels.com/@tima-miroshnichenko) | [6473978](https://www.pexels.com/photo/a-man-sanding-the-wall-6473978/) |
| `prep-taping-hero.jpg` | how-to-tell-good-prep-from-a-fast-cheap-job | hero | [Antoni Shkraba](https://www.pexels.com/@shkrabaanthony) | [4981797](https://www.pexels.com/photo/a-man-putting-tape-on-the-wall-4981797/) |
| `rental-empty-room-window.jpg` | (unused, spare) | spare | [Peter  Vang](https://www.pexels.com/@peter-vang-2157328093) | [35493915](https://www.pexels.com/photo/spacious-empty-room-with-wooden-flooring-35493915/) |
| `rental-hero-empty-room.jpg` | rental-turnover-painting-southwest-suburbs | hero | [Max Vakhtbovych](https://www.pexels.com/@artbovich) | [7031599](https://www.pexels.com/photo/empty-room-of-modern-apartment-7031599/) |
| `rental-two-painters-rolling.jpg` | rental-turnover-painting-southwest-suburbs | in-content | [Blue Bird](https://www.pexels.com/@blue-bird) | [7218029](https://www.pexels.com/photo/anonymous-people-painting-the-wall-7218029/) |

## Machine-readable version

`_credits.json` in this folder carries the same data with the Pexels alt text and the exact
download URL for each file, so the site generator can emit credit lines without re-querying the API.

## Replacement checklist

When Mike supplies real job photos:

1. Keep the same filenames so no markdown has to change, or update `hero.src` and the inline
   `<img src>` in the affected post.
2. Update `alt` text to describe the actual job, including the town if it is known.
3. Delete the "Stock photo, to be replaced with our own job photos" sentence from the caption.
4. Set `stock_photos: false` in that post's front matter.
5. Remove the row from this file and note the job and date instead.
