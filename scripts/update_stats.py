"""Generate repository-hosted profile cards from public, non-fork GitHub repos.

Run with GITHUB_TOKEN (the workflow's built-in token) or unauthenticated locally.
All API reads finish before cards are written, preserving them on API failures.
Language percentages measure repository bytes, not proficiency or activity.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-stats',
               'X-GitHub-Api-Version': '2022-11-28'}
    if os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    with urlopen(Request('https://api.github.com' + path, headers=headers), timeout=30) as response:
        return json.load(response)


def collect(username, fetch=api):
    repos = []
    page = 1
    while True:
        batch = fetch(f'/users/{username}/repos?type=owner&per_page=100&page={page}')
        if not isinstance(batch, list):
            raise ValueError('GitHub did not return a repository list')
        if not batch:
            break
        repos.extend(r for r in batch if not r.get('fork') and not r.get('private'))
        page += 1
    languages = Counter()
    for repo in repos:
        languages.update(fetch(f"/repos/{repo['full_name']}/languages"))
    return {'repos': len(repos),
            'stars': sum(r.get('stargazers_count', 0) for r in repos),
            'forks': sum(r.get('forks_count', 0) for r in repos),
            'languages': dict(languages)}


def text(x, y, value, size=14, color='#c9d1d9'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{escape(str(value))}</text>'


def card(title, description, body, height):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="470" height="{height}" '
            f'viewBox="0 0 470 {height}" role="img" aria-labelledby="title description">'
            f'<title id="title">{escape(title)}</title><desc id="description">{escape(description)}</desc>'
            f'<rect x="0.5" y="0.5" width="469" height="{height - 1}" rx="10" fill="#0d1117" stroke="#30363d"/>'
            '<g font-family="Arial, Helvetica, sans-serif">'
            + text(24, 34, title, 19, '#58a6ff') + body + '</g></svg>\n')


def render(username, stats, updated):
    scope = 'Public, non-fork repositories'
    body = ''.join(text(24, y, label) + text(390, y, f'{stats[key]:,}', 16, '#ffffff')
                   for y, label, key in [(76, 'Repositories', 'repos'), (112, 'Stars earned', 'stars'), (148, 'Forks received', 'forks')])
    body += text(24, 181, scope, 11, '#8b949e') + text(24, 200, 'Updated ' + updated + ' UTC', 11, '#8b949e')
    summary = card(username + "'s GitHub Stats", scope, body, 220)
    languages = sorted(stats['languages'].items(), key=lambda pair: (-pair[1], pair[0]))[:6]
    total = sum(stats['languages'].values())
    rows = ''
    for i, (name, count) in enumerate(languages):
        y = 65 + i * 27
        percent = count / total * 100 if total else 0
        rows += text(24, y, name, 13) + text(390, y, f'{percent:.1f}%', 13)
        rows += f'<rect x="180" y="{y - 10}" width="{percent * 1.8:.1f}" height="8" rx="4" fill="#58a6ff"/>'
    if not languages:
        rows = text(24, 80, 'No language data')
    rows += text(24, 240, 'Share of code bytes in public, non-fork repos', 11, '#8b949e')
    rows += text(24, 259, 'Updated ' + updated + ' UTC', 11, '#8b949e')
    return {'github-stats.svg': summary,
            'top-languages.svg': card('Top Languages', 'Language share by code bytes; ' + scope, rows, 280)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', default=os.environ.get('GITHUB_REPOSITORY_OWNER', 'kpulik'))
    parser.add_argument('--output-dir', default='Assets')
    args = parser.parse_args()
    stats = collect(args.username)
    cards = render(args.username, stats, datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for name, content in cards.items():
        (output / name).write_text(content, encoding='utf-8')
    print(f"Updated cards from {stats['repos']} public, non-fork repositories")


if __name__ == '__main__':
    main()
