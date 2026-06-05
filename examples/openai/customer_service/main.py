"""
Airline customer-service agent (OpenAI Agents SDK) — WITH OpenWright evidence.

Based on the official example:
  https://github.com/openai/openai-agents-python/blob/main/examples/customer_service/main.py
This is a self-contained, runnable version (no repo-internal imports) with the
OpenWright integration applied. The OpenWright delta is just the three lines marked
"+++ OpenWright" below — the agents, tools, handoffs, and Runner.run call are otherwise
the standard customer-service agent.

Run:
  pip install openwright-core openwright-openai-agents openai-agents
  export OPENAI_API_KEY=sk-...
  export OPENWRIGHT_CHECKPOINT_STORE="s3://your-bucket/checkpoints?lock=COMPLIANCE&days=180"  # or file://./out/cp
  python main.py        # interactive; or pipe input / run non-interactively for a scripted seat change
"""

from __future__ import annotations

import asyncio
import random
import sys
import uuid

from pydantic import BaseModel

from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    handoff,
    trace,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

import openwright  # +++ OpenWright


class AirlineAgentContext(BaseModel):
    passenger_name: str | None = None
    confirmation_number: str | None = None
    seat_number: str | None = None
    flight_number: str | None = None


@function_tool(
    name_override="faq_lookup_tool", description_override="Lookup frequently asked questions."
)
async def faq_lookup_tool(question: str) -> str:
    q = question.lower()
    if any(k in q for k in ["bag", "baggage", "luggage", "carry-on"]):
        return "You are allowed one carry-on under 50 lbs and 22 x 14 x 9 inches."
    if any(k in q for k in ["seat", "seats", "plane"]):
        return "120 seats: 22 business, 98 economy. Exit rows 4 and 16; rows 5-8 are Economy Plus."
    if any(k in q for k in ["wifi", "internet", "wireless"]):
        return "We have free wifi on the plane; join Airline-Wifi."
    return "I'm sorry, I don't know the answer to that question."


@function_tool
async def update_seat(
    context: RunContextWrapper[AirlineAgentContext], confirmation_number: str, new_seat: str
) -> str:
    """Update the seat for a given confirmation number."""
    context.context.confirmation_number = confirmation_number
    context.context.seat_number = new_seat
    assert context.context.flight_number is not None, "Flight number is required"
    return f"Updated seat to {new_seat} for confirmation number {confirmation_number}"


async def on_seat_booking_handoff(context: RunContextWrapper[AirlineAgentContext]) -> None:
    context.context.flight_number = f"FLT-{random.randint(100, 999)}"


faq_agent = Agent[AirlineAgentContext](
    name="FAQ Agent",
    handoff_description="A helpful agent that can answer questions about the airline.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an FAQ agent. Use the faq lookup tool to answer the customer's question; do not
    rely on your own knowledge. If you can't answer, transfer back to the triage agent.""",
    tools=[faq_lookup_tool],
)

seat_booking_agent = Agent[AirlineAgentContext](
    name="Seat Booking Agent",
    handoff_description="A helpful agent that can update a seat on a flight.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a seat booking agent. Ask for the confirmation number and the desired seat, then
    use the update seat tool. For unrelated questions, transfer back to the triage agent.""",
    tools=[update_seat],
)

triage_agent = Agent[AirlineAgentContext](
    name="Triage Agent",
    handoff_description="A triage agent that delegates a customer's request to the right agent.",
    instructions=f"{RECOMMENDED_PROMPT_PREFIX} You are a helpful triaging agent. Delegate to the "
    "appropriate agent using your tools.",
    handoffs=[
        handoff(agent=faq_agent, tool_name_override="transfer_to_faq_agent"),
        handoff(agent=seat_booking_agent, on_handoff=on_seat_booking_handoff,
                tool_name_override="transfer_to_seat_booking_agent"),
    ],
)
faq_agent.handoffs.append(handoff(agent=triage_agent, tool_name_override="transfer_to_triage_agent"))
seat_booking_agent.handoffs.append(handoff(agent=triage_agent, tool_name_override="transfer_to_triage_agent"))

# +++ OpenWright: one line — capture every tool call/handoff as signed, tamper-evident
# evidence; treat `update_seat` as an attested decision. Ledger + signing key + WORM S3
# checkpoint come from env (OPENWRIGHT_CHECKPOINT_STORE=…); checkpointing is automatic.
openwright.instrument("openai-agents", decision_tools=["update_seat"])


# When run non-interactively, replay this scripted seat-change conversation.
_SCRIPT = ["I'd like to change my seat", "My confirmation number is ABC123", "Seat 14C please"]


async def main() -> None:
    current_agent: Agent[AirlineAgentContext] = triage_agent
    input_items: list[TResponseInputItem] = []
    context = AirlineAgentContext()
    conversation_id = uuid.uuid4().hex[:16]
    interactive = sys.stdin.isatty()
    script = iter(_SCRIPT)

    while True:
        if interactive:
            try:
                user_input = input("Enter your message ('exit' to finish): ").strip()
            except EOFError:
                break
            if not user_input or user_input.lower() == "exit":
                break
        else:
            user_input = next(script, None)
            if user_input is None:
                break
            print(f"> {user_input}")

        with trace("Customer service", group_id=conversation_id):
            input_items.append({"content": user_input, "role": "user"})
            result = await Runner.run(current_agent, input_items, context=context)
            for item in result.new_items:
                name = item.agent.name
                if isinstance(item, MessageOutputItem):
                    print(f"{name}: {ItemHelpers.text_message_output(item)}")
                elif isinstance(item, HandoffOutputItem):
                    print(f"Handed off from {item.source_agent.name} to {item.target_agent.name}")
                elif isinstance(item, ToolCallItem):
                    print(f"{name}: calling a tool")
                elif isinstance(item, ToolCallOutputItem):
                    print(f"{name}: tool output: {item.output}")
            input_items = result.to_input_list()
            current_agent = result.last_agent

    # +++ OpenWright: emit the signed, control-mapped evidence pack
    openwright.get_runtime().report(out_dir="out", scope_description="Airline customer-service agent")
    print("\n[OpenWright] signed evidence pack written to ./out (verify: "
          "openwright verify out/report.json --pubkey out/public_key.pem --deep)")


if __name__ == "__main__":
    asyncio.run(main())
