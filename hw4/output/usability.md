# Problem 9: Usability Improvements

Four improvements to the Campus Customs website: two in the frontend (React) and two in the AI agent and backend (FastAPI + PydanticAI). Each one fixes a moment where a shopper got stuck, had to repeat themselves, or lost what they were looking at.

| # | Improvement | Where | Main files |
|---|---|---|---|
| F1 | The chat docks beside the page instead of covering product cards | Frontend | `frontend/src/components/ChatPanel.tsx`, `frontend/src/index.css` |
| F2 | Assistant search results stay on the page after a refresh | Frontend + a small API | `frontend/src/pages/ProductsPage.tsx`, `frontend/src/assistantResults.tsx`, `frontend/src/api.ts`, `GET /api/search` in `backend/main.py` |
| B1 | Vague requests like "something cozy" get relevant suggestions | Agent + backend | `backend/tools.py`, `backend/models.py`, `backend/agent.py`, `backend/prompts/prompt.md` |
| B2 | Follow-ups like "Does it come in blue?" understand which product "it" is | Agent + backend | `backend/agent.py`, `backend/main.py`, `backend/history.py`, `backend/models.py`, `ChatPanel.tsx` |

No database tables, columns, products, prices, or stock levels were changed. The only new rows are chat messages for the fictional test account, saved by the existing chat-history feature during testing.

---

## F1: The chat no longer covers product cards

**Before.** The chat opened as a 370 × 520 px box floating in the bottom-right corner, on top of the page. On the Shop page it hid the right-hand column of product cards. Shoppers had to close the chat to see or click those products, and then reopen it to keep talking. Problem 7 made this worse, because the assistant puts its results on the page next to the chat, and some of those results were hidden behind the chat itself.

**What changed.**
- **Screens 900 px and wider:** the open chat becomes a full-height sidebar on the right. The whole page (navbar, product grid, footer) narrows to make room, so product cards reflow beside the chat instead of sitting under it.
  - The chat button marks the page with a `chat-docked` class while the chat is open, and CSS adds right padding equal to the sidebar width.
  - The round chat button is hidden while docked, since it would sit on the message box. The panel's own × closes it, and so does the Esc key.
  - When the chat closes, the page returns to full width.
- **Phones and small tablets:** the chat stays a floating panel, because there isn't room for a sidebar. On phones it already steps aside when the assistant shows results (Problem 7).

**Why it helps.**
- *Customers* can browse and chat at the same time: ask a question, look at the cards, click one, then ask a follow-up, without opening and closing the chat.
- *The business* gets more value from the assistant. It's most useful when shoppers can see what it recommends, and every hidden card was a product nobody could click. More time with the chat open usually means more questions answered and more products viewed.

**Tested on the running site (1440 × 1000).** With the chat open, the panel is the full 1000 px tall. Across 102 product cards on Shop All, **0 overlapped the chat**, and after an assistant search, 0 of 12 results were covered. On a phone (375 × 812) the page isn't narrowed, and the chat steps aside to show results. Screenshots: `38-docked-chat-does-not-cover-products.png`, `39-something-cozy-suggestions.png`, `43-phone-results-visible.png`.

---

## F2: Search results survive a page refresh

**Before.** Assistant results were kept only in the browser's memory, at the address `/products?view=assistant`. A refresh, a reopened tab, a bookmark, or a link sent to a friend lost them, and the page went back to Shop All. A shopper who had found a set of products had to ask the assistant again.

**What changed.**
- **The search is in the address.** The page now opens at `/products?view=assistant&q=cozy`, for example. Normal browser features (refresh, Back and Forward, bookmarks, copying the link) now keep the results.
- **New read-only endpoint `GET /api/search?q=…`.** It runs the same search the assistant uses (`tools.find_products`, which both now share) and applies the same rule for what may be shown: only exact, strong, or "suggestions" matches. Anything weaker returns `total = 0`.
  - Because it's the same search, a refresh shows the same products in the same order the chat showed.
  - It never shows unrelated items, and a link to a search with no matches still shows the "No matching products" message.
- **Fetching on refresh.** When the Products page has a `q` but nothing in memory, it fetches the results while showing a loading grid. If that fails, it shows an error with a **Try again** button. When results are already in memory (straight from the chat), they appear instantly with no extra request.
- **Prices and stock are always current**, because the results are rebuilt from the database each time, never from a saved copy.
- The chat's **"View N products on the page"** buttons, including ones in a signed-in customer's restored history, use the same address. "Show all products" still returns to the full shop.

**Why it helps.**
- *Customers* don't lose their place. Refreshing, going back, or opening the results later just works, and a parent can text "look at these" with a link that shows the same products.
- *The business* keeps shoppers in the flow instead of losing them at a dead end. Fewer repeated questions also means fewer AI calls, and every product link can now be shared.

**Tested on the running site.** I asked the chat for "something cozy" (the address became `/products?view=assistant&q=cozy`), then refreshed: **the same 12 products came back in the same order**, under "Results for 'cozy'". "Show all products" returned to Shop All. Opening `/products?view=assistant&q=socks` showed "No matching products". Screenshot: `40-results-after-refresh.png`.

---

## B1: Better answers to vague requests ("something cozy")

**Before.** The search only matched words that appear in product data, and no product mentions "cozy", "warm", "gym", or "summer" (0 of 102 products). So "something cozy" returned **no match**. The assistant followed its rules and said it couldn't find anything, even though the store has plenty of fleece jackets and heavyweight sweatshirts. A shopper who described a *need* rather than a *product type* got nothing.

**What changed.**
- **The search understands common descriptive words** (`INTENT_GROUPS` in `backend/tools.py`). Each group maps a customer's words to how we read them and to product words that actually fit, with weights so the best fits rank first:

  | Customer says (examples) | Read as | Products that fit (best first) |
  |---|---|---|
  | cozy, warm, winter, cold, comfy, layering | warm, cozy layers | fleece, heavyweight, then hoodies and quarter-zips, then crewnecks |
  | hot weather, summer, lightweight, breathable | lightweight T-shirts | tri-blend tees, then other T-shirts |
  | gym, workout, running, athletic, training | athletic and performance tops | Dry Zone and performance shirts, then sports tees |
  | dressy, interview, office, preppy | dressier pieces | Brooks Brothers, mocknecks, then quarter-zips and the bomber |
  | game day, tailgate, fan, spirit | game-day designs | football, Yale vs Harvard, sports and bulldog designs |
  | retro, throwback, old school | vintage-style designs | the Vintage collection and felt or heavyweight pieces |

- **Ranking:** results are sorted with **in-stock products first**, then by best fit, then by stock level, and capped at 12. The assistant never recommends something the customer can't buy.
- **Concrete details still count.** "Cozy *navy*" or "cozy *gray hoodie*" requires every concrete word to match, and the descriptive word only ranks. Filler words common in vague requests ("something", "nice", "recommend", "weather", and so on) are ignored.
- **Literal matches come first.** The descriptive reading is used only when the customer didn't name a product type. "Hoodies", "Yale Dad Hoodie", and "vintage" still work as before.
- **A new match quality, `"suggestions"`,** with an `interpreted_as` field, for example "warm, cozy layers (fleece, heavyweight sweatshirts, hoodies, quarter-zips)". The prompt tells the assistant to:
  - say in one sentence how it understood the request
  - recommend 2–4 products by name with their real prices and a reason each fits
  - ask **one** narrowing question (color, budget, style, or who it's for)
  - put all the suggestions on the page
- **Guardrails unchanged:** suggestions still come only from the database. The output validator now accepts `"suggestions"` for the page but still rejects "partial" or "none" results. "Cozy socks" still returns no match, because the store doesn't sell socks.

**Why it helps.**
- *Customers* shop the way they think ("something warm for my dad", "something for the gym") and get real, in-stock options with a reason, instead of a dead end or a list of every hoodie.
- *The business* turns vague questions, which come from shoppers who are ready to buy but undecided, into product views. Putting in-stock items first avoids recommending things that can't be sold, and the narrowing question keeps the conversation moving toward a purchase.

**Tested on the running site.**
- "I'm looking for something cozy": the assistant explained it would look at warm layers and suggested the Super Heavyweight Crewneck ($58.00) and two fleece jackets ($98.00) with reasons, then asked "crewneck or a zip-up fleece?". All 12 page results are warm layers, and the top results are all in stock.
- "Something for hot weather" returned T-shirts.
- "A shirt for the gym" returned the Dry Zone Long Sleeve first, then sports tees.
- Screenshot: `39-something-cozy-suggestions.png`.

---

## B2: Follow-up questions understand "it"

**Before.** The assistant saw the earlier conversation only as text. After "How much is the Yale Dad Hoodie?", a follow-up "Does it come in blue?" depended entirely on the AI rereading its own earlier reply, working out the product name, and searching again. Nothing told it which product "it" was, and its rules say to ask a clarifying question when the product is unclear. On a product page, "it" was always read as the product on screen, even if the chat had just moved on to something else.

**What changed.**
- **The backend tracks which product the conversation is about.** After each reply, the server records the product or products that reply was about:
  - its product cards, if it has any
  - otherwise the single product it looked up
  - otherwise a single page result
  - otherwise the previous product, carried forward
  - if the customer moved on to a new search, nothing
- **Signed-in customers:** the product is saved with the reply in the existing `chat_messages.products_json` list, as items with `"shown_as": "context"` (no schema change). Reloaded chat history doesn't show these as cards.
- **Guests:** the server returns `context_product_ids` with each reply, and the chat window sends them back on that turn in the next request. The server **checks them against the catalogue** and drops anything it doesn't recognize. A tampered id is ignored, and the assistant just asks which product the customer means.
- **The agent is told directly.** Each request's "This conversation" instructions now say, for example: "The most recently discussed product is **Yale Dad Hoodie** (product_id …). For a follow-up without a product name… use this product… don't ask them to repeat the name."
  - If the last reply covered several products, the agent uses the only one that fits, or asks which one by name.
  - If the customer is on a product page that differs from the one just discussed, "this one" means the page and "it" in a direct follow-up means the product just discussed.
- **Prompt:** for color questions, answer from the product's real `colors` and name the shade ("navy blue" counts as blue). If it doesn't come in that color, say so and offer similar items.

**Why it helps.**
- *Customers* talk naturally, the way they would to a person in a store, and get a direct answer. Repeating product names is the kind of friction that makes people give up on a chatbot.
- *The business* gets fewer abandoned chats, shorter conversations to reach a decision (price, then color, then size, then buy), and faster, cheaper replies, because the agent looks up the right product immediately instead of searching again or asking.

**Tested on the running site.**
- **Guest:** "How much is the Yale Dad Hoodie?" got "$68.00". "Does it come in blue?" got "Yes—it comes in navy blue, with a white Yale Dad graphic…", with no "which product?". Screenshot: `41-guest-follow-up-does-it-come-in-blue.png`.
- **Signed in (fictional test account):** the same two questions gave the same result. A third follow-up, "Is it in stock in large?", got "in stock in large, with 20 available". The database has 20, and the catalogue lists the colors as navy blue and white. Screenshot: `42-signed-in-follow-up-context.png`.
- **A forged product id** sent from the browser was ignored, and the assistant asked which item the customer meant.

---

## Making sure existing features still work

| Check | Result |
|---|---|
| Chatbot regression suite: prices and stock match the database, cards, partial and no-match handling, privacy, jailbreaks (Problems 5–7) | **52/52 passed** |
| Account suite: register, log in, lockout, hashing, sessions (Problem 4, on a database copy) | **29/29 passed** |
| Memory and page context suite (Problem 8, on a database copy) | **16/16 passed**. One check was updated to count the 6 *new* messages, because the test account already had saved messages from the Problem 8 browser tests. |
| New API checks for Problem 9 (search endpoint, vague searches, guest follow-ups, forged ids) | **13/13 passed** |
| New browser checks for Problem 9 (docking, refresh, vague search, follow-ups for guest and signed-in, phone) | **14/14 passed, no browser console errors** |
| Data unchanged: catalogue + inventory, schema, the original 22 chat rows, the existing test user | All four fingerprints identical to before |

## Limitations and ideas for later

- The descriptive-word groups are a hand-written list. Words outside it ("something fun") still get a normal search and, if nothing matches, a clarifying question. The list could be extended from real chat logs, or replaced with semantic (embedding) search.
- The suggestions ranking can't judge style from photos. For example, it treats all fleece as equally cozy.
- On tablets between 561 and 899 px the chat is still a floating panel. It can cover part of the page there, but it can be closed or moved aside with one tap.
- Follow-up context covers the products from the last reply. Going back to a product from several turns earlier ("the first one you showed me") still relies on the AI reading the conversation.
