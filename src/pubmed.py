from __future__ import annotations

import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, timedelta

from .models import Paper


EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
USER_AGENT = "NeurosurgeryWeeklyDigest/1.0"

JOURNALS = [
    "Neurosurgery",
    "Journal of Neurosurgery",
    "Journal of Neurosurgery. Spine",
    "Journal of Neurosurgery. Pediatrics",
    "Neurosurgical Focus",
    "Operative Neurosurgery",
    "World Neurosurgery",
    "Acta Neurochirurgica",
    "Neurosurgical Review",
    "Journal of NeuroInterventional Surgery",
    "AJNR. American Journal of Neuroradiology",
    "Stroke",
    "JAMA Neurology",
    "Neurology",
    "Neuro-Oncology",
    "Journal of Neurotrauma",
    "Stereotactic and Functional Neurosurgery",
]

CATEGORY_KEYWORDS = {
    "脳血管障害": [
        "aneurysm", "subarachnoid", "stroke", "thrombectomy", "ischemic",
        "intracerebral hemorrhage", "arteriovenous", "moyamoya", "carotid",
        "flow diverter", "embolization", "vascular",
    ],
    "脳腫瘍・頭蓋底": [
        "glioma", "glioblastoma", "meningioma", "metastasis", "pituitary",
        "skull base", "schwannoma", "neuro-oncology", "tumor", "tumour",
    ],
    "脊椎・脊髄": [
        "spine", "spinal", "cervical", "lumbar", "thoracic", "myelopathy",
        "spondyl", "fusion",
    ],
    "外傷・集中治療": [
        "traumatic brain", "head injury", "subdural", "intracranial pressure",
        "neurocritical", "trauma",
    ],
    "機能・てんかん": [
        "deep brain stimulation", "epilep", "functional neurosurgery",
        "movement disorder", "neuromodulation", "stereotactic",
    ],
    "小児・先天性": [
        "pediatric", "paediatric", "hydrocephalus", "craniosynostosis",
        "neural tube", "chiari",
    ],
}

HIGH_VALUE_TYPES = {
    "randomized controlled trial": 6,
    "controlled clinical trial": 5,
    "systematic review": 4,
    "meta-analysis": 4,
    "practice guideline": 6,
    "multicenter study": 3,
    "clinical trial": 3,
}

JOURNAL_WEIGHTS = {
    "the lancet neurology": 8,
    "new england journal of medicine": 8,
    "jama": 7,
    "jama neurology": 7,
    "stroke": 6,
    "neurology": 5,
    "neuro-oncology": 5,
    "journal of neurointerventional surgery": 5,
    "journal of neurosurgery": 5,
    "neurosurgery": 5,
}


def _text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def _request(endpoint: str, params: dict[str, str], retries: int = 3) -> bytes:
    api_key = os.getenv("NCBI_API_KEY", "").strip()
    email = os.getenv("NCBI_EMAIL", "").strip()
    if api_key:
        params["api_key"] = api_key
    if email:
        params["email"] = email
    url = f"{EUTILS}/{endpoint}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("NCBI request failed")


def _query(start: date, end: date) -> str:
    journal_clause = " OR ".join(f'"{journal}"[jour]' for journal in JOURNALS)
    topic_clause = " OR ".join(
        [
            "neurosurg*[tiab]",
            '"endovascular treatment"[tiab]',
            '"brain tumor"[tiab]',
            '"brain tumour"[tiab]',
            '"spinal surgery"[tiab]',
            '"traumatic brain injury"[tiab]',
            '"deep brain stimulation"[tiab]',
        ]
    )
    date_clause = f'("{start:%Y/%m/%d}"[dp] : "{end:%Y/%m/%d}"[dp])'
    return (
        f"(({journal_clause}) OR ({topic_clause})) AND hasabstract[text] AND {date_clause} "
        "NOT (editorial[pt] OR comment[pt] OR letter[pt] OR news[pt])"
    )


def search_pmids(lookback_days: int = 8, max_results: int = 120) -> list[str]:
    end = date.today()
    start = end - timedelta(days=max(1, lookback_days))
    payload = _request(
        "esearch.fcgi",
        {
            "db": "pubmed",
            "term": _query(start, end),
            "retmode": "xml",
            "retmax": str(max_results),
            "sort": "pub date",
        },
    )
    root = ET.fromstring(payload)
    return [node.text for node in root.findall(".//IdList/Id") if node.text]


def fetch_papers(pmids: list[str]) -> list[Paper]:
    if not pmids:
        return []
    payload = _request(
        "efetch.fcgi",
        {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        },
    )
    root = ET.fromstring(payload)
    papers: list[Paper] = []
    for record in root.findall(".//PubmedArticle"):
        citation = record.find("MedlineCitation")
        article = citation.find("Article") if citation is not None else None
        if citation is None or article is None:
            continue
        pmid = _text(citation.find("PMID"))
        title = _text(article.find("ArticleTitle"))
        journal = _text(article.find("Journal/Title")) or _text(article.find("Journal/ISOAbbreviation"))
        pub_date_node = article.find("Journal/JournalIssue/PubDate")
        publication_date = _parse_date(pub_date_node)
        abstract_parts = []
        for abstract_node in article.findall("Abstract/AbstractText"):
            label = abstract_node.attrib.get("Label", "").strip()
            value = _text(abstract_node)
            if value:
                abstract_parts.append(f"{label}: {value}" if label else value)
        abstract = "\n".join(abstract_parts)
        authors = []
        for author in article.findall("AuthorList/Author"):
            collective = _text(author.find("CollectiveName"))
            if collective:
                authors.append(collective)
                continue
            name = " ".join(filter(None, [_text(author.find("ForeName")), _text(author.find("LastName"))]))
            if name:
                authors.append(name)
        publication_types = [_text(node) for node in article.findall("PublicationTypeList/PublicationType")]
        doi = ""
        pmcid = ""
        for article_id in record.findall("PubmedData/ArticleIdList/ArticleId"):
            id_type = article_id.attrib.get("IdType", "")
            if id_type == "doi":
                doi = _text(article_id)
            elif id_type == "pmc":
                pmcid = _text(article_id)
        if pmid and title and abstract:
            paper = Paper(
                pmid=pmid,
                title=title,
                journal=journal,
                publication_date=publication_date,
                authors=authors,
                abstract=abstract,
                doi=doi,
                pmcid=pmcid,
                publication_types=publication_types,
            )
            paper.category_hint = classify_category(f"{title} {abstract}")
            paper.score = pre_rank_score(paper)
            papers.append(paper)
    return papers


def _parse_date(pub_date_node: ET.Element | None) -> str:
    if pub_date_node is None:
        return ""
    medline = _text(pub_date_node.find("MedlineDate"))
    if medline:
        return medline
    year = _text(pub_date_node.find("Year"))
    month = _text(pub_date_node.find("Month"))
    day = _text(pub_date_node.find("Day"))
    return " ".join(filter(None, [year, month, day]))


def classify_category(text: str) -> str:
    normalized = text.casefold()
    best_category = "その他"
    best_count = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        count = sum(1 for keyword in keywords if keyword in normalized)
        if count > best_count:
            best_category = category
            best_count = count
    return best_category


def pre_rank_score(paper: Paper) -> float:
    score = 0.0
    journal = paper.journal.casefold()
    for name, weight in JOURNAL_WEIGHTS.items():
        if name in journal:
            score += weight
            break
    types = " ".join(paper.publication_types).casefold()
    for publication_type, weight in HIGH_VALUE_TYPES.items():
        if publication_type in types:
            score += weight
    title = paper.title.casefold()
    if any(term in title for term in ["randomized", "guideline", "consensus", "multicenter", "systematic review"]):
        score += 3
    if any(term in title for term in ["case report", "technical note"]):
        score -= 2
    return score


def collect_candidates(lookback_days: int = 8, max_candidates: int = 35) -> list[Paper]:
    papers = fetch_papers(search_pmids(lookback_days=lookback_days))
    papers.sort(key=lambda paper: (paper.score, paper.publication_date), reverse=True)
    return papers[:max_candidates]

