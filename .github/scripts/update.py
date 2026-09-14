"""Refresh the OSS and TIL sections of README.md. Stdlib only."""
import json, os, re, urllib.parse, urllib.request

USER = "jang-hs"
EXCLUDE_ORGS = ["pylerAI", "learn-programmers"]
TIL = "https://jang-hs.github.io/TIL/"


def get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": USER})
    if "api.github.com" in url and os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode()
    return body if raw else json.loads(body)


def oss(limit=2):
    base = f"author:{USER} type:pr -user:{USER} " + " ".join(f"-org:{o}" for o in EXCLUDE_ORGS)
    lines = []
    # merged first (newest merge), then open (newest created)
    for icon, qual, sort in [("✅", "is:merged", "updated"), ("🟡", "is:open", "created")]:
        url = f"https://api.github.com/search/issues?per_page=10&sort={sort}&q=" + urllib.parse.quote(f"{base} {qual}")
        items = get(url)["items"]
        if qual == "is:merged":
            items.sort(key=lambda i: i["pull_request"]["merged_at"], reverse=True)
        for i in items[:limit]:
            repo = i["repository_url"].split("/repos/")[1]
            lines.append(f"- {icon} [{repo}#{i['number']}]({i['html_url']}) — {i['title']}")
    return lines


def til(limit=1):
    tree = get(f"https://api.github.com/repos/{USER}/TIL/git/trees/main?recursive=1")["tree"]
    # post pages are named <category>/<YYMMDD>-<slug>.html
    posts = [t["path"] for t in tree if re.fullmatch(r"[\w-]+/\d{6}-[\w-]+\.html", t["path"])]
    posts.sort(key=lambda p: p.split("/")[1], reverse=True)
    lines = []
    for p in posts[:limit]:
        m = re.search(r"<title>(.*?) \| Today I Learned", get(TIL + p, raw=True))
        d = p.split("/")[1][:6]
        lines.append(f"- [{m.group(1) if m else p}]({TIL}{p}) <sub>20{d[:2]}-{d[2:4]}-{d[4:]}</sub>")
    return lines


def replace(text, tag, lines):
    return re.sub(rf"(<!-- {tag}:START -->).*?(<!-- {tag}:END -->)",
                  lambda m: m.group(1) + "\n" + "\n".join(lines) + "\n" + m.group(2), text, flags=re.S)


if __name__ == "__main__":
    readme = open("README.md", encoding="utf-8").read()
    readme = replace(readme, "OSS", oss())
    readme = replace(readme, "TIL", til())
    open("README.md", "w", encoding="utf-8").write(readme)
