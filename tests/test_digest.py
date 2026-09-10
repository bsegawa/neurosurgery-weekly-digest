from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from src.llm import attach_metadata
from src.main import demo_digest, issue_period, save_issue
from src.models import Paper
from src.notify import build_message
from src.pubmed import classify_category, pre_rank_score
from src.render import write_site


class DigestTests(unittest.TestCase):
    def test_category_classifier(self) -> None:
        self.assertEqual(classify_category("Mechanical thrombectomy for ischemic stroke"), "脳血管障害")
        self.assertEqual(classify_category("Lumbar spinal fusion outcomes"), "脊椎・脊髄")

    def test_pre_rank_rewards_randomized_trial(self) -> None:
        paper = Paper(
            pmid="1", title="Randomized trial", journal="Journal of Neurosurgery",
            publication_date="2026", authors=[], abstract="Abstract",
            publication_types=["Randomized Controlled Trial"],
        )
        self.assertGreaterEqual(pre_rank_score(paper), 10)

    def test_attach_metadata_rejects_unknown_and_duplicate_pmids(self) -> None:
        paper = Paper("123", "Title", "Journal", "2026", ["A"], "Abstract", doi="10.1/test")
        digest = {"papers": [{"pmid": "123", "title_ja": "要約"}, {"pmid": "123"}, {"pmid": "999"}]}
        result = attach_metadata(digest, [paper])
        self.assertEqual(len(result["papers"]), 1)
        self.assertEqual(result["papers"][0]["title"], "Title")
        self.assertEqual(result["papers"][0]["doi_url"], "https://doi.org/10.1/test")

    def test_site_generation_and_line_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "data"
            docs_dir = root / "docs"
            issue = demo_digest()
            save_issue(issue, date(2026, 9, 11), 8, data_dir=data_dir)
            issues = write_site(data_dir, docs_dir)
            self.assertTrue((docs_dir / "index.html").exists())
            self.assertTrue((docs_dir / "issues" / "2026-09-11" / "index.html").exists())
            self.assertIn("Visualサマリ", (docs_dir / "issues" / "2026-09-11" / "index.html").read_text(encoding="utf-8"))
            with patch.dict(os.environ, {"LINE_USER_ID": "Udemo"}):
                payload = build_message(issues[0], "https://example.github.io/digest/")
            encoded = json.dumps(payload, ensure_ascii=False)
            self.assertIn("https://example.github.io/digest/issues/2026-09-11/", encoded)
            self.assertEqual(payload["to"], "Udemo")

    def test_period(self) -> None:
        self.assertEqual(issue_period(date(2026, 9, 11), 8), "2026年09月03日–2026年09月11日")


if __name__ == "__main__":
    unittest.main()

