from __future__ import annotations

import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path

from .llm import create_digest
from .pubmed import collect_candidates
from .render import write_site


DATA_DIR = Path("data")
DOCS_DIR = Path("docs")


def issue_period(issue_date: date, lookback_days: int) -> str:
    start = issue_date - timedelta(days=max(1, lookback_days))
    return f"{start:%Y年%m月%d日}–{issue_date:%Y年%m月%d日}"


def save_issue(digest: dict, issue_date: date, lookback_days: int, data_dir: Path = DATA_DIR) -> Path:
    digest["issue_date"] = issue_date.isoformat()
    digest["period"] = issue_period(issue_date, lookback_days)
    target_dir = data_dir / "issues"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{issue_date.isoformat()}.json"
    target.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def demo_digest() -> dict:
    return {
        "overview": "脳血管障害、脳腫瘍、脊椎領域から、研究デザインと臨床的意義を確認するデモ版です。",
        "selection_note": "これは表示確認用の架空データです。実運用ではPubMedの新着論文から選定します。",
        "papers": [
            {
                "pmid": "DEMO001",
                "title": "Demonstration article for layout testing",
                "title_ja": "表示確認用デモ論文：Visualサマリの構成",
                "journal": "Demo Journal",
                "publication_date": "2026 Sep",
                "authors": ["Demo Author"],
                "doi": "",
                "pmcid": "",
                "publication_types": ["Demo"],
                "category": "脳血管障害",
                "importance": "注目",
                "practice_impact": "知識更新",
                "why_selected": "ページ構成、スマートフォン表示、LINEリンクを確認するためのデモです。",
                "one_liner": "論文の臨床的な意味を1文で把握できるように表示します。",
                "clinical_question": "どの臨床疑問を検証した研究か",
                "design": "研究デザインをここに表示",
                "population": "対象患者と症例数",
                "intervention": "介入または曝露",
                "comparator": "比較対照",
                "key_results": [
                    {"label": "主要評価項目", "value": "効果量・95%信頼区間"},
                    {"label": "安全性", "value": "有害事象・合併症"},
                ],
                "clinical_takeaway": "臨床でどう解釈するかを、研究の限界と分けて示します。",
                "limitations": ["表示確認用の架空データであり、医学的根拠ではありません。"],
                "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/",
                "doi_url": "",
                "pmc_url": "",
            }
        ],
    }


def run(demo: bool = False, data_dir: Path = DATA_DIR, docs_dir: Path = DOCS_DIR) -> Path:
    today = date.today()
    lookback_days = int(os.getenv("PUBMED_LOOKBACK_DAYS", "8"))
    if demo:
        digest = demo_digest()
    else:
        candidates = collect_candidates(lookback_days=lookback_days)
        if not candidates:
            raise RuntimeError("PubMed returned no eligible candidate papers")
        paper_count = int(os.getenv("DIGEST_PAPER_COUNT", "10"))
        digest = create_digest(candidates, paper_count=paper_count)
    target = save_issue(digest, today, lookback_days, data_dir=data_dir)
    write_site(data_dir, docs_dir)
    print(f"Generated {target} and {docs_dir / 'index.html'}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Generate a no-network demo issue")
    args = parser.parse_args()
    run(demo=args.demo)


if __name__ == "__main__":
    main()

