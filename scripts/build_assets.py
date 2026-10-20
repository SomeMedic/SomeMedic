"""Build the original SIGNAL LAB artwork. Python standard library only."""

from pathlib import Path
import argparse
import html

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PALETTES = {
    "dark": {"bg": "#081612", "panel": "#0c2019", "grid": "#173a2d", "ink": "#edf8f2", "muted": "#91afa1", "accent": "#42e8a5", "cyan": "#83e5db"},
    "light": {"bg": "#f1faf5", "panel": "#e5f3eb", "grid": "#ccdfd4", "ink": "#102f23", "muted": "#4b7260", "accent": "#087e52", "cyan": "#087f83"},
}


def text(x, y, value, size=18, fill="ink", weight=400, spacing=0, mono=False, extra=""):
    family = "'Cascadia Code',Consolas,monospace" if mono else "Bahnschrift,'Trebuchet MS',sans-serif"
    return f'<text x="{x}" y="{y}" fill="var(--{fill})" font-family="{family}" font-size="{size}" font-weight="{weight}" letter-spacing="{spacing}" {extra}>{html.escape(value)}</text>'


def line(x1, y1, x2, y2, color="grid", extra=""):
    return f'<path d="M{x1} {y1}H{x2}" fill="none" stroke="var(--{color})" {extra}/>' if y1 == y2 else f'<path d="M{x1} {y1}L{x2} {y2}" fill="none" stroke="var(--{color})" {extra}/>'


def svg(width, height, title, desc, body, theme, animated=False):
    palette = PALETTES[theme]
    variables = ";".join(f"--{k}:{v}" for k, v in palette.items())
    animation = """
      .signal-flow{stroke-dasharray:36 720;animation:flow 7s linear infinite}
      .node-pulse{animation:breathe 4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
      .node-pulse:nth-of-type(2n){animation-delay:-2s}
      @keyframes flow{from{stroke-dashoffset:756}to{stroke-dashoffset:0}}
      @keyframes breathe{0%,100%{opacity:.35;transform:scale(.92)}50%{opacity:1;transform:scale(1.08)}}
      @media(prefers-reduced-motion:reduce){.signal-flow,.node-pulse{animation:none}.signal-flow{stroke-dasharray:none;opacity:.65}}
    """ if animated else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{html.escape(title)}</title>
  <desc id="desc">{html.escape(desc)}</desc>
  <style>:root{{{variables}}}text{{font-variant-ligatures:none}}{animation}</style>
  <defs>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="var(--grid)" stroke-width=".65"/></pattern>
    <radialGradient id="aura"><stop stop-color="var(--accent)" stop-opacity=".12"/><stop offset="1" stop-color="var(--accent)" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="{width}" height="{height}" rx="18" fill="var(--bg)"/>
  {body}
</svg>
'''


def network(cx, cy, scale=1):
    nodes = [(-150, 5), (-86, -73), (-84, 82), (-8, -119), (0, -2), (3, 126), (83, -73), (89, 78), (155, 0)]
    pairs = [(0, 1), (0, 2), (0, 4), (1, 3), (1, 4), (2, 4), (2, 5), (3, 6), (4, 6), (4, 7), (5, 7), (6, 8), (7, 8)]
    parts = [f'<g transform="translate({cx} {cy}) scale({scale})">']
    for r in [55, 112, 170]:
        parts.append(f'<circle r="{r}" fill="none" stroke="var(--grid)" stroke-width=".8"/>')
    parts += [line(-205, 0, 205, 0, extra='stroke-dasharray="2 6"'), line(0, -184, 0, 184, extra='stroke-dasharray="2 6"')]
    for a, b in pairs:
        x, y = nodes[a]
        xx, yy = nodes[b]
        parts.append(line(x, y, xx, yy, color="accent", extra='stroke-opacity=".32" stroke-width="1.3"'))
    for n, (x, y) in enumerate(nodes):
        parts.append(f'<circle class="node-pulse" cx="{x}" cy="{y}" r="13" fill="var(--accent)" opacity=".13" style="animation-delay:-{n*.37:.2f}s"/>')
        parts.append(f'<circle cx="{x}" cy="{y}" r="{5 if n == 4 else 3.2}" fill="var(--accent)"/>')
    parts.append('<path d="M-245 5H-171L-158 5L-148 -20L-133 31L-116 -39L-100 5H-84L0 -2L83 -73L155 0H215" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round" opacity=".25"/>')
    parts.append('<path class="signal-flow" d="M-245 5H-171L-158 5L-148 -20L-133 31L-116 -39L-100 5H-84L0 -2L83 -73L155 0H215" fill="none" stroke="var(--accent)" stroke-width="3" stroke-linejoin="round"/>')
    parts.append('</g>')
    return "".join(parts)


def hero(theme, mobile=False):
    w, h = (600, 700) if mobile else (1200, 480)
    b = [f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="url(#grid)" stroke="var(--grid)"/>']
    b.append(f'<ellipse cx="{300 if mobile else 920}" cy="{495 if mobile else 230}" rx="300" ry="255" fill="url(#aura)"/>')
    b += [line(34, 59, 62, 59, "accent", 'stroke-width="2"'), line(48, 45, 48, 73, "accent", 'stroke-width="2"')]
    b.append(text(78, 65, "MAXIM / SOMEMEDIC", 17 if mobile else 18, "ink", 500, 1.5, True))
    if not mobile:
        b.append(text(1158, 64, "PERSONAL ENGINEERING LAB", 12, "muted", 400, 1.1, True, 'text-anchor="end"'))
    b.append(text(38, 123, "FULL-STACK DEVELOPMENT × AI", 13 if mobile else 14, "muted", 400, 1.3, True))
    b.append(text(33, 225 if mobile else 236, "SIGNAL", 99 if mobile else 115, "ink", 700, -3))
    b.append(text(33, 317 if mobile else 344, "LAB", 99 if mobile else 115, "accent", 700, -3))
    if mobile:
        b.append(network(315, 485, .86))
        b.append(line(38, 641, 562, 641))
        b.append(text(38, 673, "FROM SIGNAL TO SOFTWARE.", 15, "muted", 400, .8, True))
    else:
        b.append(network(930, 244, 1.04))
        b.append(text(1100, 425, "INPUT → BUILD → ITERATE", 11, "muted", 400, .7, True, 'text-anchor="end"'))
        b.append(line(38, 390, 566, 390))
        b.append(text(38, 427, "FROM SIGNAL TO SOFTWARE.", 18, "muted", 400, 1, True))
    return svg(w, h, "Maxim / SomeMedic — SIGNAL LAB", "Full-stack development and AI. An emerald signal flows into a network of connected nodes. From signal to software.", "".join(b), theme, True)


PROJECTS = [
    ("digital-expert", "01", "KNOWLEDGE SYSTEMS", "Digital Expert", "PDF → EVIDENCE → ANSWER"),
    ("aivatar", "02", "FULL-STACK AI", "Aivatar", "INTERFACE → STREAM → MODEL"),
    ("everything-ui", "03", "INTERFACE ENGINEERING", "EverythingUI", "COMPONENTS → INTERACTIONS"),
]


def project_card(project, theme, mobile=False):
    slug, num, category, name, caption = project
    w, h = (600, 250) if mobile else (1200, 200)
    b = [f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="var(--panel)" stroke="var(--grid)"/>']
    b.append(text(30, 40, f"EXPERIMENT / {num}", 12, "accent", 500, .8, True))
    b.append(text(30, 85 if mobile else 96, name, 38 if mobile else 43, "ink", 600, -1))
    b.append(text(31, 122 if mobile else 134, category, 12 if mobile else 13, "muted", 400, 1.4, True))
    if mobile:
        b.append(line(30, 146, 570, 146))
        b.append(text(30, 219, caption, 13, "accent", 400, .5, True))
        return svg(w, h, f"{num} / {name}", f"{name} — {category.lower()}.", "".join(b), theme)
    b.append(text(31, 175, caption, 12, "muted", 400, .7, True))
    b.append('<g transform="translate(710 32)">')
    if slug == "digital-expert":
        for x, y in [(0, 18), (9, 11), (18, 4)]:
            b.append(f'<rect x="{x}" y="{y}" width="65" height="90" rx="5" fill="var(--panel)" stroke="var(--accent)" stroke-opacity=".6"/>')
        for y in [28, 40, 52, 64]:
            b.append(line(32, y, 66, y, "accent", 'stroke-opacity=".4" stroke-width="2"'))
        b.append(line(105, 55, 165, 55, "accent", 'stroke-dasharray="3 5"'))
        for x, y in [(187, 20), (187, 54), (187, 88), (224, 37), (224, 72)]:
            b.append(f'<circle cx="{x}" cy="{y}" r="4" fill="var(--accent)"/>')
        for a in [20, 54, 88]:
            for bb in [37, 72]:
                b.append(line(187, a, 224, bb, "accent", 'stroke-opacity=".25"'))
        b.append(line(246, 55, 298, 55, "accent", 'stroke-dasharray="3 5"'))
        b.append('<path d="M325 24L355 54L325 84L295 54Z" fill="var(--accent)" fill-opacity=".08" stroke="var(--accent)"/>')
        b.append('<path d="M313 54L322 63L339 45" fill="none" stroke="var(--accent)" stroke-width="2"/>')
    elif slug == "aivatar":
        b.append('<rect x="0" y="4" width="285" height="116" rx="10" fill="var(--bg)" stroke="var(--grid)"/>')
        for x, y, ww, accent in [(18, 22, 153, False), (82, 50, 184, True), (18, 78, 196, False)]:
            color = "accent" if accent else "grid"
            b.append(f'<rect x="{x}" y="{y}" width="{ww}" height="18" rx="5" fill="var(--{color})" fill-opacity=".2"/>')
            b.append(line(x+10, y+9, x+ww-18, y+9, "accent", 'stroke-opacity=".65" stroke-width="2"'))
        for n in range(11):
            b.append(f'<rect x="{318+n*6}" y="{64-(n%4)*7}" width="2" height="{10+(n%4)*14}" rx="1" fill="var(--accent)" opacity="{.3+(n%4)*.2}"/>')
    else:
        b.append('<rect x="0" y="4" width="350" height="118" rx="9" fill="var(--bg)" stroke="var(--grid)"/>')
        for x in [17, 29, 41]:
            b.append(f'<circle cx="{x}" cy="18" r="2" fill="var(--muted)"/>')
        b.append(line(0, 30, 350, 30))
        b.append('<rect x="17" y="45" width="145" height="59" rx="6" fill="var(--panel)" stroke="var(--grid)"/>')
        b.append('<rect x="180" y="45" width="150" height="24" rx="12" fill="var(--accent)" fill-opacity=".12" stroke="var(--accent)"/>')
        b.append('<rect x="180" y="81" width="72" height="23" rx="5" fill="var(--accent)"/>')
        b.append('<rect x="264" y="81" width="66" height="23" rx="5" fill="none" stroke="var(--grid)"/>')
        for y, ww in [(61, 80), (73, 112), (85, 60)]:
            b.append(line(30, y, 30+ww, y, "accent", 'stroke-opacity=".35" stroke-width="3"'))
    b.append('</g>')
    return svg(w, h, f"{num} / {name}", f"{name} — {category.lower()}. Decorative diagram, not an application screenshot.", "".join(b), theme)


def footer(theme, mobile=False):
    if mobile:
        b = [line(1, 1, 599, 1), text(24, 57, "LET'S BUILD", 32, "ink", 600), text(24, 101, "SOMETHING USEFUL.", 32, "ink", 600)]
        b.append('<path d="M420 45H460L470 28L482 66L498 11L514 45H576" fill="none" stroke="var(--accent)" stroke-width="2"/>')
        return svg(600, 132, "Let's build something useful.", "Get in touch using the links below.", "".join(b), theme)
    b = [line(0, 1, 1200, 1), text(1, 62, "LET'S BUILD SOMETHING USEFUL.", 27, "ink", 600, .3), text(1, 96, "A GOOD CONVERSATION IS A GOOD FIRST COMMIT.", 12, "muted", 400, .9, True)]
    b.append('<path d="M920 58H985L998 40L1010 78L1026 23L1042 58H1200" fill="none" stroke="var(--accent)" stroke-width="2"/>')
    return svg(1200, 125, "Let's build something useful.", "A good conversation is a good first commit.", "".join(b), theme)


def build():
    files = {}
    for theme in PALETTES:
        for mobile in [False, True]:
            suffix = f"{'mobile-' if mobile else ''}{theme}"
            files[f"hero-{suffix}.svg"] = hero(theme, mobile)
            for project in PROJECTS:
                files[f"project-{project[0]}-{suffix}.svg"] = project_card(project, theme, mobile)
            files[f"footer-{suffix}.svg"] = footer(theme, mobile)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check generated files without changing them")
    args = parser.parse_args()
    files = build()
    if args.check:
        bad = [name for name, data in files.items() if not (ASSETS / name).exists() or (ASSETS / name).read_text(encoding="utf-8") != data]
        if bad:
            raise SystemExit("Artwork differs: " + ", ".join(bad))
        print(f"All {len(files)} artwork files match their source.")
    else:
        ASSETS.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (ASSETS / name).write_text(data, encoding="utf-8", newline="\n")
        print(f"Built {len(files)} original SVG assets.")


if __name__ == "__main__":
    main()
