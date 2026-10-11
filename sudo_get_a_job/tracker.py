"""applications.md: one row per job, readable by the user, duplicate-checked by job URL."""

import datetime
import os
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

COLUMNS = ["Date", "Company", "Role", "Platform", "Status", "Link", "Notes"]
STATUSES = ["applied", "skipped", "needs-user", "interview", "rejected", "offer", "withdrawn"]
# Query parameters that only track clicks; job ids (gh_jid, jk, currentJobId, ...) are kept.
TRACKING = re.compile(r"^(utm_.*|trk.*|refid|trackingid|ebp|src|source|ref|origin|position|pagenum|lipi)$", re.I)


def workspace():
    return Path(os.environ.get("SGAJ_WORKSPACE") or Path.home() / "job-hunt")


def tracker_file():
    return workspace() / "applications.md"


def normalize(url):
    parts = urlsplit(url.strip())
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query) if not TRACKING.match(k)))
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower().removeprefix("www."),
                       parts.path.rstrip("/"), query, ""))


def cell(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def rows():
    try:
        lines = tracker_file().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    out = []
    for line in lines:
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if len(cells) == len(COLUMNS) and cells[0] not in {"Date", "---"}:
            row = dict(zip(COLUMNS, cells))
            row["Link"] = re.sub(r"^\[.*?\]\((.*)\)$", r"\1", row["Link"])
            out.append(row)
    return out


def find(url):
    key = normalize(url)
    return next((r for r in rows() if normalize(r["Link"]) == key), None)


def write(all_rows):
    path = tracker_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Job applications", "", "Kept by sudo-get-a-job. One row per job; edit freely.", "",
             "| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    for r in all_rows:
        link = f"[link]({r['Link']})" if r["Link"] else ""
        lines.append("| " + " | ".join(cell(r[c]) if c != "Link" else link for c in COLUMNS) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def add(company, role, url, platform, status="applied", notes=""):
    if status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
    if existing := find(url):
        raise ValueError(f"already tracked on {existing['Date']} as {existing['Status']}: "
                         f"{existing['Company']} — {existing['Role']}")
    row = dict(zip(COLUMNS, [datetime.date.today().isoformat(), company, role, platform, status, url, notes]))
    write([*rows(), row])
    return row


def set_status(url, status, notes=None):
    if status not in STATUSES:
        raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
    all_rows, key = rows(), normalize(url)
    match = next((r for r in all_rows if normalize(r["Link"]) == key), None)
    if not match:
        raise ValueError("not tracked yet; use track add")
    match["Status"] = status
    if notes is not None:
        match["Notes"] = notes
    write(all_rows)
    return match
