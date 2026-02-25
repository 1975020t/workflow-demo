"""ヘルプデスクワークフローをCLIから実行するスクリプト"""

import argparse
import os
import sys
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                os.environ[key] = value

from src.agent import HelpDeskWorkflow
from src.configs import Settings

DEFAULT_PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "question.txt"


def main() -> None:
    parser = argparse.ArgumentParser(description="ヘルプデスクワークフローを実行します")
    parser.add_argument(
        "-f", "--file",
        type=str,
        default=str(DEFAULT_PROMPT_FILE),
        help="質問が記載されたテキストファイルのパス (デフォルト: prompts/question.txt)",
    )
    args = parser.parse_args()

    prompt_path = Path(args.file)
    if not prompt_path.exists():
        print(f"エラー: ファイルが見つかりません: {prompt_path}")
        return

    question = prompt_path.read_text(encoding="utf-8").strip()
    if not question:
        print("エラー: 質問ファイルが空です")
        return

    print(f"プロンプトファイル: {prompt_path}")
    print(f"質問:\n{question}\n")

    settings = Settings()
    print(f"Model: {settings.openai_model}")
    print(f"Base:  {settings.openai_api_base}")
    print()

    workflow = HelpDeskWorkflow(settings=settings)
    result = workflow.run(question)

    print()
    print("=" * 50)
    print("ANALYSIS")
    print("=" * 50)
    print(f"  Data Source: {result.analysis.data_source}")
    print(f"  Keywords:    {result.analysis.keywords}")

    print()
    print("=" * 50)
    print(f"SEARCH RESULTS ({len(result.search_results)} hits)")
    print("=" * 50)
    for i, sr in enumerate(result.search_results):
        print(f"  [{i + 1}] {sr.content[:80]}...")

    print()
    print("=" * 50)
    print("FINAL ANSWER")
    print("=" * 50)
    print(result.answer)


if __name__ == "__main__":
    main()
