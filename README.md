# belihaazi.com

Personal website of Utkarsh Singh: the life of Utkarsh and the mind of belihaazi.

- `content/` is everything that appears on the site. See [UPDATING.md](UPDATING.md).
- `site/` holds the page designs.
- `scripts/build.py` turns `content/` into the finished site in `dist/`.
- `.github/workflows/deploy.yml` builds and publishes to GitHub Pages on every change and every morning.

Build locally: `pip install -r requirements.txt && python scripts/build.py` (add `--offline` to skip Medium, YouTube and paintings).
