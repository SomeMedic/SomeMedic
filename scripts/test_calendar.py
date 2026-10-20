"""Behavioral checks for real-data validation and safe calendar publication."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from update_calendar import CalendarError, FILENAMES, build_outputs, parse_calendar, update_calendar, write_outputs


TODAY = date(2026, 10, 20)
NOW = datetime(2026, 10, 20, 15, 30, tzinfo=timezone.utc)
TEST_ROOT = Path(__file__).resolve().parents[1]


def source_html(*, zero=False):
    first = TODAY - timedelta(days=364)
    days = [first + timedelta(days=i) for i in range(365)]
    counts = [0 if zero else i % 5 for i in range(365)]
    parts = [f'<div data-graph-url="/users/SomeMedic/contributions" data-from="{first} 00:00:00 UTC" data-to="{TODAY} 23:59:59 UTC">', f'<h2 id="js-contribution-activity-description">{sum(counts):,} contributions in the last year</h2>']
    for i, (day, count) in enumerate(zip(days, counts)):
        word = "No contributions" if count == 0 else f'{count} contribution' + ("s" if count != 1 else "")
        parts.extend([f'<td class="ContributionCalendar-day" data-date="{day}" data-level="{count}" id="day-{i}"></td>', f'<tool-tip for="day-{i}">{word} on {day:%B} {day.day}th.</tool-tip>'])
    return "\n".join(parts) + "</div>"


class CalendarValidationTests(unittest.TestCase):
    def test_date_order_counts_and_total_are_reconciled(self):
        calendar = parse_calendar(source_html(), "SomeMedic", today=TODAY)
        self.assertEqual(len(calendar.days), 365)
        self.assertEqual(calendar.days[0].day, TODAY - timedelta(days=364))
        self.assertEqual(calendar.days[-1].day, TODAY)
        self.assertEqual(calendar.total, 730)
        self.assertEqual(calendar.days[1].count, 1)

    def test_a_complete_zero_activity_calendar_is_valid(self):
        self.assertEqual(parse_calendar(source_html(zero=True), "SomeMedic", today=TODAY).total, 0)

    def test_empty_and_unexpected_response_are_rejected(self):
        for source in ("", "<html>Rate limit exceeded</html>", "<html>Sign in</html>"):
            with self.subTest(source=source), self.assertRaises(CalendarError):
                parse_calendar(source, "SomeMedic", today=TODAY)

    def test_missing_duplicate_bad_level_and_wrong_tooltip_are_rejected(self):
        source = source_html()
        mutations = [
            source.replace('class="ContributionCalendar-day"', 'class="not-a-day"', 1),
            source.replace('data-date="2025-10-22"', 'data-date="2025-10-21"', 1),
            source.replace('data-level="1"', 'data-level="9"', 1),
            source.replace('No contributions on October 21th.', 'No contributions on November 21th.', 1),
            source.replace('730 contributions in the last year', '731 contributions in the last year', 1),
        ]
        for malformed in mutations:
            with self.subTest(index=mutations.index(malformed)), self.assertRaises(CalendarError):
                parse_calendar(malformed, "SomeMedic", today=TODAY)

    def test_stale_calendar_is_rejected(self):
        with self.assertRaises(CalendarError):
            parse_calendar(source_html(), "SomeMedic", today=TODAY + timedelta(days=3))

    def test_fetch_failure_never_replaces_last_good_outputs(self):
        with tempfile.TemporaryDirectory(prefix=".calendar-test-", dir=TEST_ROOT) as directory:
            output_dir = Path(directory)
            for name in FILENAMES:
                (output_dir/name).write_text("last good asset", encoding="utf-8")
            with patch("update_calendar.fetch_calendar", side_effect=OSError("network unavailable")):
                with self.assertRaises(OSError):
                    update_calendar("SomeMedic", output_dir, now=NOW)
            for name in FILENAMES:
                self.assertEqual((output_dir/name).read_text(), "last good asset")

    def test_malformed_source_never_replaces_last_good_outputs(self):
        with tempfile.TemporaryDirectory(prefix=".calendar-test-", dir=TEST_ROOT) as directory:
            output_dir = Path(directory)
            for name in FILENAMES:
                (output_dir/name).write_text("last good asset", encoding="utf-8")
            with self.assertRaises(CalendarError):
                update_calendar("SomeMedic", output_dir, html="", now=NOW)
            for name in FILENAMES:
                self.assertEqual((output_dir/name).read_text(), "last good asset")

    def test_replacement_failure_rolls_back_already_replaced_assets(self):
        with tempfile.TemporaryDirectory(prefix=".calendar-test-", dir=TEST_ROOT) as directory:
            output_dir = Path(directory)
            for name in ("a.svg", "b.svg"):
                (output_dir/name).write_text("old", encoding="utf-8")
            import os
            replace = os.replace
            calls = 0
            def fail_second(source, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("disk full")
                return replace(source, destination)
            with patch("update_calendar.os.replace", side_effect=fail_second):
                with self.assertRaises(OSError):
                    write_outputs(output_dir, {"a.svg": "new", "b.svg": "new"})
            self.assertEqual((output_dir/"a.svg").read_text(), "old")
            self.assertEqual((output_dir/"b.svg").read_text(), "old")

    def test_all_themes_are_self_contained_and_render_every_day_once(self):
        calendar = parse_calendar(source_html(), "SomeMedic", today=TODAY)
        outputs = build_outputs(calendar, NOW)
        self.assertEqual(set(outputs), set(FILENAMES))
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        for name, source in outputs.items():
            if not name.endswith(".svg"):
                continue
            with self.subTest(name=name):
                root = ET.fromstring(source)
                days = root.findall('.//svg:g[@class="day"]', namespace)
                self.assertEqual(len(days), 365)
                self.assertEqual(len({d.attrib["data-date"] for d in days}), 365)
                self.assertEqual(sum(int(d.attrib["data-count"]) for d in days), 730)
                self.assertEqual(len(root.findall('.//svg:g[@class="day"]/svg:polygon', namespace)), 1095)
                self.assertNotIn("<script", source)
                self.assertNotIn("<image", source)


if __name__ == "__main__":
    unittest.main()
