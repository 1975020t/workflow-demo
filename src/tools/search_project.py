from src.models import SearchOutput
from src.tools.search_by_topic import DATA_DIR, _search_csv

CSV_PATH = DATA_DIR / "ds_project.csv"


def search_project(keywords: list[str]) -> list[SearchOutput]:
    """プロジェクト・タスクドメインのCSVを検索する。"""
    return _search_csv(CSV_PATH, keywords)

