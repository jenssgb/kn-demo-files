"""End-to-end smoke test: send one query to the Lane Risk Sentinel agent."""

import argparse
import sys
import time

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-endpoint", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument(
        "--prompt",
        default="Lane SHA -> HAM via CMA is blocked (port congestion). "
                "Calculate the best reroute and return the recommendation.",
    )
    args = parser.parse_args()

    client = AgentsClient(
        endpoint=args.project_endpoint, credential=DefaultAzureCredential(),
    )

    thread = client.threads.create()
    print(f"Thread: {thread.id}")
    client.messages.create(
        thread_id=thread.id, role="user", content=args.prompt,
    )

    run = client.runs.create(thread_id=thread.id, agent_id=args.agent_id)
    print(f"Run:    {run.id}  status={run.status}")
    while run.status in ("queued", "in_progress", "requires_action"):
        time.sleep(2)
        run = client.runs.get(thread_id=thread.id, run_id=run.id)
        print(f"        status={run.status}")

    if run.status != "completed":
        print(f"FAILED: {run.status} / {run.last_error}", file=sys.stderr)
        return 2

    msgs = list(client.messages.list(thread_id=thread.id))
    for m in msgs:
        if m.role != "assistant":
            continue
        print("\n=== ASSISTANT ===")
        for block in m.content:
            if hasattr(block, "text") and block.text:
                print(block.text.value)
        break

    # Show tool calls from the run steps
    steps = list(client.run_steps.list(thread_id=thread.id, run_id=run.id))
    print("\n=== RUN STEPS ===")
    for s in steps:
        details = s.step_details
        if details.type == "tool_calls":
            for tc in details.tool_calls:
                print(f"  tool: {tc.type}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
