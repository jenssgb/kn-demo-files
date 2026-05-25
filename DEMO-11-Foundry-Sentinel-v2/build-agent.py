"""
Create / update the 'Lane Risk Sentinel' agent in the Foundry project
using the Azure AI Agents SDK.

Tools wired:
  - FileSearchTool over the kn-sentinel-corpus vector store
  - OpenApiTool over reroute_function/openapi.yaml (anonymous auth)

Usage:
    python build-agent.py \
        --project-endpoint "https://ai-knfdry-e7c20f.services.ai.azure.com/api/projects/kn-lane-risk-sentinel" \
        --vector-store-id "vs_GlI50oT3VEC3qL03BPXlyv0G"
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    FileSearchTool,
    OpenApiAnonymousAuthDetails,
    OpenApiTool,
)

HERE = Path(__file__).parent
INSTRUCTIONS_FILE = HERE / "Lane-Risk-Sentinel-Foundry-Instructions.md"
OPENAPI_FILE = HERE / "reroute_function" / "openapi.yaml"
AGENT_NAME = "Lane Risk Sentinel"
MODEL = "gpt-4.1-mini"


def load_instructions() -> str:
    text = INSTRUCTIONS_FILE.read_text(encoding="utf-8")
    text = re.sub(r"^>.*\n", "", text, flags=re.MULTILINE)
    return text.strip()


def load_openapi_spec() -> dict:
    with OPENAPI_FILE.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-endpoint", required=True)
    parser.add_argument("--vector-store-id", required=True)
    args = parser.parse_args()

    agents = AgentsClient(
        endpoint=args.project_endpoint,
        credential=DefaultAzureCredential(),
    )

    instructions = load_instructions()
    spec = load_openapi_spec()

    file_search = FileSearchTool(vector_store_ids=[args.vector_store_id])
    backend = OpenApiTool(
        name="sentinel_backend",
        description=(
            "KN Lane Risk Sentinel backend. Four operations: "
            "calculate_reroute (compute), send_approval_email (ACTION via Graph), "
            "create_planner_task (ACTION via Graph), log_decision_sharepoint "
            "(ACTION via Graph). Action operations only when operator explicitly asks."
        ),
        spec=spec,
        auth=OpenApiAnonymousAuthDetails(),
    )

    tools = file_search.definitions + backend.definitions
    tool_resources = file_search.resources

    # Find existing agent by name -> update; else create.
    existing = None
    for a in agents.list_agents():
        if a.name == AGENT_NAME:
            existing = a
            break

    common = dict(
        name=AGENT_NAME,
        model=MODEL,
        instructions=instructions,
        tools=tools,
        tool_resources=tool_resources,
        metadata={"owner": "kn-executive-ai-showcase"},
    )

    if existing:
        print(f"Updating existing agent: {existing.id}")
        agent = agents.update_agent(agent_id=existing.id, **common)
    else:
        print("Creating new agent ...")
        agent = agents.create_agent(**common)

    print("\nDONE")
    print(f"  Agent ID    : {agent.id}")
    print(f"  Name        : {agent.name}")
    print(f"  Model       : {agent.model}")
    print(f"  Tools       : {[t.type for t in agent.tools]}")
    print(f"  Vector store: {args.vector_store_id}")
    print("\nNEXT:")
    print("  1. Open Foundry portal -> Agents -> Lane Risk Sentinel -> Playground")
    print("  2. Test: 'Reroute SHA->HAM via CMA, current lane blocked'")
    print("  3. Publish to Microsoft 365 Copilot (Just-you scope)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
