import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from core.config import MODEL_NAME, OPENAI_API_KEY
from schemas import RouteDecision


class QueryRouter:
    """
    Hybrid Router:
    1. Rule-based fast path for high-confidence intents.
    2. LLM fallback for semantic / ambiguous queries.
    3. Safe default to direct answer.
    """

    def __init__(self) -> None:
        self._llm_chain = None

        if OPENAI_API_KEY:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        (
                            "You are a routing classifier for an AI marketing agent.\n\n"
                            "Classify the user query into exactly one route:\n"
                            "- rag: needs customer/product/inventory/project document retrieval\n"
                            "- tool: asks the agent to perform an action such as create/get/update/search\n"
                            "- direct: general question or explanation, no tool or retrieval needed\n\n"
                            "Return only valid JSON:\n"
                            "{\n"
                            '  "route": "rag|tool|direct",\n'
                            '  "reason": "...",\n'
                            '  "confidence": 0.0\n'
                            "}"
                        ),
                    ),
                    (
                        "human",
                        "Conversation history:\n{history}\n\nUser query:\n{query}",
                    ),
                ]
            )

            llm = ChatOpenAI(
                model=MODEL_NAME,
                api_key=OPENAI_API_KEY,
                temperature=0,
            )

            self._llm_chain = prompt | llm | StrOutputParser()

    def route(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> RouteDecision:
        text = query.strip()
        lowered = text.lower()

        rule_decision = self._rule_route(lowered, text)

        if rule_decision.confidence >= 0.85:
            return rule_decision

        llm_decision = self._llm_route(text, history or [])

        if llm_decision:
            return llm_decision

        return rule_decision

    def _rule_route(self, lowered: str, original: str) -> RouteDecision:
        tool_name, tool_input = self._select_tool(lowered, original)

        if tool_name:
            return RouteDecision(
                route="tool",
                reason=f"Rule matched tool intent: {tool_name}",
                confidence=0.95,
                matched_rules=[f"tool:{tool_name}"],
                tool_name=tool_name,
                tool_input=tool_input,
            )

        rag_keywords = [
            "repo",
            "docs",
            "document",
            "knowledge base",
            "customer",
            "customers",
            "segment",
            "segments",
            "inventory",
            "product",
            "products",
            "preference",
            "preferences",
            "purchase",
            "purchased",
            "bought",
            "campaign data",
            "based on",
            "according to",
            "citation",
            "source",
        ]

        matched_rag_keywords = [k for k in rag_keywords if k in lowered]

        if matched_rag_keywords:
            return RouteDecision(
                route="rag",
                reason="Rule matched retrieval/knowledge intent.",
                confidence=0.9,
                matched_rules=[
                    f"rag_keyword:{k}" for k in matched_rag_keywords[:5]
                ],
            )

        direct_keywords = [
            "hello",
            "hi",
            "thanks",
            "thank you",
            "what is",
            "explain",
            "define",
        ]

        matched_direct_keywords = [k for k in direct_keywords if k in lowered]

        if matched_direct_keywords or len(lowered.split()) <= 3:
            return RouteDecision(
                route="direct",
                reason="Rule matched simple/direct question.",
                confidence=0.85,
                matched_rules=[
                    f"direct_keyword:{k}" for k in matched_direct_keywords[:5]
                ] or ["short_query"],
            )

        return RouteDecision(
            route="direct",
            reason="Rules were inconclusive; default candidate is direct.",
            confidence=0.55,
            matched_rules=["rule_inconclusive"],
        )

    def _llm_route(
        self,
        query: str,
        history: List[Dict[str, str]],
    ) -> Optional[RouteDecision]:
        if not self._llm_chain:
            return None

        try:
            history_text = "\n".join(
                [
                    f"{msg['role']}: {msg['content']}"
                    for msg in history[-6:]
                ]
            )

            raw = self._llm_chain.invoke(
                {
                    "query": query,
                    "history": history_text or "No previous history.",
                }
            )

            parsed = json.loads(raw)

            route = str(parsed.get("route", "direct")).lower().strip()

            if route not in {"rag", "tool", "direct"}:
                route = "direct"

            return RouteDecision(
                route=route,
                reason=str(parsed.get("reason", "LLM fallback routing decision.")),
                confidence=float(parsed.get("confidence", 0.65)),
                matched_rules=["llm_fallback"],
            )

        except Exception:
            return None

    def _select_tool(
        self,
        lowered: str,
        original: str,
    ) -> tuple[Optional[str], Dict[str, Any]]:
        draft_id = self._extract_draft_id(lowered)

        if draft_id and any(
            word in lowered
            for word in ["get", "show", "fetch", "read", "open", "查看"]
        ):
            return "get_draft", {"draft_id": draft_id}

        if draft_id and any(
            word in lowered
            for word in ["update", "edit", "revise", "rewrite", "change", "修改", "改"]
        ):
            return "update_draft", {
                "draft_id": draft_id,
                "edit_instruction": original,
            }

        if any(
            phrase in lowered
            for phrase in [
                "create draft",
                "generate draft",
                "save draft",
                "write email",
                "generate email",
                "campaign email",
                "compose email",
                "写邮件",
                "生成邮件",
                "创建draft",
                "生成draft",
            ]
        ):
            return "create_draft", {
                "title": "AI-generated campaign draft",
                "content": original,
                "created_by": "agent",
                "workspace_id": "default",
            }

        if lowered.startswith("search ") or lowered.startswith("lookup "):
            return "search", {"query": original}

        return None, {}

    def _extract_draft_id(self, lowered: str) -> Optional[str]:
        patterns = [
            r"draft[_\s-]?id[:\s#-]*([a-zA-Z0-9_-]+)",
            r"draft[:\s#-]+([a-zA-Z0-9_-]+)",
            r"draft\s+([a-zA-Z0-9_-]+)",
            r"([a-zA-Z0-9_-]+)\s*号\s*draft",
        ]

        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return match.group(1)

        return None