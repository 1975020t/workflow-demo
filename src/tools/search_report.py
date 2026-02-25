from src.models import SearchOutput
from src.tools.search_by_topic import DATA_DIR, _search_csv

CSV_PATH = DATA_DIR / "ds_report.csv"


def search_report(keywords: list[str]) -> list[SearchOutput]:
    """レポート・データ出力ドメインのCSVを検索する。"""
    return _search_csv(CSV_PATH, keywords)

