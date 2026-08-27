"""Request models for api/routes/agent_lab.py -- אותה קונבנציה כמו api/rag_schemas.py:
תגובות הן dict רגיל (artifacts רחבים ומשתנים), רק בקשות מאומתות ב-Pydantic."""

from typing import Literal

from pydantic import BaseModel, Field

ConfigKind = Literal["rag", "agent"]


class RunRequest(BaseModel):
    task: str = Field(min_length=1)
    config: ConfigKind = "agent"
    enabled_tools: list[str] | None = None
    break_tool: str | None = None
    use_evaluator_optimizer: bool = True
    # ברירת המחדל בכל מקום היא הקונפיגורציה הקנונית של המטלה -- ראו src/model_providers.py.
    # Gemini הוא אופציה זמינה לבקרת עלות, לא תחליף שקט להשוואה הרשמית של Task 5.
    model: str = "claude-haiku-4-5"
    judge_model: str = "claude-sonnet-5"
    system_prompt: str | None = None


class AddConfigRequest(BaseModel):
    name: str = Field(min_length=1)
    model: str = "claude-haiku-4-5"
    judge_model: str = "claude-sonnet-5"
    enabled_tools: list[str] = Field(default_factory=lambda: ["search_tax_corpus", "calculator", "calculate_tax_refund"])
    system_prompt: str | None = None
