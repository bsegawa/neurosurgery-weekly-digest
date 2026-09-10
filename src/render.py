from __future__ import annotations

import html
import json
import shutil
from datetime import date
from pathlib import Path
from typing import Any


STYLE_SOURCE = Path(__file__).with_name("static") / "style.css"


def h(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def render_issue(issue: dict[str, Any]) -> str:
    cards = "\n".join(render_paper_card(paper, index + 1) for index, paper in enumerate(issue["papers"]))
    category_counts: dict[str, int] = {}
    for paper in issue["papers"]:
        category = paper.get("category", "その他")
        category_counts[category] = category_counts.get(category, 0) + 1
    categories = "".join(
        f'<span class="category-chip">{h(category)} <b>{count}</b></span>'
        for category, count in category_counts.items()
    )
    return page_shell(
        title=f"Neurosurgery Weekly — {h(issue['issue_date'])}",
        body=f"""
<header class="hero">
  <div class="hero-inner">
    <p class="eyebrow">NEUROSURGERY WEEKLY</p>
    <h1>今週の注目論文</h1>
    <p class="issue-date">{h(issue['period'])}</p>
    <p class="overview">{h(issue.get('overview'))}</p>
    <div class="category-row">{categories}</div>
  </div>
</header>
<main class="container">
  <section class="method-note">
    <strong>選定方針</strong>
    <span>{h(issue.get('selection_note'))}</span>
  </section>
  <section class="paper-list">{cards}</section>
  <footer>
    <p>AI生成要約です。原則としてPubMedの書誌情報と抄録を根拠とし、診療判断を代替しません。必ず原著本文をご確認ください。</p>
    <a href="../../index.html">バックナンバーへ</a>
  </footer>
</main>
""",
        asset_prefix="../../",
    )


def render_paper_card(paper: dict[str, Any], index: int) -> str:
    authors = ", ".join(paper.get("authors", [])[:5])
    if len(paper.get("authors", [])) > 5:
        authors += ", et al."
    results = "".join(
        f'<div class="result"><span>{h(item.get("label"))}</span><strong>{h(item.get("value"))}</strong></div>'
        for item in paper.get("key_results", [])
    )
    limitations = "".join(f"<li>{h(item)}</li>" for item in paper.get("limitations", []))
    links = [f'<a class="button primary" href="{h(paper.get("pubmed_url"))}" target="_blank" rel="noopener">PubMed</a>']
    if paper.get("doi_url"):
        links.append(f'<a class="button" href="{h(paper.get("doi_url"))}" target="_blank" rel="noopener">元論文 / DOI</a>')
    if paper.get("pmc_url"):
        links.append(f'<a class="button" href="{h(paper.get("pmc_url"))}" target="_blank" rel="noopener">無料全文</a>')
    visual_items = [
        ("Clinical question", paper.get("clinical_question")),
        ("Population", paper.get("population")),
        ("Intervention", paper.get("intervention")),
        ("Comparator", paper.get("comparator")),
    ]
    visual = "".join(
        f'<div class="visual-cell"><span>{h(label)}</span><p>{h(value)}</p></div>'
        for label, value in visual_items
    )
    return f"""
<article class="paper-card">
  <div class="paper-topline">
    <span class="paper-number">{index:02d}</span>
    <span class="badge category">{h(paper.get('category'))}</span>
    <span class="badge importance">{h(paper.get('importance'))}</span>
    <span class="impact">{h(paper.get('practice_impact'))}</span>
  </div>
  <h2>{h(paper.get('title_ja'))}</h2>
  <p class="original-title">{h(paper.get('title'))}</p>
  <p class="citation">{h(authors)} · {h(paper.get('journal'))} · {h(paper.get('publication_date'))}</p>
  <p class="one-liner">{h(paper.get('one_liner'))}</p>
  <div class="why"><strong>選定理由</strong><span>{h(paper.get('why_selected'))}</span></div>
  <div class="visual-grid">{visual}</div>
  <div class="study-row"><strong>研究デザイン</strong><span>{h(paper.get('design'))}</span></div>
  <section class="results">
    <h3>Key results</h3>
    <div class="result-grid">{results}</div>
  </section>
  <section class="takeaway">
    <h3>Clinical takeaway</h3>
    <p>{h(paper.get('clinical_takeaway'))}</p>
  </section>
  <details>
    <summary>限界・解釈上の注意</summary>
    <ul>{limitations}</ul>
  </details>
  <div class="link-row">{''.join(links)}</div>
</article>
"""


def render_index(issues: list[dict[str, Any]]) -> str:
    if not issues:
        content = '<p class="empty">まだダイジェストはありません。</p>'
    else:
        latest = issues[0]
        top_papers = "".join(
            f'<li><span>{h(paper.get("category"))}</span>{h(paper.get("title_ja"))}</li>'
            for paper in latest.get("papers", [])[:5]
        )
        archive = "".join(
            f'<a class="archive-item" href="issues/{h(issue["issue_date"])}/index.html"><b>{h(issue["issue_date"])}</b><span>{h(issue["period"])}</span><em>{len(issue.get("papers", []))} papers</em></a>'
            for issue in issues
        )
        content = f"""
<section class="latest-card">
  <p class="eyebrow">LATEST ISSUE</p>
  <h2>{h(latest['period'])}</h2>
  <p>{h(latest.get('overview'))}</p>
  <ol>{top_papers}</ol>
  <a class="button primary large" href="issues/{h(latest['issue_date'])}/index.html">最新号を読む</a>
</section>
<section class="archive">
  <h2>バックナンバー</h2>
  {archive}
</section>
"""
    return page_shell(
        title="Neurosurgery Weekly",
        body=f"""
<header class="hero compact">
  <div class="hero-inner">
    <p class="eyebrow">CURATED FOR CLINICAL PRACTICE</p>
    <h1>Neurosurgery Weekly</h1>
    <p class="overview">脳神経外科の新着論文を、臨床に使える構造へ。</p>
  </div>
</header>
<main class="container">{content}
  <footer><p>AI生成要約です。診療判断の前に必ず原著をご確認ください。</p></footer>
</main>
""",
        asset_prefix="",
    )


def page_shell(title: str, body: str, asset_prefix: str) -> str:
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <meta name="theme-color" content="#071b2e">
  <title>{h(title)}</title>
  <link rel="stylesheet" href="{asset_prefix}assets/style.css">
</head>
<body>{body}</body>
</html>
"""


def write_site(data_dir: Path, docs_dir: Path) -> list[dict[str, Any]]:
    issue_dir = data_dir / "issues"
    issue_files = sorted(issue_dir.glob("*.json"), reverse=True)
    issues = [json.loads(path.read_text(encoding="utf-8")) for path in issue_files]
    docs_dir.mkdir(parents=True, exist_ok=True)
    assets = docs_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(STYLE_SOURCE, assets / "style.css")
    (docs_dir / ".nojekyll").write_text("", encoding="utf-8")
    (docs_dir / "index.html").write_text(render_index(issues), encoding="utf-8")
    for issue in issues:
        target = docs_dir / "issues" / issue["issue_date"]
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(render_issue(issue), encoding="utf-8")
    return issues

