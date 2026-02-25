from src.models import SearchOutput
from src.tools.search_by_topic import DATA_DIR, _search_csv

CSV_PATH = DATA_DIR / "ds_account.csv"


def search_account(keywords: list[str]) -> list[SearchOutput]:
    """アカウント・認証ドメインのCSVを検索する。"""
    return _search_csv(CSV_PATH, keywords)

