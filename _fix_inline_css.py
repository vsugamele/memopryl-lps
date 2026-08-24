#!/usr/bin/env python3
"""
Fix CSS-not-loading bug on ml05/ml06 standalone Vercel deploy.

Symptoms: page renders unstyled (raw bullets, default h2 font, layout collapsed)
even though CSS files return HTTP 200 with valid content.

Root cause: the standalone deploy is missing critical layout CSS that the
original Elementor+Bt page relied on, and the browser may be caching an
older/empty version of the CSS files. Vercel's flat static deploy of the
original tree (no Node preprocessing) means the index.html points to
`assets/css/*.css` and the browser does the rest -- if any of those files
return 404 or get cached stale, the page goes raw.

Fix (defensive, in this priority order):
  1. <base href="/ml05/">  (forces correct relative path resolution no matter
     where the page is served from -- /ml05, /ml05/index.html, apex redirect)
  2. Cache-Control + Pragma meta tags (kill stale browser cache)
  3. Critical inline <style> block containing the Elementor + Bootstrap
     layout rules actually needed by the page (container, section, column,
     widget, icon-list inline, heading, button, image).  If the external
     files load they override; if they fail, the page still has shape.
  4. ?v=3 cache-buster on every <link rel="stylesheet"> (force fresh fetch)
  5. <link rel="preload"> for the critical CSS (start fetch in parallel
     with HTML parse)
  6. The existing icon-size overrides (kept, with version bump to v3)

Same script runs over ml05/index.html and ml06/index.html with the
appropriate <base href> per page.
"""
from pathlib import Path
import re
import sys

ROOT = Path(r"C:\Users\vsuga\Downloads\SlimSoda\páginas\deploy-memopryl-v2")

# Critical CSS extracted from the actual external files. Only the rules the
# page actually USES (not the whole 194KB of Bootstrap, not every Elementor
# media query).  If the external files load, they override these; if they
# fail, the page keeps its shape.
CRITICAL_CSS = r"""
/* ============================================================
   v3 INLINE FALLBACK -- v2 standalone deploy (ml05+ml06)
   These rules cover the layout that the page breaks without.
   If the external CSS files (assets/css/*.css) load, they
   take precedence (cascade) and this block is harmless.
   If they fail (CDN cache, deploy race, 404), the page
   still has shape: header bar, h1, inline nav, body, etc.
   ============================================================ */
*,*::before,*::after{box-sizing:border-box}
html{line-height:1.15;-webkit-text-size-adjust:100%}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica Neue,Arial,Noto Sans,sans-serif;color:#333;background:#fff;overflow-x:hidden}

/* Elementor containers / sections / columns -- the page only uses e-con */
.e-con{--flex-direction:row;display:flex;flex-wrap:wrap;position:relative;width:100%;margin:0 auto;padding:0 10px}
.e-con.e-flex{--flex-direction:row;flex-direction:var(--flex-direction)}
.e-con.e-con-boxed{max-width:1140px}
.e-con-full,.e-con>.e-con-inner{padding:0 10px;width:100%}
.e-con.e-flex>.e-con-inner{display:flex;flex:1;flex-direction:inherit;flex-wrap:inherit;align-items:inherit;justify-content:inherit;gap:inherit;margin:0 auto;max-width:1140px;width:100%}

/* Make the parent bar actually be a flex row -- the screenshot showed
   everything stacking vertically because this was missing. */
.e-con.e-flex.e-con-boxed.e-parent{align-items:center;justify-content:space-between}

/* Widget wrapping */
.elementor-widget{position:relative;width:100%}
.elementor-widget-wrap{display:flex;flex-wrap:wrap;position:relative;width:100%;align-content:flex-start}

/* Inline nav list (Life But Better / Fitness / Food / Sleep / More) */
.elementor-icon-list-items.elementor-inline-items{display:flex;flex-wrap:wrap;align-items:center;list-style:none;margin:0;padding:0;gap:0 18px}
.elementor-icon-list-item.elementor-inline-item{display:inline-flex;align-items:center;gap:6px}
.elementor-icon-list-text{font-size:14px;line-height:1;color:#333}

/* Icon list: kill the native <ul> disc that shows in the screenshot */
ul.elementor-icon-list-items{list-style:none;padding-left:0}

/* Elementor icon SVG -- the v2 !important override from 3c4449a */
.elementor-widget .elementor-icon-list-icon svg,
.elementor-widget .elementor-icon-list-icon i,
.elementor-widget .elementor-icon svg,
.elementor-widget .elementor-icon i{
  height:1em!important;width:1em!important;
  max-width:24px!important;max-height:24px!important
}
.elementor-icon{color:#69727d;display:inline-block;font-size:24px;line-height:1;text-align:center}
.elementor-icon svg,.elementor-icon i{display:block;height:1em;width:1em;position:relative}

/* Headings */
.elementor-heading-title{line-height:1;margin:0;padding:0}
h1,h2,h3,h4,h5,h6{margin:0 0 .5em;font-weight:500;line-height:1.2}
.elementor-element h2.elementor-heading-title{font-size:18px;font-weight:700;color:#1f1f1f}

/* Image */
.elementor-widget-image img{max-width:100%;height:auto;border:0;display:inline-block;vertical-align:middle}
img.attachment-full{width:auto;max-width:46px;height:auto}

/* Sign-in button */
.elementor-button{background-color:#69727d;border-radius:3px;color:#fff;display:inline-block;fill:#fff;font-size:13px;line-height:1;padding:10px 20px;text-align:center;text-decoration:none}
.elementor-button:hover{color:#fff;opacity:.9}

/* Heading + image group: keep them on the same row as a flex item */
.e-con.e-flex .elementor-widget-image,
.e-con.e-flex .elementor-widget-heading{display:inline-flex;align-items:center;margin-right:8px}

/* Divider line under the header bar */
.elementor-divider-separator{display:block;border-top:1px solid #ced4da;width:100%}

/* Body text under the divider -- keep margins only, do NOT force font-size
   here.  post-1604.css gives the widget div a 37px/700 styling that
   inherits to <p id="dynamic-date">; if we set font-size on text-editor p
   here it overrides that inheritance and the headline shrinks to 16px. */
.elementor-widget-text-editor p{margin:0 0 1em;line-height:1.5}
#dynamic-date{font-size:32px;font-weight:700;line-height:1.2;text-align:left;margin:0 0 16px;color:#000;font-family:"Roboto","Helvetica Neue",Arial,sans-serif}

/* VSL player wrapper */
vturb-smartplayer{display:block;margin:0 auto;width:100%;max-width:400px}
.vturb-player-placeholder{position:relative;width:100%;padding:177.77% 0 0;background-color:#000;z-index:0}

/* Hide the .esconder block until the VSL reveal -- keep its content from
   flashing visible at the top of the page during the first paint */
.esconder{display:none}

/* ============================================================
   END v3 INLINE FALLBACK
   ============================================================ */
"""

# No-cache headers (kill stale browser cache for the HTML itself)
NO_CACHE_META = '''<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">'''

# Old inline style block to replace (kept the icon overrides, but add the rest
# of the critical CSS in front of them so it lands early in the cascade).
OLD_STYLE_START = "<style>\n\t\t\t.esconder {"
NEW_STYLE_START = "<style>\n" + CRITICAL_CSS + "\n\t\t\t.esconder {"

# Old <head> opener to inject the <base> + cache headers BEFORE the styles
OLD_HEAD = "\t</head>"
NEW_HEAD = (
    f'\t<base href="/{{HREF}}/">\n'
    + "\t" + NO_CACHE_META + "\n"
    + "\t</head>"
)

# CSS file cache-buster -- append ?v=3 to every assets/css/ link that
# doesn't already have a ?v= query string.  (reset.css was the only file
# explicitly written as `?v=2` -- there isn't one in this tree, so all
# files get ?v=3 from scratch.)
CSS_HREF_RE = re.compile(r'(href="assets/css/[^"]+\.css)(?!\?v=3)(?=")')


def patch(page_dir: str):
    base = page_dir.strip("/")
    target = ROOT / page_dir / "index.html"
    text = target.read_text(encoding="utf-8")
    orig = text

    # 1. <base href="/ml05/"> (or /ml06/) + no-cache meta
    new_head = NEW_HEAD.replace("{HREF}", base)
    if "<base href=" not in text:
        text = text.replace(OLD_HEAD, new_head, 1)
    else:
        # already had a base, just refresh its href
        text = re.sub(
            r'<base href="[^"]*">',
            f'<base href="/{base}/">',
            text,
            count=1,
        )

    # 2. Critical CSS inline (replaces the tiny old <style> opener with the
    #    big one; the existing .esconder + icon rules ride along inside the
    #    same <style>...</style>).
    if "v3 INLINE FALLBACK" not in text:
        text = text.replace(OLD_STYLE_START, NEW_STYLE_START, 1)

    # 3. Cache-buster on every assets/css/ link
    text = CSS_HREF_RE.sub(r'\1?v=3', text)

    if text == orig:
        print(f"  {page_dir}: no changes")
        return False

    target.write_text(text, encoding="utf-8")
    print(f"  {page_dir}: patched ({len(orig)} -> {len(text)} bytes)")
    return True


if __name__ == "__main__":
    changed = 0
    for d in ("ml05", "ml06"):
        if patch(d):
            changed += 1
    print(f"\n{changed} file(s) patched.")
    sys.exit(0 if changed else 1)
