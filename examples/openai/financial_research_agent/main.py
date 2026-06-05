"""
Financial research agent (OpenAI Agents SDK) — WITH OpenWright evidence.

Based on the official multi-agent example:
  https://github.com/openai/openai-agents-python/tree/main/examples/financial_research_agent
That example spans several files (planner, search, fundamentals/risk analysts, writer,
verifier). This is a self-contained, runnable single-file version with the OpenWright
integration applied. The OpenWright delta is just the lines marked "+++ OpenWright" —
the 6-agent pipeline below is otherwise standard OpenAI Agents SDK code.

(One simplification vs. upstream: the search step uses a plain function_tool instead of the
hosted WebSearchTool, so it runs on any chat model with just an OPENAI_API_KEY. Swap in
`from agents import WebSearchTool` for the real thing.)

Run:
  pip install openwright-core openwright-openai-agents openai-agents
  export OPENAI_API_KEY=sk-...
  export OPENWRIGHT_CHECKPOINT_STORE="s3://your-bucket/checkpoints?lock=COMPLIANCE&days=180"  # or file://./out/cp
  python main.py
"""

from __future__ import annotations

import asyncio
import sys

from pydantic import BaseModel

from agents import Agent, Runner, function_tool, trace

import openwright  # +++ OpenWright


# ── structured outputs (same shapes as the upstream example) ──────────────────
class FinancialSearchItem(BaseModel):
    reason: str
    query: str


class FinancialSearchPlan(BaseModel):
    searches: list[FinancialSearchItem]


class AnalysisSummary(BaseModel):
    summary: str


class FinancialReportData(BaseModel):
    short_summary: str
    markdown_report: str
    follow_up_questions: list[str]


class VerificationResult(BaseModel):
    verified: bool
    issues: str


# ── tools + agents ────────────────────────────────────────────────────────────
@function_tool
def web_search(query: str) -> str:
    """Search the web for a financial query (stub — returns a placeholder note)."""
    return f"[search results for: {query}]"


planner_agent = Agent(
    name="FinancialPlannerAgent",
    instructions="Given a financial research query, produce 3-5 web searches (term + reason) "
    "to gather the context needed to answer it.",
    output_type=FinancialSearchPlan,
)

search_agent = Agent(
    name="FinancialSearchAgent",
    instructions="Use the web_search tool for the given term, then summarize the result in 1-2 "
    "concise paragraphs (under 300 words). Capture the key financial points.",
    tools=[web_search],
)

financials_agent = Agent(
    name="FundamentalsAnalystAgent",
    instructions="Given a company and recent context, write a short analysis of key financial "
    "metrics (revenue, margins, growth). Return an AnalysisSummary.",
    output_type=AnalysisSummary,
)

risk_agent = Agent(
    name="RiskAnalystAgent",
    instructions="Given a company and recent context, write a short analysis of potential red "
    "flags and risks. Return an AnalysisSummary.",
    output_type=AnalysisSummary,
)

writer_agent = Agent(
    name="FinancialWriterAgent",
    instructions="You are a senior financial analyst. Using the query, the search summaries, and "
    "the fundamentals/risk analysis tools, write a cohesive markdown report with a short summary "
    "and 2-3 follow-up questions. Return FinancialReportData.",
    output_type=FinancialReportData,
)

verifier_agent = Agent(
    name="VerificationAgent",
    instructions="Verify the report is internally consistent, clearly sourced, and makes no "
    "unsupported claims. Return a VerificationResult.",
    output_type=VerificationResult,
)


async def _summary(run_result) -> str:
    return str(run_result.final_output.summary)


# +++ OpenWright: capture the ENTIRE pipeline — planner, searches, the fundamentals/risk
# analyst tools, the writer, and the verifier — as signed, tamper-evident evidence. One
# call (a global tracing processor); none of the agents above change. The analyst tools
# are recorded as attested decisions. Ledger + key + WORM S3 checkpoint come from env.
openwright.instrument("openai-agents", decision_tools=["fundamentals_analysis", "risk_analysis"])


async def main() -> None:
    default = ("Write a short analysis of Apple's long-term revenue drivers and key risks. "
               "Avoid claims about unreleased quarterly results.")
    if sys.stdin.isatty():
        query = input("Enter a financial research query: ").strip() or default
    else:
        query = default
        print(f"> {query}")

    with trace("Financial research"):
        # 1) plan
        plan = (await Runner.run(planner_agent, f"Query: {query}")).final_output_as(FinancialSearchPlan)
        print(f"Planned {len(plan.searches)} searches")
        # 2) search (in parallel)
        async def _one(item: FinancialSearchItem) -> str:
            r = await Runner.run(search_agent, f"Term: {item.query}\nReason: {item.reason}")
            return str(r.final_output)
        results = await asyncio.gather(*[_one(s) for s in plan.searches])
        # 3) write (analysts exposed as tools to the writer)
        writer = writer_agent.clone(tools=[
            financials_agent.as_tool(tool_name="fundamentals_analysis",
                                     tool_description="Short write-up of key financial metrics",
                                     custom_output_extractor=_summary),
            risk_agent.as_tool(tool_name="risk_analysis",
                               tool_description="Short write-up of potential red flags",
                               custom_output_extractor=_summary),
        ])
        report = (await Runner.run(writer, f"Query: {query}\nSearch summaries: {results}")
                  ).final_output_as(FinancialReportData)
        # 4) verify
        verification = (await Runner.run(verifier_agent, report.markdown_report)
                        ).final_output_as(VerificationResult)

    print("\n===== REPORT =====\n", report.markdown_report)
    print("\n===== VERIFICATION =====\n", verification)

    # +++ OpenWright: emit the signed, control-mapped evidence pack
    openwright.get_runtime().report(out_dir="out", scope_description="Financial research agent")
    print("\n[OpenWright] signed evidence pack written to ./out (verify: "
          "openwright verify out/report.json --pubkey out/public_key.pem --deep)")


if __name__ == "__main__":
    asyncio.run(main())
