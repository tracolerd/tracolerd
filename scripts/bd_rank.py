#!/usr/bin/env python3
"""Generate assets/bd-rank.svg: Bangladesh GitHub rank card (followers + activity).

Data source: gayanvoice/top-github-users (cache/bangladesh.json), which lists the
most-followed GitHub users in Bangladesh together with their public contribution
counts for the last year. Ranks are computed against that list.

  Followers rank : your live follower count (GitHub API) vs. followers of the list
  Activity rank  : your public contributions (from the list) vs. the rest of the list

Stdlib only. Optional env vars:
  GITHUB_TOKEN    raises the API rate limit (provided automatically in Actions)
  RANK_USER       GitHub username (default: tracolerd)
  RANK_OUT        output path (default: assets/bd-rank.svg)
  RANK_FOLLOWERS  override live follower count (testing only)
"""
import datetime
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("RANK_USER", "tracolerd")
OUT = os.environ.get("RANK_OUT", "assets/bd-rank.svg")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
CACHE_URL = (
    "https://raw.githubusercontent.com/gayanvoice/top-github-users/main/cache/bangladesh.json"
)


def get_json(url, auth=False):
    headers = {"User-Agent": "bd-rank-card", "Accept": "application/json"}
    if auth and TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def live_followers(fallback):
    override = os.environ.get("RANK_FOLLOWERS")
    if override:
        return int(override)
    try:
        return int(get_json("https://api.github.com/users/" + USER, auth=True)["followers"])
    except Exception as exc:  # network or rate limit: fall back to the list value
        print("live follower lookup failed:", exc, file=sys.stderr)
        return fallback


def compute():
    users = get_json(CACHE_URL)
    me = next((u for u in users if u["login"].lower() == USER.lower()), None)
    others = [u for u in users if u["login"].lower() != USER.lower()]
    followers = live_followers(me["followers"] if me else 0)
    total = len(others) + 1
    f_rank = 1 + sum(1 for u in others if u["followers"] > followers)
    if me is not None:
        contrib = me["publicContributions"]
        a_rank = 1 + sum(1 for u in others if u["publicContributions"] > contrib)
    else:
        contrib, a_rank = None, None
    min_followers = min(u["followers"] for u in users)
    return {
        "followers": followers,
        "f_rank": f_rank,
        "contrib": contrib,
        "a_rank": a_rank,
        "total": total,
        "min_followers": min_followers,
    }


def panel(x, label, rank, total, sub):
    rank_txt = "#%d" % rank if rank else "N/A"
    of_txt = " of %d" % total if rank else " (not in list)"
    return f"""
  <g class="in" style="animation-delay:{0.15 if x < 400 else 0.45}s">
    <text x="{x}" y="34" class="lab">{escape(label)}</text>
    <line class="bar" x1="{x}" y1="44" x2="{x + 70}" y2="44" stroke="#58a6ff" stroke-width="2"/>
    <text x="{x}" y="88"><tspan class="num">{rank_txt}</tspan><tspan class="of" dx="10">{of_txt}</tspan></text>
    <text x="{x}" y="108" class="sub">{escape(sub)}</text>
  </g>"""


def render(d):
    updated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    contrib_txt = "%d public contributions in the last year" % d["contrib"] if d["contrib"] is not None else "No public contribution data"
    p1 = panel(40, "BANGLADESH RANK  |  FOLLOWERS", d["f_rank"], d["total"], "%d followers" % d["followers"])
    p2 = panel(440, "BANGLADESH RANK  |  ACTIVITY", d["a_rank"], d["total"], contrib_txt)
    foot = "Ranked among Bangladeshi GitHub users with %d+ followers (source: top-github-users)  |  Updated %s UTC" % (
        d["min_followers"], updated)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="820" height="150" viewBox="0 0 820 150" role="img" aria-label="Bangladesh GitHub rank: followers #{d['f_rank']}, activity #{d['a_rank']}">
  <style>
    text {{ font-family: 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif; }}
    .lab {{ font-size: 12px; letter-spacing: 1.6px; fill: #8b949e; }}
    .num {{ font-size: 42px; font-weight: 700; fill: #58a6ff; }}
    .of {{ font-size: 15px; fill: #8b949e; }}
    .sub {{ font-size: 13px; fill: #c9d1d9; }}
    .foot {{ font-size: 10.5px; fill: #6e7681; }}
    .in {{ animation: rise .9s ease-out both; }}
    .bar {{ animation: draw 1.2s ease-out .3s both; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    @keyframes draw {{ from {{ stroke-dasharray: 70; stroke-dashoffset: 70; }} to {{ stroke-dasharray: 70; stroke-dashoffset: 0; }} }}
  </style>
  <rect x="0.5" y="0.5" width="819" height="149" rx="10" fill="#0d1117" stroke="#30363d"/>
  <line x1="410" y1="20" x2="410" y2="116" stroke="#21262d" stroke-width="1"/>{p1}{p2}
  <line x1="40" y1="124" x2="780" y2="124" stroke="#21262d" stroke-width="1"/>
  <text x="410" y="141" text-anchor="middle" class="foot">{escape(foot)}</text>
</svg>
"""


def main():
    try:
        data = compute()
    except Exception as exc:
        print("rank update skipped:", exc, file=sys.stderr)
        return 0  # keep the previous card instead of failing the workflow
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(render(data))
    print(json.dumps(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
