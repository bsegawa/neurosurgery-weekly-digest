from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Paper:
    pmid: str
    title: str
    journal: str
    publication_date: str
    authors: list[str]
    abstract: str
    doi: str = ""
    pmcid: str = ""
    publication_types: list[str] = field(default_factory=list)
    category_hint: str = "その他"
    score: float = 0.0

    @property
    def pubmed_url(self) -> str:
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"

    @property
    def doi_url(self) -> str:
        return f"https://doi.org/{self.doi}" if self.doi else ""

    @property
    def pmc_url(self) -> str:
        return f"https://pmc.ncbi.nlm.nih.gov/articles/{self.pmcid}/" if self.pmcid else ""

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "pmid": self.pmid,
            "title": self.title,
            "journal": self.journal,
            "publication_date": self.publication_date,
            "publication_types": self.publication_types,
            "category_hint": self.category_hint,
            "abstract": self.abstract,
        }

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.update(
            pubmed_url=self.pubmed_url,
            doi_url=self.doi_url,
            pmc_url=self.pmc_url,
        )
        return value

