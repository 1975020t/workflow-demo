from src.models import SearchOutput
from src.tools.search_by_topic import DATA_DIR, _search_csv

CSV_PATH = DATA_DIR / "ds_system.csv"


def search_system(keywords: list[str]) -> list[SearchOutput]:
    """システム管理ドメインのCSVを検索する。"""
    return _search_csv(CSV_PATH, keywords)

