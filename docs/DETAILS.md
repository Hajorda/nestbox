# Nestbox: technical notes and reference

A personal tool that finds, ranks and helps you contact rental flats near **EUROCONTROL (Haren, Brussels)** for a short stay
(default: 1 Nov 2026 to 30 Apr 2027, two people, budget up to €1,300 including charges).

It collects listings from Immoweb, Immovlan and 2ememain, reads the listing texts, uses Google Gemini to spot deal-breakers
(1-year minimum lease, one person only, no address registration...), scores every flat, and gives you a web page with
ready-to-send messages in French, Dutch and English, status tracking, notes and an automatic schedule.

Runs only on your own computer. Python standard library only, nothing to install.

---

## Quick start

```bash
cd brussels-flat
cp .env.example .env          # then put your Gemini key after GEMINI_API_KEY=   (optional, see "Gemini")
python3 serve.py              # keep this window open
```

Open **http://127.0.0.1:8765/control**, fill in "Your details", press **Scrape now**. When it finishes, open the **Listings** tab.

Requirements: Python 3 (tested with 3.14) and internet access. Notifications use macOS (`osascript`). On other systems everything
works except desktop notifications.

---

## The two pages

Both pages have a **Listings | Control panel** tab bar at the top.

### Listings (`/`)
- **Contact now**: the best 10 flats you have not contacted yet (text-checked ones first).
- Sticky banner: how many good flats are still waiting, plus counts of contacted / replied / visits / applied.
- Each card shows score, price (rent + charges), commute estimate, size, flags, Gemini's one-line summary, agency phone (Immoweb), and:
  - **copy message (FR / NL / EN)**: copies a filled-in first message and marks the flat as `contacted`. French is the default for Brussels
    communes, Dutch for Diegem, Machelen, Zaventem, Sint-Stevens-Woluwe and Vilvoorde.
  - **status dropdown**: new → contacted → replied → visit → applied → rejected.
  - **notes box**: saved automatically (who you spoke to, visit time...).
- **Contact buttons on each card**: *copy message* (FR / NL / EN), *call* with a hint about good call times (the agency's own hours if the listing gives them, otherwise weekdays 9:00-12:00 and 14:00-17:30), and *WhatsApp* for the flats with a Belgian mobile number: it copies your message first and then opens the chat, you paste it and press send. Nothing is ever sent for you.
- **NEW tag**: a listing put online in the last `new_days` days (default 7, set in the control panel), using the site's creation date where it shows one (Immoweb, Immovlan, 2ememain "today/yesterday"), otherwise its last update date (the tag's tooltip says which). The Contact now list puts NEW listings first.
- **Follow-up reminders**: a flat you contacted that has not answered after 2 days appears in "Follow-ups due" with *copy follow-up* buttons (FR / NL / EN). Copying it resets the timer; a second reminder comes 3 days later, then it stops. The scheduled run also sends a Mac notification when follow-ups are due.
- Stats panel at the top (collapsible, and it stays closed once you close it): listings found, good matches, your progress, quality, prices, by source and by area.
- Filters: free-text search, price range, bedrooms, minimum size, commute, score, value points, real cost, free-by date, updated within N days, status, area, source, must-have tags (furnished, short stay OK, registration allowed, fridge, ask about lease length, text read, checked by Gemini, new today) and hide switches. Quick views (best value, cheapest, short stay, ask about lease length, closest...). Sort by score, value points, price, real monthly cost, commute, size, price per m2, newest, recently updated, available soonest or bedrooms, in either direction. Filters are remembered in the browser; Reset filters clears them.
- While a scrape runs the tab bar shows "scraping..." and afterwards "new results ready, reload".

Statuses and notes are saved in `statuses.json` when you use the page through `serve.py` (browser storage is used as a fallback).

### Control panel (`/control`)
- **Scrape now** with options: notify, Gemini on/off, "re-score only" (no requests to listing sites), how many listing pages to read, one-off budget.
  Live log, Stop button.
- **Automatic runs**: on/off, every 2 h to once a day, allowed hours, notifications, Gemini.
- **Search settings**: budget, minimum size, result pages per area, listing pages and Gemini analyses per run, commute limit for reading texts,
  notification threshold, which of the 14 areas to search.
- **Your details**: names, signature, phone, email, visit times, move-in/out dates. These go into the copy-message texts.
  After saving, run **re-score only** to rebuild the messages.

---

## Command line

Everything the control panel does can also be done from a terminal:

```bash
python3 scraper.py                 # normal run
python3 scraper.py --offline       # re-score saved listings, no requests to listing sites (Gemini still runs)
python3 scraper.py --details 260   # read up to 260 listing pages this run (default from config.json, ~3 s each)
python3 scraper.py --no-ai         # skip Gemini
python3 scraper.py --no-details    # skip reading listing pages
python3 scraper.py --notify        # macOS notification for new high-score flats
python3 scraper.py --max 1200      # budget for this run only
```

Output: `listings.html` (the page), `listings.csv` (spreadsheet), `run.log` (last run).

---

## How it works

1. **Search**: the sites do not return newest first, so for each area it reads the first 2 result pages and keeps going (up to `max_pages_per_area`, default 4) while the area has more listings, so new flats are not hidden on page 3. For each enabled area, Immoweb (normal + furnished-only search), Immovlan, and the newest 2ememain rental ads within 15 km of EUROCONTROL.
2. **Read**: for the best-scoring unread candidates (in budget, within `read_max_minutes` commute) it opens the listing page and keeps the full description,
   furnished/kitchen/availability data and, on Immoweb, the agency phone, website and contact hours. Results are cached in `state.json`.
   Pages are read **site by site in parallel** (Immoweb, Immovlan, HousingAnywhere, Spotahome at the same time, but still only one request at a time per site, 2-4 s apart), and each page is sent to Gemini **as soon as it has been read**, while the next pages are still downloading. Reading and analysing overlap, so a run takes about as long as the slower of the two, not the sum. Gemini still works one analysis at a time (about 4.5 s each), so with a very high "Gemini analyses per run" it becomes the slower part.
3. **Gemini**: reads each description once (cached by text hash) and returns typed facts: minimum lease months, registration allowed,
   two people OK, shared accommodation, short stay OK, furnished, fridge, plus a one-line summary.
4. **Score and flag** (below), de-duplicate flats listed on several sites, estimate the commute.
5. **Catalog**: every listing is remembered. A listing not found in 2 consecutive runs is marked **possibly taken** (call to confirm).
   Nothing is marked if a site blocked us or a search returned no results, so a wifi drop cannot mark everything as taken.

### Score
Starts at 100. Roughly:

| Effect | Points |
|---|---|
| Each €10 above €900 total | -1 |
| Each commute minute above 15 | -0.9 |
| Furnished / short-term accepted / registration allowed / fridge / text checked | +18 / +15 / +10 / +4 / +3 |
| No registration | -60 |
| Long lease only (12+ months) | -30 |
| One person only, students only | -40 |
| Shared flat, room, co-living, kot | -80 |
| Minimum lease 6-8 months | -12 |
| Smaller than `min_m2` | -15 |
| Under €550 (check for scam) | -10 |
| Available much later than your move-in | -10 / -30 |
| Over budget | -50 |

"Good" = within budget and no red flag (no registration, long lease only, one person only, students only, shared).

### Run history, logs and Gemini cost
Every scrape is recorded in `history.json` and its full text log is kept in `logs/` (the newest 40), however it was started
(control panel, schedule or terminal). The control panel shows the table: when, how it was started, how long it took, requests to the listing sites,
listings found, listings added (never seen before), listings that became "possibly taken", listing pages read, Gemini analyses with their tokens and
estimated cost, and how many live / good / new listings there were afterwards. Click "log" on a row to read that run's log.

The cost is tokens x the price in `config.json` (`gemini_price`: $0.30 per million input tokens and $2.50 per million output tokens, figures from third-party
sources, not confirmed on Google's page). On the free tier you pay nothing, but Google may use free-tier prompts to improve its products.
A typical analysis is about 430 tokens in and 150 out, so 40 analyses cost roughly 2 cents if billed.

### Listings without text, and ads in another language
Immoweb keeps an ad's text in the language the seller wrote it in. If the main description is empty, the other-language text is used (English, French, Dutch, German, then any). A page that was read but has **no description at all** is marked "no description in the listing" (an orange tag) instead of "text not checked", and is not retried on every run. Wording such as "à louer chambres pour étudiants", "chambres à louer", "rooms for rent" or "kamers te huur" is treated as a room, not a flat.

### Run history: page rebuilds
Quick re-scores that read nothing and ask Gemini nothing (about 3 seconds, for example after a rules change) are hidden in the run history table by default. Tick "also show page rebuilds" to see them.

### Marking, adding by link and reporting wrong
- **Mark (★)**: press the ☆ on a card. Marked flats appear in the **★ Marked** tab (sorted by when you marked them, best score, best value or price), whatever the filters say, with your status and notes. The tab shows how many you have marked.
- **Add a listing by link**: open "＋ Add a listing by link" at the top, paste the address of one listing (Immoweb in English, French or Dutch, Immovlan, Spotahome, HousingAnywhere, 2ememain) and press Add. The tool opens that page, reads price, size, text and dates, scores it (Gemini checks it first) and adds it with a purple **manually added** pill. Manual listings are never hidden by the filters, never marked "taken" and kept until you press "remove". If a page does not show its rent, type it in the rent box and add the link again. Only these five sites are ever fetched. The list is kept in `manual.json`.
- **Report wrong**: if a tag, price or anything else on a card is wrong, press **⚑ report wrong** and say what is wrong. The card gets a red **marked wrong** pill and a note with your words and the tags it had at that moment. Press **↻ recheck** to read the listing page again and re-analyse it (a fresh Gemini check, no search); the wrong mark **stays** so you can compare the new tags with the old ones, until you press **remove wrong mark**. The filter "Marked wrong by me" lists them, and the stats panel counts them. Rechecks are recorded in the run history.

### Costs, deposit and availability
Each card shows what the listing really costs, not just the rent. Listing data always beats the description text (descriptions, especially the AI-written ones on Immovlan, can quote other numbers).

- **Deposit**: from the listing's own data (Immovlan "Rental deposit", HousingAnywhere) or, failing that, from the text ("security deposit of €3,000", "garantie locative: 2 mois", "huurwaarborg"). Flagged when it is above 2 months of rent, the Brussels cap.
- **Extra monthly costs**: HousingAnywhere publishes the exact monthly extras (electricity, gas, water, internet and "other additional costs"); they are added to the real cost. Elsewhere, "utilities not included" without a figure adds the estimate from config.json (`utilities_estimate`), and "other monthly costs" without an amount adds `unknown_extra_estimate`. Both are marked as estimates.
- **Couple surcharge**: a sentence like "an additional monthly charge of €125 applies for couples" is read and added to the real cost, because you are two people.
- **One-off fees**: HousingAnywhere's platform fee and admin fee are read exactly (replacing the assumed percentage); agency, file or contract fees in the text are added too. **Upfront cash** on the card = deposit + first month (with extras) + one-off fees.
- **Price check**: if the description quotes another rent than the listing data, the card gets "text and listing disagree on price".
- **Availability**: Immovlan's "Availability From 15/01/2027" and HousingAnywhere's bookable date are read. A flat free more than 14 days after your move-in gets "free later than your move-in" and loses points; free more than `max_late_days` (default 45, set in the control panel) after your move-in it is **dropped from the good list**. Unknown availability is shown as "not stated".
- **Bedrooms and size**: from the listing data; if the seller left them out, a clear statement in the text is used (marked with *), and a listing that says "1 room" is shown as a studio. Otherwise the card says the seller did not give it.
- **HousingAnywhere pages** are now read like the others (exact costs, minimum and maximum stay, private or shared bathroom, kitchen and toilet, couples allowed, washing machine, size, bookable date). The same flat listed on Immovlan and HousingAnywhere is merged into one card that keeps the details of both.
- **Show more**: the list loads 50 flats at a time and more load automatically as you scroll, or press "Show 50 more" / "Show all". If the page hits an error it shows a red line at the top.

### Map
The **🗺 Map** tab (address `/#map`) draws the flats that match your filters on the Listings tab as pins on an OpenStreetMap map, with EUROCONTROL (black ring) and the tram 62 stops (grey dots).
Colour the pins by match score or by value points (green best, blue very good, orange okay, red weak); a gold ring marks ★ flats; click a pin for price, real cost, commute, key tags and a mark button.
Pins with a **pale dashed** look have only an approximate position (the centre of their area, spread a little so they do not stack) because the listing gave no exact location; untick "include approximate positions" to see only exact ones.
It needs an internet connection: the page loads Leaflet 1.9.4 from cdnjs (checked with an integrity hash, so only that exact file runs) and the map tiles from openstreetmap.org (light personal use is fine under their policy; attribution is shown on the map).

### What is a good score?
Measured on the good flats found on 17 Oct 2026 (the numbers move a little as listings change):

| Match score | Meaning | Value points | Meaning |
|---|---|---|---|
| 100 or more | excellent (top 10%) | 53 or more | excellent (top 10%) |
| 80 to 99 | very good | 47 to 52 | good |
| 60 to 79 | okay (the middle) | 40 to 46 | average |
| under 60 | weak, probably a catch | under 40 | below average |

Value points are lower than they look: a flat would need to be cheap, big, close, furnished and efficient all at once to pass 65.

### Catching shared flats and rooms
A flat is dropped from the "good" list when its title, type or description shows that you would share the kitchen, bathroom or living space (flatmates,
colocation, co-living, kot, "shared flat/house/kitchen/bathroom", "share the kitchen with", "chambre dans une colocation", "gedeelde keuken", a room in a house...).
Shared laundry, shared garden or terrace, bike rooms and "common areas" in the charges are normal for a whole flat and do **not** count.
Gemini double-checks the descriptions it reads and quotes the phrase that shows the sharing (hover over the red "shared" tag to see it).
Softer wording such as "room available" or "price per room" gives an orange "maybe shared: check" tag and −10 points.

The weak spot is listings whose text has **not been read yet**: a shared flat can hide there. So "Contact now" only lists flats whose text has been read, and tells you how many more are waiting.
Raise "Listing pages read per run" in the control panel (or run `python3 scraper.py --details 150`) to clear them faster.

### How descriptions are read
All keyword rules live in `describe.py` (French, Dutch and English), and every rule keeps the phrase it was triggered by.

- **Negation is understood**: "no shared kitchen", "pas de colocation", "geen gedeelde keuken", "non meublé", "semi-furnished", "no washing machine" do not count as positives.
- **Your sharing rules**: a flat is either whole or shared. A shared **kitchen, bathroom, shower or toilet** means a shared flat. "Room for rent", "private room", "chambre à louer", "kamer te huur", flatmates, colocation, co-living and kot count as shared. Shared garden, bike room and "common areas" in the charges do not.
- **Laundry**: a **washing machine inside the flat** gives a green tag and +4 points (and +3 value points). A **shared laundry room** is fine and only gets a grey tag, no penalty. A **machine connection** ("aansluiting voor wasmachine", "raccordement lave-linge") is not a machine and gets a grey tag.
- **Listing data beats text**: on Immoweb, the kitchen fields "has washing machine" and "has fridge" are used when the listing filled them in.
- **Evidence**: hover over any tag to see the phrase it came from. Each card with a read text has **"read the description"**, which shows the full text with the key phrases marked: red = deal-breaker, orange = check, green = good, grey = info.
- Descriptions are stored up to 8,000 characters, and Gemini reads up to 6,000. Gemini double-checks sharing, laundry, lease length and registration, and quotes its evidence.

### Value points (price-performance, 0-100)
A second number on every card ("value 63"), separate from the match score. The match score asks "does this flat fit my needs?",
the value points ask "what do I get for my money?". Hover over the number for the exact breakdown.

| Part | Max | How |
|---|---|---|
| Cost | 40 | Based on the **real monthly cost** (below): 600 EUR or less = full points, your budget = 0 |
| Size | 15 | Total m2 for two people: 20 m2 = 0, 50 m2 or more = full. Unknown size = 6 |
| Layout | 10 | Studio 4, 1 bedroom 8, 2 or more bedrooms 10 (a room each). Unknown = 5 |
| Commute | 15 | 10 minutes = full, 60 minutes = 0 |
| Included | 15 | Furnished 5, bills included 3, fridge/equipped kitchen 2, washing machine in the flat 3, short stay accepted 2 |
| Energy | 5 | EPC A/B 5, C 4, D 3, E 1, F/G 0, unknown 2 |

A deal-breaker (no registration, one person only, shared, wrong location...) caps the value at 25.

**Real monthly cost** = rent + charges
+ utilities estimate (HousingAnywhere and Spotahome prices exclude utilities unless the card says "bills included"; default 120 EUR)
+ furniture/linen allowance for unfurnished flats (default 100 EUR a month, half if the text has not been read)
+ the platform's one-off fee divided by the months of your stay.

Platform fees are **assumptions you can edit** in the control panel:
- HousingAnywhere publishes 25-40% of the first month's rent (minimum 175 EUR), charged when the landlord accepts you.
- Spotahome publishes no tenant fee formula. 20-30% is a third-party figure and is **not confirmed**: check the booking fee at checkout.
- Immoweb, Immovlan and 2ememain landlords: no fee is added. Ask whether an agency charges any file or contract fees before you sign.

### Commute
An estimate, not a timetable. It takes the best of walking, tram 62 (stop positions in `data/tram62.json`, from OpenStreetMap), and a generic
bus/train speed. Set `eurocontrol_shuttle` to true in settings only if the free EUROCONTROL shuttle from the city centre is confirmed to run.
Check the real route in the STIB app before a visit.

---

## Gemini setup (optional but recommended)

1. Create an API key in Google AI Studio.
2. Put it in a file named `.env` next to `serve.py`:
   ```
   GEMINI_API_KEY=your_key_here
   ```
   (or export `GEMINI_API_KEY` in the shell). Do not share this file; `chmod 600 .env` keeps it private.
3. The model is `gemini-2.5-flash` (`gemini_model` in settings). If Google retires it, change the name; a 404 stops the run's AI step with a clear message.

What is sent: only the public listing title and description. Nothing about you. Listing text is treated as untrusted, and only strictly typed fields
come back into scoring. Without a key the tool still works with keyword matching only.

---

## Automatic runs

Two options, use either:

- **Control panel schedule** (simplest): works while `serve.py` is running and the Mac is awake. Minimum interval 2 hours.
  Pauses itself for 24 hours if a site blocks or rate-limits.
- **macOS background schedule** (works when `serve.py` is closed): `./install_schedule.sh on` runs the scraper at 08:30 and 18:30
  and `./install_schedule.sh off` removes it. Output goes to `scheduled.log`.

---

## Being a polite visitor (please keep it this way)

- Only public search and listing pages that each site's `robots.txt` allows; price and sort filters are applied on your computer instead.
- One request at a time, 2-4 seconds apart, a few hundred requests per run at most. 2-4 runs a day is plenty.
- On the first 403 or 429 response the site is skipped for the rest of the run. If you see a block, wait a day.
- Phone numbers are read only where the page already contains them. Nothing hidden behind a "show number" button is revealed.
- Sites' terms of use may still restrict automated access. This is a low-volume personal tool; use it that way, and do not share or resell the data.
- Zimmo blocks automated access, and Facebook groups cannot be searched; check those by hand.

---

## Files

| File | Purpose |
|---|---|
| `serve.py` | Local web server, control API, scheduler. Listens on 127.0.0.1 only, rejects foreign Host/Origin headers |
| `scraper.py` | Main program (the options above) |
| `sources.py` | Immoweb, Immovlan, 2ememain fetching and parsing |
| `scoring.py` | Flags, commute estimate, score, de-duplication |
| `gemini.py` | Gemini description analysis |
| `messages.py` | FR / NL / EN message texts |
| `report.py` | Builds `listings.html` and `listings.csv` |
| `control.html` | The control panel page |
| `config.json` | Settings and your details (edited from the control panel) |
| `schedule.json` | Automatic-run settings |
| `state.json` | Catalog of listings, cached texts and Gemini results, first-seen dates |
| `statuses.json` | Your statuses and notes |
| `data/tram62.json` | Tram 62 stop positions |
| `landlord-templates.md` | Message and phone-call templates, red flags, vocabulary |
| `.env` / `.env.example` | Gemini key |
| `install_schedule.sh`, `run_scheduled.sh` | Optional macOS background schedule |

---

## Safety when renting

- Never pay before you have visited and signed. Deposit goes into a **blocked bank account in your name** (max 2 months), never cash to the landlord.
- Check the flat allows **registering your address** with a main-residence lease, in writing, before you sign. You will need it at the commune.
- Suspiciously cheap flats, landlords abroad, or payment by transfer to a foreign account are scam signs. The tool tags very cheap listings, but it cannot detect scams.
- A listing's text can be wrong or outdated. Gemini and the keyword checks only read what the listing says; always confirm the lease length, registration and fridge with the landlord.

---

## Troubleshooting

| Problem | What to do |
|---|---|
| "no key in .env: skipped" on the control panel | Create `.env` with `GEMINI_API_KEY=...`, reload the control page |
| Gemini step says HTTP 404 | Change `gemini_model` in settings |
| Gemini step says quota reached | Wait, or lower "Gemini analyses per run" |
| "BLOCKED" in the log | A site rate-limited us. Wait a day; automatic runs already pause |
| `nodename nor servname provided` in the log | Your internet dropped; run again |
| Page shows old data | Click "new results ready, reload", or reload the page |
| Copy message has `[placeholders]` | Fill in "Your details" in the control panel, then run "re-score only" |
| Many listings show "text not checked" | Run with `--details 260` (about 13 minutes) |
| No notification appears | System Settings → Notifications → allow Terminal (or the app running `serve.py`) |
| Port 8765 already in use | `pkill -f serve.py`, then start it again |

---

## Limits

- Results depend on what the sites show. Good flats can be gone within a day.
- Whether a landlord accepts your stay length (6 months with a 1 Nov start), the registration, and the fridge are only certain after the landlord answers.
- Immovlan listings often lack bedroom count and size until the listing page has been read.
- Commute times are estimates.
- The "possibly taken" mark is a guess based on absence from search results.

## 🎉 Today tab (motivation)

See [FUN.md](FUN.md). Setting up the shared copy is in [SHARED_COPY.md](SHARED_COPY.md).

## Faster, politer scraping

- **Parallel search:** the five sites are searched side by side (one thread per site, one request at a time per site, same 2-4 s pause), so a full search takes about the time of the slowest site (about 3 minutes instead of 6-7).
- **Change detection:** when a listing page is read, a fingerprint of what the search shows (price, charges, title, last-modified date) is stored. A cached page is read again only when that fingerprint changes. The run log says how many cached pages were skipped.
- **Retry backoff:** a page that fails to read is retried next run, then after 1 day, then after 3 days, and is given up on (until the ad changes) after 5 failures.
- **Possibly taken:** a listing missing from a search counts as one miss at most every 6 hours, so several runs in a row cannot mark it taken.

## Link your Gmail (replies show on the right flat)

Nothing is added to your emails: no codes, normal subjects. The **✉ Gmail** button on a card opens a Gmail compose window with the message and a normal subject (for example "Viewing request – Rue … 9, 1200 Woluwe"). Replies are found in your inbox (read-only) by what is already in them: the flat's address with a house number or its listing number (strong match), a thread that started from your message (its later messages follow), or the agency's name (weak match: shown as "possible reply", you press "it is this flat" or "not this flat").

When a reply is found: a macOS notification, the flat's status becomes **replied** (also on the shared copy, with a point in the Today tab) and the card shows the sender, the time and the first lines with an "open in Gmail" link. The mail text stays on your Mac (`mail.json`); the shared copy only learns the status.

Setup, once (also written in the control panel, "Gmail link"):
1. console.cloud.google.com: new project, enable the **Gmail API**.
2. OAuth consent screen: External, add the read-only Gmail scope and yourself as test user, then **Publish app** (otherwise Google signs you out every 7 days; the "unverified app" warning is fine for a private tool).
3. Credentials: OAuth client ID, type **Desktop app**, download the JSON as `gmail_client.json` in the project folder.
4. `python3 mail_link.py connect` and allow read-only access.

`python3 mail_link.py poll` checks once by hand; `python3 test_mail_link.py` tests the matching with a fake inbox. Limits: private ads and form-only contacts often give no address in the reply, so those need the weak match or "it is this flat".


## New: first run, demo, setup, health check

- **Try it first:** `python3 demo.py` builds `demo_site/` with made-up listings and opens it on http://127.0.0.1:8766/. Your real data is never touched.
- **First run:** a fresh download has `config.example.json`; the first start copies it to `config.json`. The page shows a "start the setup" banner and `/setup` asks about your name, budget, dates, workplace and areas (2 minutes). Everything can be changed later in the control panel.
- **Health check:** the control panel starts with a list of what works and what does not (Python, your details, each site's last result, Gemini, shared copy, Gmail, schedule), each with how to fix it, and a button that tests the internet and the sites.
- **Honest errors:** if a site returns 0 (or far fewer) results than usual, a red bar on the listings page says so, instead of quietly listing fewer flats.

## New: everyday use

- **Freshness:** every card says when it was last seen and when its page was read; "possibly taken" explains why and links to the original ad.
- **Why this flat:** one line under each card says why it is good or not.
- **Filters:** saved named filters, chips with a ✕ for each active filter, "Clear all", and "N new since my last visit". On a phone the filters open as a full-screen drawer.
- **Undo:** after a status or mark change a toast offers "Undo" for 7 seconds.
- **Messages:** the control panel's "Messages" section edits the first message and follow-up in FR/NL/EN with a live preview (placeholders such as `{where}`, `{rent}`, `{signature}`); your versions are saved in `templates.json`.
- **History per flat:** copied messages, calls, Gmail drafts, replies, status changes and viewings with times (shared between you and a friend).
- **Viewings:** "📅 schedule a viewing" on a card; the **Visits** tab lists them by day and exports a `.ics` calendar file or opens Google Calendar.
- **Reminders:** how many days before a follow-up reminder, and how many follow-ups, are settings in the control panel.
- **Quiet mode:** the 🔊 Fun / 🔇 Quiet button (or the `q` key) switches off every sound, voice, animation and pop-up at once.
- **Keyboard:** `j` / `k` move between flats, `m` marks, `o` opens the ad, `c` copies the message, `/` searches, `?` lists the shortcuts.
- **Print:** "Print shortlist" on the Marked tab prints a clean list for a viewing day.

## What to do now, pipeline, morning summary, "I found a flat"

- **▶ Next** (first tab): the one page to open every day. In this order: replies waiting for your answer (with "open in Gmail", "I answered", "schedule a viewing"), viewings today and tomorrow (call, calendar, and after the viewing "I want it" / "no"), follow-ups due (the follow-up message one tap away) and the best new flats for you to contact (copy message, Gmail, call, WhatsApp). When you open the page for the first time in a session and something is waiting, it opens on this tab.
- **🗂 Pipeline:** columns new → contacted → replied → viewing → applied → rejected. Drag a card to another column, or tap ⋯.
- **Morning summary:** a notification each morning (default 08:30, while the server runs; if the Mac was asleep, as soon as it wakes) with the number of replies, viewings, follow-ups and new good flats. Switch it off or change the time in the control panel; "Send one now" tests it. With the shared copy and notifications on, it also goes to your phone or browser.
- **🏠 I found a flat:** on a flat's card, "this is the one". Searching, follow-up reminders, the morning summary and the hourly reminders stop; the other flats are archived (shown only if you ask), and nothing is deleted. "Resume searching" undoes it.
- **Scam hint:** a reply from a free-mail address (gmail, outlook...) that talks like a rental platform ("Welcome to HousingAnywhere") is marked "spam". Marketing and welcome emails from platforms are ignored when matching replies.
