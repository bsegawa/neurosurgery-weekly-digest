from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .models import Paper


RESPONSES_URL = "https://api.openai.com/v1/responses"
CATEGORIES = ["脳血管障害", "脳腫瘍・頭蓋底", "脊椎・脊髄", "外傷・集中治療", "機能・てんかん", "小児・先天性", "その他"]


def digest_schema(max_papers: int) -> dict[str, Any]:
    paper_item = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "pmid", "category", "importance", "why_selected", "title_ja", "one_liner",
            "clinical_question", "design", "population", "intervention", "comparator",
            "key_results", "clinical_takeaway", "limitations", "practice_impact",
        ],
        "properties": {
            "pmid": {"type": "string"},
            "category": {"type": "string", "enum": CATEGORIES},
            "importance": {"type": "string", "enum": ["必読", "注目", "参考"]},
            "why_selected": {"type": "string"},
            "title_ja": {"type": "string"},
            "one_liner": {"type": "string"},
            "clinical_question": {"type": "string"},
            "design": {"type": "string"},
            "population": {"type": "string"},
            "intervention": {"type": "string"},
            "comparator": {"type": "string"},
            "key_results": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["label", "value"],
                    "properties": {
                        "label": {"type": "string"},
                        "value": {"type": "string"},
                    },
                },
            },
            "clinical_takeaway": {"type": "string"},
            "limitations": {"type": "array", "minItems": 1, "maxItems": 4, "items": {"type": "string"}},
            "practice_impact": {"type": "string", "enum": ["診療変更を検討", "知識更新", "今後の検証待ち"]},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["overview", "selection_note", "papers"],
        "properties": {
            "overview": {"type": "string"},
            "selection_note": {"type": "string"},
            "papers": {
                "type": "array",
                "minItems": 1,
                "maxItems": max_papers,
                "items": paper_item,
            },
        },
    }


SYSTEM_PROMPT = """あなたは脳神経外科専門医かつ臨床疫学に習熟したエビデンスレビュアーです。
与えられたPubMed書誌情報と抄録だけを根拠に、日本語で週刊ダイジェストを作成してください。

厳守事項:
- 抄録に記載されていない数値、対象、手技、結論を推測・補完しない。
- 不明な項目は「抄録では不明」または「該当なし」と明記する。
- 相対効果だけでなく、抄録にあれば絶対数、分母、信頼区間、追跡期間を優先する。
- 因果関係を断定せず、研究デザインに合った表現を使う。
- 診療変更を検討とするのは、方法と結果が十分強い場合に限る。
- 選定ではRCT、ガイドライン、メタ解析、前向き・多施設研究、大規模研究、実臨床への影響を重視する。
- 脳神経外科全般を扱い、質を損なわない範囲で領域の偏りを避ける。
- PMIDは候補に存在する値だけを使い、同じPMIDを重複させない。
- 原著タイトル、著者、雑誌名、リンクは出力せず、PMIDで参照させる。
"""


def create_digest(papers: list[Paper], paper_count: int = 10) -> dict[str, Any]:
    if not papers:
        raise ValueError("No candidate papers were supplied")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    requested = min(max(1, paper_count), len(papers))
    prompt = {
        "instruction": f"候補から臨床的価値の高い論文を最大{requested}報選び、指定形式で要約してください。",
        "candidates": [paper.to_prompt_dict() for paper in papers],
    }
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
        "store": False,
        "reasoning": {"effort": "low"},
        "max_output_tokens": 18000,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "neurosurgery_weekly_digest",
                "strict": True,
                "schema": digest_schema(requested),
            }
        },
    }
    request = urllib.request.Request(
        RESPONSES_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"OpenAI API error {exc.code}: {body}") from exc
    output_text = _extract_output_text(result)
    digest = json.loads(output_text)
    return attach_metadata(digest, papers)


def _extract_output_text(response: dict[str, Any]) -> str:
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]
    raise RuntimeError("OpenAI response did not contain output_text")


def attach_metadata(digest: dict[str, Any], candidates: list[Paper]) -> dict[str, Any]:
    lookup = {paper.pmid: paper for paper in candidates}
    seen: set[str] = set()
    attached: list[dict[str, Any]] = []
    for summary in digest.get("papers", []):
        pmid = str(summary.get("pmid", ""))
        if pmid in seen or pmid not in lookup:
            continue
        seen.add(pmid)
        merged = lookup[pmid].to_dict()
        merged.update(summary)
        attached.append(merged)
    if not attached:
        raise RuntimeError("The model did not select a valid PMID")
    digest["papers"] = attached
    return digest

