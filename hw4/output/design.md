# Problem 10: Premium Store Design

The site was redesigned to feel like a real, premium Yale-inspired store rather than a class project. All products, prices, stock levels, and counts on the page still come from the database. No backend code or data was changed for this problem.

## Design direction

| Element | Before | Now | Why |
|---|---|---|---|
| **Palette** | White pages, bright blue | **Cream** backgrounds (`#f7f2e8`), warm paper cards, deep **Yale navy** (`#00356b` / `#0b2342`), and a small brass accent for labels | Cream and navy feel heritage and premium, like a campus outfitter, not a template. Navy keeps it unmistakably Yale. |
| **Type** | Inter + Libre Baskerville | **Cormorant Garamond** (elegant serif) for headings, product names, and prices; **Inter** for reading text | An editorial serif signals quality. A clean sans keeps descriptions and forms easy to read. |
| **Layout** | Dense, uniform blocks | Generous spacing, eyebrow labels ("— Find your fit") above each heading, clear sections alternating cream and deeper cream | Clear hierarchy tells shoppers where they are and what to do next. |

*Note: the workspace default (AGENTS.md) is black and pink. This problem explicitly asked for navy and cream, so that request was followed.*

## What changed, page by page

**Homepage**
- **Hero:** "Dressed in *Yale blue*, made for every Bulldog", with two clear actions: *Shop the Collection* and *Ask our assistant*. Live stats from the catalogue (102 styles, 6 categories, XS–XXL) sit next to a collage of real best-stocked products. A tag gives the featured product's name and price, and a slowly rotating Campus Customs seal adds a finishing touch.
- **Scrolling navy ribbon** of themes (Residential colleges ✦ Game day ✦ Gifts for Mom & Dad …).
- **Shop by Category:** tall photo tiles with style counts; the photo zooms gently on hover.
- **Featured Picks** and a new **Gifts for Every Bulldog in the Family** row (the real Mom, Dad, Grandpa, Aunt, Cousin designs). "See more" opens all 12 family designs.
- **"Not sure what to choose? Just ask."** A navy panel introduces the assistant, with one-click example questions ("Something cozy for winter", "A gift for my dad") that open the chat and ask them. A labeled example conversation shows what to expect.
- **Four promise cards:** live stock, every college and team, gifts, and help. Then a milestone banner, "From move-in day to commencement".

**Navigation and footer**
- A navy promo bar with real promises (live stock, XS–XXL, assistant).
- A frosted cream navbar with a crest logo. Links get an animated underline, and a soft shadow appears once you scroll.
- On phones there's a full-screen-width menu with large serif links.
- The footer now opens with "Need a hand choosing?" and a *Chat with the assistant* button, and lists every category.

**Product cards**
- **Photo frames match each photo:** about half of the catalogue photos have black backgrounds and about 30 are padded with black side bars.
  - A small component (`ProductImage.tsx`) reads each photo's edges in the browser and paints the frame in the photo's own background color.
  - It also trims the black bars, so every photo sits cleanly in its tile, without editing any image files.
- Cards show the category, a serif name, the price, and **color swatches** (from the real color names), plus a **Low stock** or **Sold out** badge when it applies.
- On hover, a card lifts, its photo zooms slightly, and a **View details →** bar slides up.

**Product detail page**
- A large photo with **hover-to-zoom**, which magnifies around the pointer so you can see a logo or fabric.
- A serif name, the price, and a stock pill (*In stock*, *Limited sizes*, or *Sold out*).
- Color chips with swatches. The selected size turns solid navy, sold-out sizes are dashed and crossed out, and low-stock counts are highlighted.
- A new **"Ask the assistant about this item"** button, plus a "Complete the look" section for related products.
- This replaces the outdated note saying the assistant was "on its way".

**Chatbot**
- A navy header with a "CC" avatar and an online dot, cream message area, softer bubbles, serif product names in chat cards, and gold typing dots.
- **Starter questions** appear before the first message. They are general ones ("Show me quarter-zips"), or product ones on a product page ("What colors does this come in?").
- The floating button now reads **"Ask our assistant"** and pulses gently three times to get noticed. The docked sidebar from Problem 9 is kept.

**Motion (subtle, and switched off for people who prefer reduced motion)**
- Sections fade up as they scroll into view, and product grids appear with a short stagger.
- Buttons lift slightly on hover, and the chat panel slides in.
- The ribbon scrolls and the seal floats slowly; neither moves when reduced motion is on.
- Hover-only effects are turned off on touch screens.

**Mobile**
- Two-column product grids.
- The hero becomes one large photo with two smaller ones underneath.
- The chat button shrinks to an icon, and decorative extras are hidden so they never cover anything.
- Tested at 375 px with no sideways scrolling.

## Why this should help people browse longer and buy

- **Trust at first glance.** A cohesive, crafted look (consistent photo frames, elegant type, no visible black boxes) makes a small store feel established. Shoppers are more willing to buy from a store that looks professional.
- **More paths into the catalogue.** Category tiles, featured picks, the family row, related products, and assistant suggestions each give the shopper another reason to keep clicking instead of leaving.
- **Answers before doubts.** Swatches, stock badges, and the per-size stock pill answer "do they have my size or color?" right on the card or page, which removes common reasons to hesitate.
- **The assistant is easy to find.** It sits in the hero, the homepage panel, each product page, the footer, and the starter chips. Shoppers who are unsure get personal help, which usually turns browsing into buying.
- **Gift shopping is a strong motivator.** The family row and the milestone banner speak directly to parents and relatives, who are a key audience for Yale merchandise.
- **Small moments of delight.** Hover zoom, card lifts, and gentle reveals make browsing feel responsive and enjoyable without slowing anyone down.

## Testing

**Problem 10 browser suite: 20/20 checks passed, no browser console errors.**
- **Look and content:** the fonts and cream/navy colors load, and the homepage shows real data (6 categories, 102 styles).
- **Photos and hover effects:** letterboxed photos are cleaned up, and the card hover lift and "View details" reveal work. The product photo zooms on hover.
- **Shop features:** the category filter, search, and *Clear filters* still work.
- **Product page:** size selection is correct (L: 20 in stock), and color swatches appear.
- **Assistant:** the product-page *Ask the assistant* button opens the chat with product starters, and "What colors does this come in?" gets the right answer (navy blue and white). The homepage example questions open the chat and put the results on the page.
- **Accounts:** log in and log out still work.
- **Mobile:** no sideways scrolling on Home, Shop, or the product page, and the phone menu works.

**Problem 9 browser suite: 14/14 checks passed.** This covers the docked chat, results surviving a refresh, vague searches, and follow-up questions.

**Bug found and fixed during testing.** The Shop search box sometimes lost letters when typed quickly ("navy" became "y"). It kept its text in the page address and read it back after every keystroke, and the address lags behind fast typing. The box now keeps its own text and copies it to the address, and *Clear filters* still resets it. This was checked 8 times in a row, and is part of the suite above.

## Screenshots (`output/screenshots/`)

| # | Shows |
|---|---|
| 44 | Homepage hero (desktop) |
| 45 | Full homepage (desktop) |
| 46 | Shop page with a card's hover state |
| 47 | Product detail page with size L selected |
| 48 | Product page with the docked, restyled chat answering a starter question |
| 49 | Homepage example question giving results on the page next to the chat |
| 50 | Log-in page |
| 51–53 | Home, Shop, and product page on a phone |
| 54 | Full homepage on a phone |
| 55 | Phone menu |
| 56 | Chat on a phone, with starter questions |

Screenshots 38–43 (Problem 9) were also retaken and now show the new design.
