# Web CV

Project context for Claude Code. Respond in the language the user writes in (Swedish or English).

## Purpose

Replace the CV on Overleaf with a website hosted on GitHub Pages, with a button that gives a PDF version. Same idea as the car comparison app in the parent folder: static page, data in a JSON file, published by a GitHub Actions workflow on every push to `main`.

Status: built locally (layouts "hero" and "sidebar", currently sidebar; accent blue). `build.py` (stdlib only) turns `cv.json` into
`_site/` and prints the PDF with headless Chrome/Edge. Writing style: third person, English.
Layouts are swappable: `site.layout` → `templates/<layout>.html` + `assets/layouts/<layout>.css`.
Rejected-for-now alternatives (sidebar, magazine) are in the gitignored `mockups/` folder.
Photos: originals in gitignored `images/`; web copies without EXIF in `assets/img/`.
Private PDF: separate private repo `private_cv` (folder next to this one).

## Legal and hosting

Allowed. GitHub Pages is meant for personal sites and a CV or portfolio is a common use. The terms only rule out things like running a commercial service or selling things through it.

## PDF options (decided: combine 1 and 2)

1. **Print stylesheet + `window.print()`.** `@media print` with A4 size, margins and page breaks. The "Download PDF" button calls `window.print()` and the visitor picks "Save as PDF". Text stays selectable, which matters for recruiter systems that parse CVs.
2. **PDF built on every push.** The workflow renders the page to `cv.pdf` with a headless browser (Playwright or Puppeteer) or WeasyPrint and publishes it as a static file. The button is then `<a href="cv.pdf" download>`. Same PDF for every visitor, works on any device. Preferred for a CV.
3. **Browser JS libraries (html2pdf.js, jsPDF).** Avoid: they often rasterize the page, so text is not selectable or searchable and the layout can be blurry.

## Design

- Keep the data separate from the layout, like `cars.json`: a single `cv.json` feeds both the web page and the PDF, so there is only one copy to edit.
- Standard library / no-install approach where possible, as in the car comparison app.
- Responsive page plus print styles. The workflow builds the PDF from the print styles.
- The live site changes whenever the user pushes, so a link sent to an employer shows whatever is live. Attaching the PDF to an application fixes what was sent.
- A custom domain is optional.

## Privacy: the site is public

A private repo does not make a Pages site private on normal plans.

**Fine to show:** LinkedIn link, GitHub link, one work-oriented email address, city or region (e.g. "Stockholm, Sweden").

**Leave out:** phone number, home address, personal number (personnummer). Date of birth and photo only if the user wants them (both are optional in Sweden).

**Email:** public addresses get scraped. Optionally assemble the address in JavaScript so simple scrapers do not find it in the HTML (helps a bit, not foolproof), or use a dedicated address or a form service.

**Two versions from the same `cv.json`:**
- Public: LinkedIn, GitHub, city, one email. Published to Pages.
- Private (optional): adds the phone number and more detail. The user sends it directly to a specific employer. The workflow must not publish it to Pages.

## Next step

The user creates the GitHub repos and commits and pushes themselves. Claude never commits or pushes.
