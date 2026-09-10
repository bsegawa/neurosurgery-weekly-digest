from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path


PUSH_URL = "https://api.line.me/v2/bot/message/push"


def latest_issue(data_dir: Path = Path("data")) -> dict:
    paths = sorted((data_dir / "issues").glob("*.json"), reverse=True)
    if not paths:
        raise RuntimeError("No issue archive was found")
    return json.loads(paths[0].read_text(encoding="utf-8"))


def build_message(issue: dict, public_base_url: str) -> dict:
    base = public_base_url.rstrip("/")
    issue_url = f"{base}/issues/{issue['issue_date']}/"
    titles = "\n".join(
        f"{index}. {paper.get('title_ja', paper.get('title', ''))[:62]}"
        for index, paper in enumerate(issue.get("papers", [])[:3], 1)
    )
    text = (
        f"🧠 Neurosurgery Weekly\n{issue['period']}\n\n"
        f"今週の注目論文 {len(issue.get('papers', []))}報\n{titles}\n\n"
        f"要約・Visualサマリを読む\n{issue_url}"
    )
    return {
        "to": os.environ["LINE_USER_ID"],
        "messages": [
            {"type": "text", "text": text[:4900]},
            {
                "type": "flex",
                "altText": f"Neurosurgery Weekly {issue['issue_date']}",
                "contents": {
                    "type": "bubble",
                    "header": {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#071B2E",
                        "contents": [
                            {"type": "text", "text": "NEUROSURGERY WEEKLY", "color": "#5EE0D6", "size": "xs", "weight": "bold"},
                            {"type": "text", "text": "今週の注目論文", "color": "#FFFFFF", "size": "xl", "weight": "bold", "margin": "md"},
                        ],
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": issue["period"], "size": "sm", "color": "#5F7180"},
                            {"type": "text", "text": issue.get("overview", "")[:260], "wrap": True, "size": "sm", "margin": "lg"},
                        ],
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "button", "style": "primary", "color": "#1AB7B0", "action": {"type": "uri", "label": "Visualサマリを開く", "uri": issue_url}}
                        ],
                    },
                },
            },
        ],
    }


def send_line(payload: dict, token: str) -> None:
    request = urllib.request.Request(
        PUSH_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            if response.status != 200:
                raise RuntimeError(f"LINE API returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"LINE API error {exc.code}: {body}") from exc


def main() -> None:
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    user_id = os.getenv("LINE_USER_ID", "").strip()
    public_url = os.getenv("PUBLIC_BASE_URL", "").strip()
    missing = [name for name, value in [("LINE_CHANNEL_ACCESS_TOKEN", token), ("LINE_USER_ID", user_id), ("PUBLIC_BASE_URL", public_url)] if not value]
    if missing:
        raise RuntimeError(f"Missing required notification configuration: {', '.join(missing)}")
    send_line(build_message(latest_issue(), public_url), token)
    print("LINE notification sent")


if __name__ == "__main__":
    main()

