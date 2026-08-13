"""Generates a small contribution-streak SVG from GitHub's own GraphQL API.

Self-hosted replacement for github-readme-streak-stats: that public demo
service was returning stale/wrong numbers for this account. This script
reads the same public contribution calendar GitHub itself shows on the
profile page (which already reflects private contributions if the
"Include private contributions" profile setting is on) and renders a
compact card, so the numbers are always correct.
"""

import json
import os
import sys
import urllib.request
from datetime import date, timedelta

TOKEN = os.environ["GH_TOKEN"]
LOGIN = os.environ.get("GH_LOGIN", "bunihayashi")
OUT_PATH = sys.argv[1] if len(sys.argv) > 1 else "streak.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "streak-script",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def flatten_days(payload):
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = []
    for week in weeks:
        for day in week["contributionDays"]:
            days.append((date.fromisoformat(day["date"]), day["contributionCount"]))
    days.sort(key=lambda item: item[0])
    return days


def compute_streaks(days):
    by_date = {d: c for d, c in days}
    today = date.today()

    cursor = today
    if by_date.get(cursor, 0) == 0:
        cursor -= timedelta(days=1)
    current = 0
    current_start = None
    while by_date.get(cursor, 0) > 0:
        current += 1
        current_start = cursor
        cursor -= timedelta(days=1)

    longest = 0
    longest_start = longest_end = None
    run = 0
    run_start = None
    for d, c in days:
        if c > 0:
            if run == 0:
                run_start = d
            run += 1
            if run > longest:
                longest = run
                longest_start, longest_end = run_start, d
        else:
            run = 0
            run_start = None

    return {
        "current": current,
        "current_start": current_start,
        "longest": longest,
        "longest_start": longest_start,
        "longest_end": longest_end,
    }


def fmt_day(d):
    return f"{d:%b} {d.day}" if d else "-"


def render_svg(total, stats):
    current_sub = f"since {fmt_day(stats['current_start'])}" if stats["current"] else "no active streak"
    longest_sub = (
        f"{fmt_day(stats['longest_start'])} - {fmt_day(stats['longest_end'])}" if stats["longest"] else "-"
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="120" viewBox="0 0 480 120">
  <rect x="0.5" y="0.5" width="479" height="119" rx="10" fill="#1a1b27" stroke="#30363d" />
  <line x1="160" y1="18" x2="160" y2="102" stroke="#30363d" />
  <line x1="320" y1="18" x2="320" y2="102" stroke="#30363d" />

  <text x="80" y="52" text-anchor="middle" font-family="Segoe UI, Helvetica, sans-serif" font-size="26" font-weight="700" fill="#79c0ff">{total}</text>
  <text x="80" y="74" text-anchor="middle" font-family="Segoe UI, Helvetica, sans-serif" font-size="11" fill="#8b949e">Total Contributions</text>
  <text x="80" y="92" text-anchor="middle" font-family="Segoe UI, Helvetica, sans-serif" font-size="10" fill="#56d364">last 365 days</text>

  <text x="240" y="52" text-anchor="middle" font-family="Segoe UI, Helvetica, sans-serif" font-size="26" font-weight="700" fill="#d2a8ff">{stats['current']}</text>
  <text x="240" y="74" text-anchor="middle" font-family="Segoe UI, Helvetica, sans-serif" font-size="11" fill="#8b949e">Current Streak</text>
  <text x="240" y="92" text-anchor="middle" font-family="Segoe UI, Helvetica, sans-serif" font-size="10" fill="#56d364">{current_sub}</text>

  <text x="400" y="52" text-anchor="middle" font-family="Segoe UI, Helvetica, sans-serif" font-size="26" font-weight="700" fill="#79c0ff">{stats['longest']}</text>
  <text x="400" y="74" text-anchor="middle" font-family="Segoe UI, Helvetica, sans-serif" font-size="11" fill="#8b949e">Longest Streak</text>
  <text x="400" y="92" text-anchor="middle" font-family="Segoe UI, Helvetica, sans-serif" font-size="10" fill="#56d364">{longest_sub}</text>
</svg>
'''


def main():
    payload = fetch()
    days = flatten_days(payload)
    total = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    stats = compute_streaks(days)
    svg = render_svg(total, stats)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"total={total} current={stats['current']} longest={stats['longest']}")


if __name__ == "__main__":
    main()
