# Updating belihaazi.com

Everything on the site comes from the `content` folder. Change something there and the site rebuilds and goes live on its own, usually within 2 minutes. You never touch the design files.

You can do all of this in the browser on github.com. No software to install.

## Add a new piece (POV, prose or poem)

1. Name the Word file the way you always have: `Title_month_year.docx`, for example `The sherlocks of today_april_2026.docx`.
2. On GitHub, open the right folder:
   - POVs: `content/utkarsh/povs`
   - Prose: `content/belihaazi/prose`
   - Poems: `content/belihaazi/poems`
3. Click **Add file → Upload files**, drag the Word file in, and click **Commit changes**.

That's it. The first image inside the Word file becomes the cover. If there's no image, add the title to `content/art.json` with a painting to look up (see below), or the site paints one for it.

A new POV goes on the first shelf by default. To shelve it properly, add a word from its title to the right shelf in `content/utkarsh/shelves.json`.

To fix a title that came out wrong (Google Drive turns `?` and `'` into `_`), add a line to `content/titles.json`:
`"What the filename says": "What the title should be"`

## Add a talk

1. Upload the poster to `content/utkarsh/talks`.
2. Open `content/utkarsh/talks.json`, click the pencil icon, and copy one block to the top:

```json
{"date": "12 Dec 2026", "title": "Talk title", "where": "Organiser or place", "poster": "poster-file-name.jpg", "link": ""},
```

For a recorded talk on YouTube, use `"youtube": "VIDEO_ID"` instead of `"poster"`. The video ID is the part after `youtu.be/`.

## Add a spoken word piece or song

Open `content/belihaazi/spoken-word.json` or `hip-hop.json` and add to the top of `items`:

```json
{"title": "Title", "year": 2026, "link": "https://www.instagram.com/reel/XXXX/", "cover": ""},
```

For a cover image, upload it to `content/belihaazi/covers` and put its file name in `"cover"`. Clicking the card plays the reel on the site.

## Medium

Nothing to do. The site checks Medium every morning at 6 am and adds new posts with their cover images. Older posts that Medium no longer lists are kept in `content/belihaazi/medium.json`.

## Paintings for pieces without an image

`content/art.json` pairs a title with a public-domain painting, which the site finds on Wikimedia Commons:

```json
"Title of the piece": {"search": "Van Gogh Wheatfield with crows 1890", "paint": "crows"},
```

`paint` is the back-up brushwork if the painting can't be found: `night`, `wheat`, `almond`, `crows` or `cypress`.

## Booking link and contact

`content/utkarsh/profile.json` holds your email, your current role and the Google Calendar booking link (`booking_link`).

## "What I solve"

`content/utkarsh/solve.json` holds the "What I solve" section on the Utkarsh page: the opening line, the problems under Brand / Sales / Product / Programmes, the industry tags, and the scale line. Edit the words in quotes; keep the commas and brackets as they are. The same text feeds what Google and AI tools read about what you do.

## Logo reel in "What I solve"

The logos live in `content/utkarsh/logos/` and their order is the `logos` list in `content/utkarsh/solve.json`. To add one: upload a PNG with a transparent background (black works best), then add a line like `{"file": "brand.png", "name": "Brand"}` to that list. The reel always ends on "& more".

## 1001 Stories reports and their concepts

`content/utkarsh/reports.json` lists the report cards. A report with a `concepts` list gets its own page at `belihaazi.com/reports/<slug>/`, readable by search engines and AI tools, and opens in a reading window with a button through to 1001 Stories. Each concept needs:

- `name`: e.g. "The Daily Googly"
- `kind`: e.g. "Context shift #4", "Principle #1", "Concept"
- `page`: the PDF page it comes from (shown as the source)
- `def`: the definition, in the report's words
- optional: `quote` + `by` (+ `qpage`), and `aka` for other spellings people might search

Also give the report a `slug`, `authors`, `summary` and `link` (the 1001 Stories page). Add `source_pdf` if the PDF has a public link, so each source jumps to the right page.

## Likes, comments and new-post emails

These live in a free Supabase database. Readers don't need an account to like, comment or subscribe.

**One-time setup**
1. Create a free project at supabase.com (region: Mumbai).
2. Supabase → **SQL Editor** → paste all of `supabase/setup.sql` → **Run**.
3. Supabase → **Project Settings → API**. Copy the **Project URL** and the **anon public** key into `content/utkarsh/profile.json` as `supabase_url` and `supabase_anon_key`. (The anon key is meant to be public; the database only lets it like, comment and subscribe.)
4. For emails: create a free account at resend.com, add the domain `belihaazi.com`, and add the DNS records it shows you in GoDaddy. Then create an API key.
5. GitHub → this repo → **Settings → Secrets and variables → Actions** → add three secrets: `SUPABASE_URL` (the Project URL), `SUPABASE_SERVICE_KEY` (the **service_role** key from step 3; never put this one in a file), `RESEND_API_KEY`.

The first publish after step 5 only records the posts that already exist. After that, anything new you add (a Word file, a report, a Medium post) is emailed to subscribers once, after the site publishes.

**Day to day**
- Hide a comment: Supabase → **Table Editor → comments** → untick `visible`. Delete the row to remove it for good.
- See who subscribed: **Table Editor → subscribers** (`active` is false for people who unsubscribed).
- Want to approve comments before they show? In the SQL Editor run `alter table comments alter column visible set default false;` and tick `visible` on the ones you approve.

## Photos

- Fieldwork collage: `content/utkarsh/fieldwork` (the first 8 photos, in file-name order, make the collage)
- Talk photos: `content/utkarsh/talk-photos` (`portrait.jpg` is the photo at the top of the Utkarsh page)

## If something looks wrong

- Open the **Actions** tab on GitHub. A red cross means the last build failed; click it to see why. The live site stays as it was until a build succeeds.
- To undo a change, open the file's **History**, pick the earlier version and restore it.
- **Actions → Build and publish → Run workflow** rebuilds the site by hand.
