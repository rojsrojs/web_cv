"""Build the CV website and the printable CV from cv.json.

    python build.py                  -> _site/ (website + cv-print.html)
    python build.py --pdf            -> also prints _site/<pdfFile> with headless Chrome/Edge
    python build.py --private private.json --out _private --pdf
                                     -> only the printable CV, with the extra contact details

Standard library only. The layout is chosen by "site.layout" in cv.json and maps to
templates/<layout>.html + assets/layouts/<layout>.css.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from string import Template
from typing import Any, Final

Json = dict[str, Any]

ROOT: Final[Path] = Path(__file__).resolve().parent
MONTHS: Final[tuple[str, ...]] = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
ACCENTS: Final[dict[str, str]] = {"blue": "#0f6fb8", "green": "#2e7d5b", "orange": "#c2541b"}
# Which icon a contact entry in private.json gets, by its "label" (case-insensitive).
CONTACT_ICONS: Final[dict[str, str]] = {"email": "mail", "e-mail": "mail", "mail": "mail", "phone": "phone"}
# Inner SVG (24 × 24 viewBox) for the link icons in the printable CV header.
ICONS: Final[dict[str, str]] = {
    "pin": '<g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/></g>',
    "mail": '<g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></g>',
    "phone": '<g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></g>',
    "globe": '<g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/></g>',
    "linkedin": '<path fill="currentColor" d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.72V1.72C24 .77 23.2 0 22.22 0z"/>',
    "github": '<path fill="currentColor" d="M12 .3a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2c-3.3.7-4-1.6-4-1.6-.6-1.4-1.4-1.8-1.4-1.8-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 0-.8.4-1.3.7-1.6-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.500 11.500 0 0 1 6 0C17.300 4.700 18.300 5 18.300 5c.7 1.700.2 2.900.1 3.200.8.800 1.200 1.900 1.200 3.200 0 4.600-2.800 5.600-5.500 5.900.4.400.8 1.100.8 2.200v3.300c0 .3.2.7.8.6A12 12 0 0 0 12 .300z"/>',
}
BROWSERS: Final[tuple[str, ...]] = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge", "chrome")
WINDOWS_BROWSERS: Final[tuple[str, ...]] = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)


# ---------------------------------------------------------------- helpers

def e(text: str) -> str:
    return html.escape(text, quote=True)


def fmt_date(value: str | None) -> str:
    """'2026-08' -> 'Aug 2026', '2014' -> '2014', None -> 'Present'."""
    if value is None:
        return "Present"
    year, _, month = value.partition("-")
    return f"{MONTHS[int(month) - 1]} {year}" if month else year


def fmt_range(start: str, end: str | None) -> str:
    return f"{fmt_date(start)} – {fmt_date(end)}"


def tag_list(items: list[str], cls: str = "tags") -> str:
    return f'<ul class="{cls}">' + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>"


def bullet_list(items: list[str], cls: str) -> str:
    return f'<ul class="{cls}">' + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>"


def in_pdf(item: Json) -> bool:
    return bool(item.get("pdf", True))


def org_line(job: Json) -> str:
    via = f' <span class="via">· via {e(job["via"])}</span>' if job.get("via") else ""
    return f'{e(job["org"])}{via}'


def load_template(name: str) -> Template:
    return Template((ROOT / "templates" / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- website sections

def render_about(cv: Json) -> str:
    about: Json = cv["about"]
    paragraphs = "".join(f"<p>{e(p)}</p>" for p in about["paragraphs"])
    facts = "".join(
        f'<div class="fact"><dt>{e(f["label"])}</dt><dd>{e(f["value"])}</dd></div>' for f in about["facts"]
    )
    capabilities = "".join(
        f'<article class="card capability"><h3>{e(c["title"])}</h3><p>{e(c["text"])}</p>'
        + (f'<p class="capability-tools">{" · ".join(e(t) for t in c["tools"])}</p>' if c.get("tools") else "")
        + "</article>"
        for c in cv["capabilities"]
    )
    interests: Json = cv["interests"]
    cards = "".join(
        f'<article class="card photo-card"><img src="{e(i["image"])}" alt="{e(i["alt"])}" loading="lazy">'
        + (f'<div><h3>{e(i["title"])}</h3><p>{e(i.get("text", ""))}</p></div>' if i.get("title") else "")
        + "</article>"
        for i in interests["items"]
    )
    portrait: Json = about["portrait"]
    return f"""
      <div class="intro">
        <div class="intro-text"><p class="lead">{e(about["lead"])}</p>{paragraphs}</div>
        <figure class="intro-photo"><img src="{e(portrait["src"])}" alt="{e(portrait["alt"])}"></figure>
      </div>
      <dl class="facts">{facts}</dl>
      <h2>Core skills</h2>
      <div class="capabilities">{capabilities}</div>
      <h2>Outside work</h2>
      <p class="interests-text">{e(interests["text"])}</p>
      <div class="photo-grid">{cards}</div>"""


def render_experience(cv: Json) -> str:
    jobs: list[str] = []
    for job in cv["experience"]:
        highlights = bullet_list(job["highlights"], "highlights") if job.get("highlights") else ""
        jobs.append(f"""
        <li class="job">
          <div class="job-when"><span class="dates">{fmt_range(job["start"], job["end"])}</span><span class="place">{e(job["location"])}</span></div>
          <article class="card job-card">
            <h3>{e(job["role"])}</h3>
            <p class="job-org">{org_line(job)}</p>
            <p>{e(job["summary"])}</p>
            {highlights}
            {tag_list(job["tech"], "tags small")}
          </article>
        </li>""")
    earlier: Json = cv["earlierExperience"]
    earlier_items = "".join(
        f'<li><div class="earlier-head"><h3>{e(i["role"])} <span class="org">· {e(i["org"])}</span></h3>'
        f'<span class="dates">{fmt_range(i["start"], i["end"])}</span></div><p>{e(i["text"])}</p></li>'
        for i in earlier["items"]
    )
    intro = f'<p>{e(earlier["intro"])}</p>' if earlier.get("intro") else ""
    return f"""
      <ol class="timeline">{"".join(jobs)}</ol>
      <h2>Earlier experience</h2>
      {intro}
      <ul class="card earlier">{earlier_items}</ul>"""


def render_education(cv: Json) -> str:
    schools = "".join(
        f"""
        <article class="card edu-card">
          <div class="edu-head"><h3>{e(s["degree"])}</h3><span class="dates">{fmt_range(s["start"], s["end"])}</span></div>
          <p class="job-org">{e(s["school"])}</p>
          <p>{e(s["text"])}</p>
          {f'<p class="note">{e(s["note"])}</p>' if s.get("note") else ""}
        </article>"""
        for s in cv["education"]
    )
    certs = "".join(
        f'<li><span class="cert-name">{e(c["name"])}</span><span class="cert-meta">{e(c["issuer"])} · {e(c["year"])}</span>'
        + (f'<a class="cert-link" href="{e(c["url"])}" rel="noopener">View credential</a>' if c.get("url") else "")
        + "</li>"
        for c in cv["certifications"]
    )
    return f"""
      <div class="edu-list">{schools}</div>
      <h2>Certifications</h2>
      <ul class="certs">{certs}</ul>"""


def render_publications(cv: Json) -> str:
    pubs: Json = cv["publications"]
    items = "".join(
        f"""
        <li class="card pub">
          <h3>{e(p["title"])}</h3>
          <p class="pub-meta">{e(p["authors"])} ({e(p["year"])}). <i>{e(p["journal"])}</i> {e(p["volume"])}, {e(p["pages"])}.</p>
          <a href="https://doi.org/{e(p["doi"])}" rel="noopener">doi:{e(p["doi"])}</a>
        </li>"""
        for p in pubs["items"]
    )
    return f"""
      <p class="lead small">{e(pubs["intro"])}</p>
      <ul class="pubs">{items}</ul>"""


def render_site(cv: Json) -> str:
    site: Json = cv["site"]
    basics: Json = cv["basics"]
    return load_template(f'{site["layout"]}.html').substitute(
        title=e(site["title"]),
        description=e(site["description"]),
        layout=e(site["layout"]),
        accent=e(site["accent"]),
        name=e(basics["name"]),
        role=e(basics["title"]),
        location=e(basics["location"]),
        linkedin_url=e(basics["linkedin"]["url"]),
        linkedin_label=e(basics["linkedin"]["label"]),
        github_url=e(basics["github"]["url"]),
        github_label=e(basics["github"]["label"]),
        avatar_src=e(basics["avatar"]["src"]),
        avatar_alt=e(basics["avatar"]["alt"]),
        banner_src=e(basics["banner"]["src"]),
        banner_alt=e(basics["banner"]["alt"]),
        pdf_file=e(site["pdfFile"]),
        about=render_about(cv),
        experience=render_experience(cv),
        education=render_education(cv),
        publications=render_publications(cv),
        year=str(date.today().year),
    )


# ---------------------------------------------------------------- printable CV

def icon(name: str) -> str:
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


def render_print(cv: Json, contact: list[Json]) -> str:
    site: Json = cv["site"]
    basics: Json = cv["basics"]
    location = f'<span>{icon("pin")}{e(basics["location"])}</span>'
    # Public version: the location is a line under the role. Private version: it is the first row of
    # a contact list (location, email, phone) next to the online links instead.
    location_line = "" if contact else f'<p class="where">{location}</p>'
    contact_items = [f"<li>{location}</li>"] if contact else []
    for c in contact:
        key = c.get("label", "").lower()
        contact_items.append(
            "<li><span>"
            + (icon(CONTACT_ICONS[key]) if key in CONTACT_ICONS else "")
            + (f'<a href="{e(c["href"])}">{e(c["value"])}</a>' if c.get("href") else e(c["value"]))
            + "</span></li>"
        )
    contact_list = f'<ul class="contact">{"".join(contact_items)}</ul>' if contact_items else ""
    # Right of the header: the online links, web version first.
    links = [
        ("globe", basics["website"], "Website: "),
        ("linkedin", basics["linkedin"], ""),
        ("github", basics["github"], ""),
    ]
    link_items = [
        f'<li><a href="{e(link["url"])}">{icon(name)}{e(prefix)}{e(link["label"])}</a></li>'
        for name, link, prefix in links
    ]

    jobs = "".join(
        f"""
        <div class="item">
          <div class="item-head"><h3>{e(j["role"])} <span class="org">· {e(j["org"])}</span></h3><span class="when">{e(j["location"])} · {fmt_range(j["start"], j["end"])}</span></div>
          {f'<p class="sub">Consultant via {e(j["via"])}</p>' if j.get("via") else ""}
          <p>{e(j["pdfSummary"])}</p>
          {bullet_list(j["pdfHighlights"], "bullets") if j.get("pdfHighlights") else ""}
          <p class="tech">{" · ".join(e(t) for t in j["tech"])}</p>
        </div>"""
        for j in cv["experience"]
        if in_pdf(j)
    )
    schools = "".join(
        f"""
        <div class="item">
          <h3>{e(s["degree"])}</h3>
          <p class="sub">{e(s["school"])}<br>{fmt_range(s["start"], s["end"])}</p>
          <p>{e(s["text"])}</p>
          {f'<p class="note">{e(s["note"])}</p>' if s.get("note") else ""}
        </div>"""
        for s in cv["education"]
        if in_pdf(s)
    )
    return load_template("print.html").substitute(
        title=e(f'{basics["name"]} – CV'),
        accent_color=ACCENTS.get(site["accent"], ACCENTS["blue"]),
        name=e(basics["name"]),
        role=e(basics["title"]),
        avatar_src=e(basics["avatar"]["src"]),
        avatar_alt=e(basics["avatar"]["alt"]),
        contact_list=contact_list,
        location_line=location_line,
        links="".join(link_items),
        summary=e(cv["pdfSummary"]),
        experience=jobs,
        education=schools,
        languages=" · ".join(e(l) for l in cv["languages"]),
    )


# ---------------------------------------------------------------- PDF

def find_browser() -> str:
    explicit = os.environ.get("CV_BROWSER")
    if explicit:
        return explicit
    for name in BROWSERS:
        found = shutil.which(name)
        if found:
            return found
    for path in WINDOWS_BROWSERS:
        if Path(path).exists():
            return path
    sys.exit("No Chrome, Chromium or Edge found. Set CV_BROWSER to the browser executable.")


def print_pdf(page: Path, pdf: Path) -> None:
    pdf.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        subprocess.run(
            [
                find_browser(),
                "--headless",
                "--disable-gpu",
                "--no-first-run",
                "--no-pdf-header-footer",
                "--print-to-pdf-no-header",
                f"--user-data-dir={profile}",
                f"--print-to-pdf={pdf}",
                page.as_uri(),
            ],
            check=True,
            timeout=120,
            capture_output=True,
        )
    if not pdf.exists():
        sys.exit(f"The browser did not write {pdf}")


# ---------------------------------------------------------------- main

def copy_assets(out: Path) -> None:
    shutil.copytree(ROOT / "assets", out / "assets", dirs_exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=None, help="output folder (default _site, or _private with --private)")
    parser.add_argument("--private", type=Path, default=None, help="JSON file with extra contact details (printable CV only)")
    parser.add_argument("--pdf", action="store_true", help="print the PDF with headless Chrome/Edge")
    args = parser.parse_args()

    cv: Json = json.loads((ROOT / "cv.json").read_text(encoding="utf-8"))
    out: Path = (args.out or ROOT / ("_private" if args.private else "_site")).resolve()
    if out == ROOT:
        sys.exit("--out must be a separate folder")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    copy_assets(out)

    if args.private:
        private: Json = json.loads(args.private.read_text(encoding="utf-8"))
        page = out / "cv-print.html"
        page.write_text(render_print(cv, private.get("contact", [])), encoding="utf-8")
        pdf_name = cv["site"]["pdfFile"]
    else:
        (out / "index.html").write_text(render_site(cv), encoding="utf-8")
        page = out / "cv-print.html"
        page.write_text(render_print(cv, []), encoding="utf-8")
        pdf_name = cv["site"]["pdfFile"]

    if args.pdf:
        print_pdf(page, out / pdf_name)
    print(f"Built {out}" + (f" with {pdf_name}" if args.pdf else ""))


if __name__ == "__main__":
    main()
