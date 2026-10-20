# SIGNAL LAB maintenance

The profile is a Markdown document with original, repository-hosted SVG artwork. It does not depend on a live badge or image service. The project descriptions link to public source repositories; the card illustrations are abstract diagrams, not product screenshots.

## Edit the profile

- Change copy, project links, toolkit, or contacts in `README.md`.
- Change artwork and its emerald palettes in `scripts/build_assets.py`, then run `python scripts/build_assets.py`.
- The `<picture>` elements select mobile layouts below 600 CSS pixels and light/dark palettes from the viewer's system color preference. GitHub's theme-specific image behavior may follow the system preference when a manually selected site theme differs.
- The header uses SVG CSS animation. `prefers-reduced-motion: reduce` shows a static composition. All headline text is visible even when animation is unavailable.

## Contribution calendar

`scripts/update_calendar.py` downloads the anonymous HTML calendar at `https://github.com/users/SomeMedic/contributions`. It reads actual daily counts from GitHub's tooltips, validates the full date range, and reconciles every day's count against the public total before writing any output. No PAT, private repository query, or Python package installation is needed. GitHub may include anonymized private contributions if the profile owner chooses to display them publicly.

Four calendar SVGs and `assets/calendar-data.json` are committed snapshots. Each day appears once in every view. Height uses a logarithmic scale so isolated busy days do not hide the rest; colors use GitHub's activity levels. The mobile view splits the same dates into two consecutive terraces. Each image includes its actual range and refresh time in UTC.

The **Refresh contribution landscape** workflow runs daily at 05:23 UTC, on manual dispatch, and on changes to the calendar script, its tests, or the workflow. Scheduled workflows run from the default branch. GitHub can delay scheduled runs or disable schedules in inactive public repositories; use the workflow's **Run workflow** control to refresh manually. The workflow needs **Actions enabled** and a `GITHUB_TOKEN` with `contents: write` permission, and commits only the five calendar outputs. Branch protection may require adapting the publication step.

If GitHub changes its HTML or a request fails, the job fails visibly and preserves the last good images. Check the workflow log before changing the parser; do not substitute invented activity.

```sh
python scripts/update_calendar.py --username SomeMedic
python scripts/build_assets.py --check
python -m unittest discover -s scripts -p 'test_calendar.py' -v
```

For offline parser reproduction, save a successful contribution HTML response and pass `--html path/to/contributions.html --output-dir path/to/scratch-assets`. The response must still be within the parser's freshness window.

## Visual review

After a layout change, inspect the rendered GitHub README at desktop and phone widths in both color schemes. Check that every image loads, project cards remain readable, navigation anchors work, and reduced motion disables the animated path and nodes. Keep all SVGs self-contained: no scripts, embedded HTML, or external font/image requests.
