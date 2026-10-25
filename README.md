# Web CV

Daniel Odin's CV as a static website on GitHub Pages, with a downloadable one-page PDF.

## Edit the content

All content lives in `cv.json`. Both the website and the PDF are generated from it.

- `pdf: false` on an education entry keeps it off the PDF.
- `pdfSummary` is the short text the PDF shows instead of the full description.
- `site.accent` is `blue`, `green` or `orange`.

## Build locally

```
python build.py          # website in _site/
python build.py --pdf    # also prints _site/Daniel_Odin_CV.pdf with Edge/Chrome
```

Open `_site/index.html` in a browser. Only the Python standard library is needed. If the browser
is not found automatically, set `CV_BROWSER` to its path.

## Change the layout

`site.layout` in `cv.json` picks `templates/<layout>.html` and `assets/layouts/<layout>.css`:

- `hero`: full-width photo banner, overlapping headshot, tabs under the header.
- `sidebar`: fixed left column with cover photo, headshot, tabs and buttons (a header on phones).

The section HTML and styling (about, experience, education, publications) are shared and live in
`build.py` and `assets/base.css`, so a layout only defines the page structure around them. To add
a new design, add a template + CSS pair and change `site.layout`.

## Publish

Every push to `main` runs `.github/workflows/pages.yml`, which builds the site and the PDF and
deploys them to GitHub Pages (Settings → Pages → Source: GitHub Actions).

## Private PDF

A version with phone number and email is built in a separate private repository that checks out
this one and runs `python build.py --private private.json --pdf`. Personal contact details are
never stored in this repository.
