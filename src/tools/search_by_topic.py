import csv
from pathlib import Path

from src.custom_logger import setup_logger
from src.models import SearchOutput

MAX_SEARCH_RESULTS = 5

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

logger = setup_logger(__name__)


def _search_csv(csv_path: Path, keywords: list[str]) -> list[SearchOutput]:
    """CSVファイルをキーワード検索する共通処理。"""

    if not csv_path.exists():
        logger.warning(f"CSV not found: {csv_path}")
        return []

    query_keywords = {k.strip() for k in keywords if k.strip()}
    if not query_keywords:
        return []

    logger.info(f"Searching {csv_path.name} with keywords: {query_keywords}")

    scored_results: list[tuple[int, SearchOutput]] = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_keywords = {k.strip() for k in row.get("キーワード", "").split(",") if k.strip()}
            matched = query_keywords & row_keywords
            if not matched:
                continue

            scored_results.append((
                len(matched),
                SearchOutput(file_name=csv_path.name, content=row.get("内容", "")),
            ))

    scored_results.sort(key=lambda x: x[0], reverse=True)
    results = [r[1] for r in scored_results[:MAX_SEARCH_RESULTS]]

    logger.info(f"Search results: {len(results)} hits (from {len(scored_results)} candidates)")
    return results
