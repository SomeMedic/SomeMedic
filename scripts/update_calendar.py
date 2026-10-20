#!/usr/bin/env python3
"""Render an isometric calendar from GitHub's anonymous public profile graph.

Python standard library only. A failed request or changed HTML schema leaves the
last successful assets untouched. No token, private repository query or external
image host is used. GitHub's public aggregate may include anonymized private
contributions when the profile owner has chosen to display them.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.request import Request, urlopen


MAX_RESPONSE_BYTES = 2_000_000
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
FILENAMES = ("calendar-dark.svg", "calendar-light.svg", "calendar-mobile-dark.svg", "calendar-mobile-light.svg", "calendar-data.json")


class CalendarError(ValueError):
    """The source cannot be trusted as a complete contribution calendar."""


@dataclass(frozen=True)
class Day:
    day: date
    count: int
    level: int


@dataclass(frozen=True)
class Calendar:
    username: str
    days: tuple[Day, ...]
    total: int


class ContributionParser(HTMLParser):
    def __init__(self, username: str):
        super().__init__(convert_charrefs=True)
        self.username = username
        self.range_start: str | None = None
        self.range_end: str | None = None
        self.cells: list[dict[str, str]] = []
        self.tooltips: dict[str, str] = {}
        self.heading = ""
        self._tooltip_id: str | None = None
        self._tooltip_text: list[str] = []
        self._in_heading = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("data-graph-url") == f"/users/{self.username}/contributions":
            self.range_start = attrs.get("data-from", "")[:10]
            self.range_end = attrs.get("data-to", "")[:10]
        if "ContributionCalendar-day" in attrs.get("class", "").split() and "data-date" in attrs:
            self.cells.append(attrs)
        if tag == "tool-tip" and attrs.get("for"):
            self._tooltip_id = attrs["for"]
            self._tooltip_text = []
        if tag == "h2" and attrs.get("id") == "js-contribution-activity-description":
            self._in_heading = True

    def handle_data(self, text):
        if self._tooltip_id is not None:
            self._tooltip_text.append(text)
        if self._in_heading:
            self.heading += text

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self._tooltip_id is not None:
            if self._tooltip_id in self.tooltips:
                raise CalendarError("Duplicate contribution tooltip")
            self.tooltips[self._tooltip_id] = "".join(self._tooltip_text).strip()
            self._tooltip_id = None
        if tag == "h2":
            self._in_heading = False


def parse_calendar(html: str, username: str, *, today: date | None = None) -> Calendar:
    """Require complete dates, matching tooltip counts and a reconciled total."""
    today = today or datetime.now(timezone.utc).date()
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", username):
        raise CalendarError("Invalid GitHub username")
    parser = ContributionParser(username)
    try:
        parser.feed(html)
        start = date.fromisoformat(parser.range_start or "")
        end = date.fromisoformat(parser.range_end or "")
    except (ValueError, TypeError) as exc:
        raise CalendarError("Missing or invalid calendar date range") from exc
    expected_days = (end - start).days + 1
    if not 350 <= expected_days <= 378 or len(parser.cells) != expected_days:
        raise CalendarError("Calendar is not a complete rolling year")
    if not today - timedelta(days=2) <= end <= today + timedelta(days=1):
        raise CalendarError("Calendar response is stale or future-dated")
    days: dict[date, Day] = {}
    for cell in parser.cells:
        try:
            cell_date = date.fromisoformat(cell["data-date"])
            level = int(cell["data-level"])
            tooltip = parser.tooltips[cell["id"]]
        except (KeyError, ValueError) as exc:
            raise CalendarError("Missing day date, level or tooltip") from exc
        match = re.fullmatch(r"(No|[\d,]+) contributions? on ([A-Za-z]+) (\d{1,2})(?:st|nd|rd|th)?(?:,? (\d{4}))?\.", tooltip)
        if not match:
            raise CalendarError(f"Unrecognized contribution tooltip: {tooltip!r}")
        try:
            count = 0 if match[1] == "No" else int(match[1].replace(",", ""))
        except ValueError as exc:
            raise CalendarError("Invalid contribution count") from exc
        if (match[2] != MONTHS[cell_date.month - 1] or int(match[3]) != cell_date.day
                or (match[4] and int(match[4]) != cell_date.year)):
            raise CalendarError("Tooltip date does not match its calendar cell")
        if not 0 <= level <= 4 or count < 0 or (count == 0) != (level == 0):
            raise CalendarError("Contribution count and level are inconsistent")
        if not start <= cell_date <= end or cell_date in days:
            raise CalendarError("Duplicate or out-of-range contribution date")
        days[cell_date] = Day(cell_date, count, level)
    if set(days) != {start + timedelta(days=i) for i in range(expected_days)}:
        raise CalendarError("Contribution dates contain a gap")
    heading = re.search(r"([\d,]+)\s+contributions?\b", parser.heading)
    if not heading:
        raise CalendarError("Missing public contribution total")
    total = int(heading[1].replace(",", ""))
    if sum(day.count for day in days.values()) != total:
        raise CalendarError("Daily counts do not reconcile with GitHub's total")
    return Calendar(username, tuple(days[d] for d in sorted(days)), total)


def fetch_calendar(username: str) -> str:
    request = Request(f"https://github.com/users/{username}/contributions", headers={
        "User-Agent": "SomeMedic-Signal-Lab/1.0 (+https://github.com/SomeMedic/SomeMedic)",
        "Accept": "text/html", "Accept-Language": "en-US,en;q=0.9",
    })
    with urlopen(request, timeout=30) as response:
        if response.status != 200 or response.headers.get_content_type() != "text/html":
            raise CalendarError("GitHub did not return contribution HTML")
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise CalendarError("GitHub response exceeds the size limit")
    return payload.decode("utf-8", errors="strict")


PALETTES = {
    "dark": {"bg": "#081612", "border": "#173a2d", "text": "#e7f6ef", "muted": "#8caaa0", "accent": "#34d399", "floor": "#0d241b", "levels": ("#163a2b", "#145a3b", "#0d8d59", "#10b981", "#55e6b0")},
    "light": {"bg": "#f1faf5", "border": "#c5e3d2", "text": "#123e2b", "muted": "#557b66", "accent": "#087d50", "floor": "#e3f3e9", "levels": ("#cee5d7", "#9bd8b1", "#58bf8b", "#16a269", "#087d50")},
}


def shade(color: str, factor: float) -> str:
    return "#" + "".join(f"{min(255, round(int(color[i:i+2], 16) * factor)):02x}" for i in (1, 3, 5))


def points(coords) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)


def render_svg(calendar: Calendar, theme: str, generated_at: datetime, *, mobile: bool = False) -> str:
    p = PALETTES[theme]
    width, height = (680, 730) if mobile else (1100, 440)
    first = calendar.days[0].day
    last = calendar.days[-1].day
    sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    n_weeks = (last - sunday).days // 7 + 1
    peak = max(day.count for day in calendar.days)
    active_days = sum(day.count > 0 for day in calendar.days)
    stamp = generated_at.astimezone(timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    range_text = f"{first:%d %b %Y} — {last:%d %b %Y}"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="calendar-title calendar-desc">',
        f'<title id="calendar-title">{escape(calendar.username)} — contribution landscape</title>',
        f'<desc id="calendar-desc">{calendar.total:,} contributions on {active_days} active days, {range_text}. Each column is one day. Height scales logarithmically with its real contribution count; colors follow GitHub levels. Updated {stamp}.</desc>',
        f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="24" fill="{p["bg"]}" stroke="{p["border"]}"/>',
        '<g font-family="Segoe UI,Arial,sans-serif">',
        f'<text x="36" y="35" fill="{p["accent"]}" font-family="Consolas,monospace" font-size="11" letter-spacing="2.5">03 / CONTRIBUTION LANDSCAPE</text>',
        f'<text x="36" y="73" fill="{p["text"]}" font-size="30" font-weight="650">Small steps. Real momentum.</text>',
    ]
    if mobile:
        parts.extend([
            f'<text x="36" y="105" fill="{p["text"]}" font-size="19" font-weight="600">{calendar.total:,} contributions</text>',
            f'<text x="{width-36}" y="105" text-anchor="end" fill="{p["muted"]}" font-size="15">{active_days} active days</text>',
        ])
    else:
        parts.extend([
            f'<text x="36" y="101" fill="{p["muted"]}" font-size="13">{range_text} · {active_days} active days</text>',
            f'<text x="{width-36}" y="48" text-anchor="end" fill="{p["accent"]}" font-size="30" font-weight="650">{calendar.total:,}</text>',
            f'<text x="{width-36}" y="71" text-anchor="end" fill="{p["muted"]}" font-size="12">contributions</text>',
        ])
    # Slightly flattened isometry keeps a full year readable in a README column.
    # On mobile, two consecutive half-year terraces preserve every date.
    split = (n_weeks + 1) // 2
    segments = [(0, split), (split, n_weeks)] if mobile else [(0, n_weeks)]
    for index, (start_week, end_week) in enumerate(segments):
        ox, oy = ((40, 272 + index * 275) if mobile else (76, 292))
        ux, uy, vx, vy = (18, -1.8, 10.5, 7.8) if mobile else (16.6, -1.8, 10, 7)
        weeks = end_week - start_week
        floor = [(ox-6, oy-5), (ox+weeks*ux, oy+weeks*uy-5), (ox+weeks*ux+7*vx+5, oy+weeks*uy+7*vy+7), (ox+7*vx-6, oy+7*vy+7)]
        parts.append(f'<polygon points="{points(floor)}" fill="{p["floor"]}" stroke="{p["border"]}"/>')
        tiles = []
        for day in calendar.days:
            week, weekday = divmod((day.day - sunday).days, 7)
            if not start_week <= week < end_week:
                continue
            week -= start_week
            x, y = ox + week*ux + weekday*vx, oy + week*uy + weekday*vy
            tiles.append((y, x, day))
        for y, x, day in sorted(tiles, key=lambda tile: (tile[0], tile[1])):
            h = 2.5 + (math.log1p(day.count) / math.log1p(peak) * (65 if mobile else 70) if peak else 0)
            u, v = (ux*.79, uy*.79), (vx*.79, vy*.79)
            a, b, c, d = (x, y-h), (x+u[0], y+u[1]-h), (x+u[0]+v[0], y+u[1]+v[1]-h), (x+v[0], y+v[1]-h)
            top = p["levels"][day.level]
            unit = "contribution" if day.count == 1 else "contributions"
            parts.extend([
                f'<g class="day" data-date="{day.day}" data-count="{day.count}" data-level="{day.level}">',
                f'<title>{day.day}: {day.count:,} {unit}</title>',
                f'<polygon points="{points([d,c,(c[0],c[1]+h),(d[0],d[1]+h)])}" fill="{shade(top,.64)}"/>',
                f'<polygon points="{points([b,c,(c[0],c[1]+h),(b[0],b[1]+h)])}" fill="{shade(top,.80)}"/>',
                f'<polygon points="{points([a,b,c,d])}" fill="{top}" stroke="{shade(top,1.08)}" stroke-width=".35"/>',
                '</g>',
            ])
        segment_days = [d for d in calendar.days if start_week <= (d.day-sunday).days//7 < end_week]
        # Month labels follow the near edge; a second October is labeled by year.
        seen_months = set()
        for day in segment_days:
            key = (day.day.year, day.day.month)
            if key in seen_months:
                continue
            seen_months.add(key)
            # A short leading partial month would collide with the next label.
            # The full date range above/below the plot still records these days.
            if day == segment_days[0] and day.day.day > 15:
                continue
            week = (day.day - sunday).days // 7 - start_week
            x, y = ox + week*ux + 7*vx, oy + week*uy + 7*vy + 23
            label = day.day.strftime("%b")
            if day.day.month == 1 or day == segment_days[0]:
                label += day.day.strftime(" ’%y")
            parts.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{p["muted"]}" font-size="{13 if mobile else 11}">{label}</text>')
    footer_y = 654 if mobile else 376
    parts.append(f'<path d="M36 {footer_y}H{width-36}" stroke="{p["border"]}"/>')
    if mobile:
        parts.append(f'<text x="36" y="{footer_y+29}" fill="{p["muted"]}" font-size="14">{range_text}</text>')
        parts.append(f'<text x="36" y="{footer_y+54}" fill="{p["muted"]}" font-size="12">REFRESHED {stamp}</text>')
    else:
        parts.append(f'<text x="36" y="{footer_y+29}" fill="{p["muted"]}" font-size="11" font-family="Consolas,monospace">REFRESHED {stamp}</text>')
    legend_x = width - (224 if mobile else 242)
    legend_y = footer_y + (45 if mobile else 21)
    parts.append(f'<text x="{legend_x}" y="{legend_y+7}" fill="{p["muted"]}" font-size="11">Less</text>')
    for level, color in enumerate(p["levels"]):
        parts.append(f'<rect x="{legend_x+34+level*22}" y="{legend_y-4}" width="16" height="13" rx="3" fill="{color}"/>')
    parts.append(f'<text x="{legend_x+150}" y="{legend_y+7}" fill="{p["muted"]}" font-size="11">More</text>')
    parts.extend(['</g>', '</svg>'])
    return "\n".join(parts) + "\n"


def build_outputs(calendar: Calendar, generated_at: datetime) -> dict[str, str]:
    outputs = {}
    for mobile in (False, True):
        for theme in ("dark", "light"):
            name = f'calendar-{"mobile-" if mobile else ""}{theme}.svg'
            outputs[name] = render_svg(calendar, theme, generated_at, mobile=mobile)
    data = {
        "schema_version": 1,
        "username": calendar.username,
        "source_url": f"https://github.com/users/{calendar.username}/contributions",
        "generated_at": generated_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "from": calendar.days[0].day.isoformat(),
        "to": calendar.days[-1].day.isoformat(),
        "total": calendar.total,
        "days": [{"date": day.day.isoformat(), "count": day.count, "level": day.level} for day in calendar.days],
    }
    outputs["calendar-data.json"] = json.dumps(data, indent=2) + "\n"
    return outputs


def write_outputs(output_dir: Path, outputs: dict[str, str]) -> None:
    """Stage every file, then replace; roll back any replacements on IO failure."""
    output_dir.mkdir(parents=True, exist_ok=True)
    previous = {name: (output_dir/name).read_bytes() if (output_dir/name).exists() else None for name in outputs}
    replaced = []
    with tempfile.TemporaryDirectory(prefix=".calendar-", dir=output_dir) as staging:
        stage = Path(staging)
        for name, text in outputs.items():
            (stage/name).write_text(text, encoding="utf-8", newline="\n")
        try:
            for name in outputs:
                os.replace(stage/name, output_dir/name)
                replaced.append(name)
        except OSError:
            for name in reversed(replaced):
                destination = output_dir/name
                if previous[name] is None:
                    destination.unlink(missing_ok=True)
                else:
                    destination.write_bytes(previous[name])
            raise


def update_calendar(username: str, output_dir: Path, *, html: str | None = None, now: datetime | None = None) -> Calendar:
    now = now or datetime.now(timezone.utc)
    source = fetch_calendar(username) if html is None else html
    calendar = parse_calendar(source, username, today=now.date())
    outputs = build_outputs(calendar, now)
    write_outputs(output_dir, outputs)
    return calendar


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default="SomeMedic")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1]/"assets")
    parser.add_argument("--html", type=Path, help="Use a saved public contribution HTML response (offline reproduction)")
    args = parser.parse_args()
    try:
        source = args.html.read_text(encoding="utf-8") if args.html else None
        calendar = update_calendar(args.username, args.output_dir, html=source)
    except (CalendarError, OSError, UnicodeError) as exc:
        print(f"Calendar not updated; last successful assets preserved: {exc}", file=sys.stderr)
        return 1
    print(f"Rendered {len(calendar.days)} real days / {calendar.total:,} contributions for {calendar.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
