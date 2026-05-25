"""
Build the Sentinel vector store for the KN Lane Risk Sentinel agent.

Uses AIProjectClient -> OpenAI client scoped to the project, creates a
named vector store and uploads the Sentinel corpus.

Usage:
    python build-vector-store.py --project-endpoint "https://<acc>.services.ai.azure.com/api/projects/<project>"
"""

import argparse
import sys
import time
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

SENTINEL_DIR = Path(__file__).parent.parent / "Sentinel"
FILES = [
    "ContosoShipments.csv",
    "Alternate-Lane-Capacity.csv",
    "KN-Lane-Risk-Playbook.md",
]
VECTOR_STORE_NAME = "kn-sentinel-corpus"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-endpoint", required=True)
    args = parser.parse_args()

    project = AIProjectClient(
        endpoint=args.project_endpoint,
        credential=DefaultAzureCredential(),
    )
    openai = project.get_openai_client()

    file_ids: list[str] = []
    for name in FILES:
        path = SENTINEL_DIR / name
        if not path.exists():
            print(f"  SKIP (not found): {path}")
            continue
        print(f"  Uploading {name} ...", flush=True)
        # File Search rejects .csv, upload as .txt instead.
        upload_name = name.replace(".csv", ".txt")
        with path.open("rb") as fh:
            uploaded = openai.files.create(
                file=(upload_name, fh.read()), purpose="assistants",
            )
        file_ids.append(uploaded.id)
        print(f"    -> file_id={uploaded.id}")

    if not file_ids:
        print("ERROR: no files uploaded.", file=sys.stderr)
        return 2

    print(f"\nCreating vector store '{VECTOR_STORE_NAME}' "
          f"with {len(file_ids)} files ...")
    vs = openai.vector_stores.create(
        name=VECTOR_STORE_NAME, file_ids=file_ids,
    )
    while vs.status == "in_progress":
        time.sleep(2)
        vs = openai.vector_stores.retrieve(vs.id)

    print("\nDONE")
    print(f"  Vector store ID: {vs.id}")
    print(f"  Name           : {vs.name}")
    print(f"  Status         : {vs.status}")
    print(f"  File counts    : {vs.file_counts}")
    print("\nNEXT: In Foundry portal -> Agent -> Knowledge -> File Search "
          f"-> select '{vs.name}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
