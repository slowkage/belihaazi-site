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

## Photos

- Fieldwork collage: `content/utkarsh/fieldwork` (the first 8 photos, in file-name order, make the collage)
- Talk photos: `content/utkarsh/talk-photos` (`portrait.jpg` is the photo at the top of the Utkarsh page)

## If something looks wrong

- Open the **Actions** tab on GitHub. A red cross means the last build failed; click it to see why. The live site stays as it was until a build succeeds.
- To undo a change, open the file's **History**, pick the earlier version and restore it.
- **Actions → Build and publish → Run workflow** rebuilds the site by hand.
