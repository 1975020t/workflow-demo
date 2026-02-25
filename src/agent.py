from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.pregel import Pregel
from openai import OpenAI

from src.configs import Settings
from src.custom_logger import setup_logger
from src.models import FilteredData, QuestionAnalysis, SearchOutput, WorkflowResult
from src.prompts import (
    ANALYZE_QUESTION_SYSTEM_PROMPT,
    ANALYZE_QUESTION_USER_PROMPT,
    FALLBACK_ANSWER,
    FILTER_RESULTS_SYSTEM_PROMPT,
    FILTER_RESULTS_USER_PROMPT,
    GENERATE_ANSWER_SYSTEM_PROMPT,
    GENERATE_ANSWER_USER_PROMPT,
)
from src.tools.search_account import search_account
from src.tools.search_project import search_project
from src.tools.search_report import search_report
from src.tools.search_system import search_system

logger = setup_logger(__file__)


class WorkflowState(TypedDict):
    question: str
    analysis: QuestionAnalysis | None
    search_results: list[SearchOutput]
    filtered_data: list[str]
    answer: str


class HelpDeskWorkflow:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(api_key=self.settings.openai_api_key)

    # ------------------------------------------------------------------
    # Step 1: 質問分析（LLM - キーワード抽出 + ルーティング判定）
    # ------------------------------------------------------------------
    def analyze_question(self, state: WorkflowState) -> dict:
        logger.info("Step 1: 質問分析を開始...")

        user_prompt = ANALYZE_QUESTION_USER_PROMPT.format(question=state["question"])
        messages = [
            {"role": "system", "content": ANALYZE_QUESTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        response = self.client.beta.chat.completions.parse(
            model=self.settings.openai_model,
            messages=messages,
            response_format=QuestionAnalysis,
        )

        analysis = response.choices[0].message.parsed
        logger.info(f"Step 1 完了: keywords={analysis.keywords}, data_source={analysis.data_source}")

        return {"analysis": analysis}

    # ------------------------------------------------------------------
    # ルーティング関数
    # ------------------------------------------------------------------
    @staticmethod
    def route_by_data_source(state: WorkflowState) -> str:
        return f"search_{state['analysis'].data_source}"

    # ------------------------------------------------------------------
    # Step 2: ドメイン別データ検索（プログラム的 - LLM不要）
    # ------------------------------------------------------------------
    def search_account(self, state: WorkflowState) -> dict:
        keywords = state["analysis"].keywords
        logger.info(f"Step 2: アカウントデータを検索... keywords={keywords}")
        results = search_account(keywords)
        logger.info(f"Step 2 完了: {len(results)}件の検索結果")
        return {"search_results": results}

    def search_project(self, state: WorkflowState) -> dict:
        keywords = state["analysis"].keywords
        logger.info(f"Step 2: プロジェクトデータを検索... keywords={keywords}")
        results = search_project(keywords)
        logger.info(f"Step 2 完了: {len(results)}件の検索結果")
        return {"search_results": results}

    def search_report(self, state: WorkflowState) -> dict:
        keywords = state["analysis"].keywords
        logger.info(f"Step 2: レポートデータを検索... keywords={keywords}")
        results = search_report(keywords)
        logger.info(f"Step 2 完了: {len(results)}件の検索結果")
        return {"search_results": results}

    def search_system(self, state: WorkflowState) -> dict:
        keywords = state["analysis"].keywords
        logger.info(f"Step 2: システムデータを検索... keywords={keywords}")
        results = search_system(keywords)
        logger.info(f"Step 2 完了: {len(results)}件の検索結果")
        return {"search_results": results}

    # ------------------------------------------------------------------
    # Step 3: データ絞り込み（LLM）
    # ------------------------------------------------------------------
    def filter_results(self, state: WorkflowState) -> dict:
        if not state["search_results"]:
            logger.info("Step 3: 検索結果0件のためスキップ（フォールバック）")
            return {"filtered_data": [], "answer": FALLBACK_ANSWER}

        logger.info(f"Step 3: データ絞り込みを開始... ({len(state['search_results'])}件)")

        search_results_text = "\n\n".join(
            f"[{i + 1}] ({r.file_name})\n{r.content}"
            for i, r in enumerate(state["search_results"])
        )

        user_prompt = FILTER_RESULTS_USER_PROMPT.format(
            question=state["question"],
            search_results=search_results_text,
        )
        messages = [
            {"role": "system", "content": FILTER_RESULTS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        response = self.client.beta.chat.completions.parse(
            model=self.settings.openai_model,
            messages=messages,
            response_format=FilteredData,
        )

        filtered = response.choices[0].message.parsed
        logger.info(f"Step 3 完了: {len(filtered.relevant_entries)}件に絞り込み")

        if not filtered.relevant_entries:
            return {"filtered_data": [], "answer": FALLBACK_ANSWER}

        return {"filtered_data": filtered.relevant_entries}

    # ------------------------------------------------------------------
    # Step 4: 回答生成（LLM）
    # ------------------------------------------------------------------
    def generate_answer(self, state: WorkflowState) -> dict:
        if state.get("answer"):
            logger.info("Step 4: フォールバック回答が設定済みのためスキップ")
            return {}

        logger.info("Step 4: 回答生成を開始...")

        filtered_text = "\n\n".join(state["filtered_data"])
        user_prompt = GENERATE_ANSWER_USER_PROMPT.format(
            question=state["question"],
            filtered_data=filtered_text,
        )
        messages = [
            {"role": "system", "content": GENERATE_ANSWER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
        )

        answer = response.choices[0].message.content
        logger.info("Step 4 完了: 回答生成完了")

        return {"answer": answer}

    # ------------------------------------------------------------------
    # グラフ構築
    # ------------------------------------------------------------------
    def create_graph(self) -> Pregel:
        workflow = StateGraph(WorkflowState)

        workflow.add_node("analyze_question", self.analyze_question)
        workflow.add_node("search_account", self.search_account)
        workflow.add_node("search_project", self.search_project)
        workflow.add_node("search_report", self.search_report)
        workflow.add_node("search_system", self.search_system)
        workflow.add_node("filter_results", self.filter_results)
        workflow.add_node("generate_answer", self.generate_answer)

        workflow.add_edge(START, "analyze_question")

        workflow.add_conditional_edges(
            "analyze_question",
            self.route_by_data_source,
            {
                "search_account": "search_account",
                "search_project": "search_project",
                "search_report": "search_report",
                "search_system": "search_system",
            },
        )

        workflow.add_edge("search_account", "filter_results")
        workflow.add_edge("search_project", "filter_results")
        workflow.add_edge("search_report", "filter_results")
        workflow.add_edge("search_system", "filter_results")
        workflow.add_edge("filter_results", "generate_answer")
        workflow.add_edge("generate_answer", END)

        return workflow.compile()

    # ------------------------------------------------------------------
    # 実行
    # ------------------------------------------------------------------
    def run(self, question: str) -> WorkflowResult:
        app = self.create_graph()
        result = app.invoke({
            "question": question,
            "analysis": None,
            "search_results": [],
            "filtered_data": [],
            "answer": "",
        })
        return WorkflowResult(
            question=question,
            analysis=result["analysis"],
            search_results=result["search_results"],
            filtered_data=result["filtered_data"],
            answer=result["answer"],
        )
