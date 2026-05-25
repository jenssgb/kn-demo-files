# DEMO-11 · Build Guide — Lane Risk Sentinel v2 in Microsoft Foundry

> Companion to the KN Executive AI Showcase briefing.
> Estimated build time: **~3 hours** (Function deploy ~45 min, Foundry agent ~30 min, data prep ~15 min, dry-run ~1.5 h).
> Run this BEFORE the session, not on stage.

## ✅ Live deployment in CDX (status: ready to run)

The end-to-end build is **provisioned and tested** in CDX tenant
`M365CPI98544940.onmicrosoft.com` (Switzerland North). All resource IDs:

| Layer | Resource |
|---|---|
| Resource Group | `rg-kn-foundry-demo` |
| Storage | `stknfdrye7c20f` (identity-only auth — Shared Key disabled by CDX policy) |
| Function App | `func-knfdry-e7c20f` (Flex Consumption, Linux Python 3.11, SystemAssignedIdentity) |
| Function URL | `https://func-knfdry-e7c20f.azurewebsites.net/api/calculate_reroute` (AuthLevel **ANONYMOUS**) |
| Foundry (AIServices) | `ai-knfdry-e7c20f` |
| Project | `kn-lane-risk-sentinel` |
| Project endpoint | `https://ai-knfdry-e7c20f.services.ai.azure.com/api/projects/kn-lane-risk-sentinel` |
| Model deployments | `gpt-5-mini` (chat) · `gpt-4.1-mini` (agent — supports OpenAPI tool) |
| Vector Store | `kn-sentinel-corpus` → `vs_GlI50oT3VEC3qL03BPXlyv0G` (3 files) |
| Agent | `Lane Risk Sentinel` → `asst_gA18S1uWgG8xuIIGa9ri5Fbi` |

### To reproduce from scratch

```powershell
# 1. Provision Azure infra (resource group, storage, Function, Foundry, model deployments)
.\prep-foundry.ps1      # currently captures the manual steps used; idempotent rewrite TBD

# 2. Build the Sentinel vector store
python .\build-vector-store.py `
    --project-endpoint "https://ai-knfdry-e7c20f.services.ai.azure.com/api/projects/kn-lane-risk-sentinel"

# 3. Create / update the agent (wires file_search + openapi tool)
python .\build-agent.py `
    --project-endpoint "https://ai-knfdry-e7c20f.services.ai.azure.com/api/projects/kn-lane-risk-sentinel" `
    --vector-store-id  "vs_GlI50oT3VEC3qL03BPXlyv0G"

# 4. Smoke-test end-to-end
python .\test-agent.py `
    --project-endpoint "https://ai-knfdry-e7c20f.services.ai.azure.com/api/projects/kn-lane-risk-sentinel" `
    --agent-id         "asst_gA18S1uWgG8xuIIGa9ri5Fbi"
```

### Deployment-time gotchas (real ones we hit in CDX)

- **CDX Azure Policy silently sets `allowSharedKeyAccess: false`** on every
  storage account. Y1 Consumption Function Apps can't run under that policy
  (file-share 403). **Fix:** Flex Consumption +
  `--deployment-storage-auth-type SystemAssignedIdentity`.
- **`az functionapp keys list` returns 400** on Flex + MI deployments.
  **Fix:** function set to `AuthLevel.ANONYMOUS` (acceptable: internal demo
  surface, no PII, called only by Foundry).
- **`gpt-5-mini` cannot be used with `OpenApiTool`** (only Responses API
  tools). **Fix:** deploy `gpt-4.1-mini` alongside and use it for the agent.
  `gpt-5-mini` stays available for plain chat / Playground demos.
- **CSV files rejected by File Search.** Build script renames `.csv` to
  `.txt` on upload — content is unchanged.
- **`azure-ai-projects` 2.1.0 is a lean SDK** — agents/files/vector-stores
  live on `AgentsClient` (`azure-ai-agents`) or the OpenAI client from
  `project.get_openai_client()`. Don't use `project.agents` for runtime
  operations — that is the versioned-manifest surface.

---

## Why this exists

In **DEMO-08** we showed the Lane Risk Sentinel as a Copilot Studio agent — low-code, business-user-buildable.
In **DEMO-11** we rebuild the *same* operational pattern in **Microsoft Foundry** to answer the question every VP-IT/Engineering executive will ask:

> *"OK, that low-code agent is great for business users. But how do my developers build a differentiating agent on the same data, in our Azure tenant, that we own end-to-end?"*

Same story, same data, different audience. The build path goes:

1. **Custom function tool** (Azure Function, Python) — `calculate_reroute`
2. **Prompt Agent** in Foundry portal — model + instructions + 3 tools
3. **Live chat** in the Foundry Playground — show RAG + web + custom function in one turn
4. **Tracing** — show every model call, tool call, latency, token cost
5. **Publish to Teams** — single click, the Sentinel v2 ships into the demo user's Teams

## Prerequisites

- CDX tenant with an Azure subscription where you have `Contributor` + `User Access Administrator`
- Microsoft Foundry resource provisioned in **West Europe** or **Switzerland North** (matters for the KN data-residency talking point)
- A model deployment of **gpt-5-mini** (Foundry direct, GA) in the same project
- Azure Functions Core Tools v4 installed locally for the function deploy
- The Sentinel demo files from DEMO-08 already exist at `Demo-Files/Sentinel/` (we reuse the corpus for File Search)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Microsoft Foundry (Switzerland North)             │
│                                                                     │
│   ┌────────────────────┐         ┌──────────────────────────────┐   │
│   │ Prompt Agent       │         │ File Search Index            │   │
│   │ "Lane Risk Sentinel│ ──┐    │  ContosoShipments.csv        │   │
│   │  v2"               │   ├──> │  Alternate-Lane-Capacity.csv │   │
│   │ Model: gpt-5-mini  │   │    │  KN-Lane-Risk-Playbook.md    │   │
│   └────────────────────┘   │    └──────────────────────────────┘   │
│            │               │                                        │
│            │               ├──> Web Search (Bing grounding)         │
│            │               │                                        │
│            │               └──> Custom Function tool ───────┐       │
│   ┌────────────────────┐                                    │       │
│   │ Tracing / Eval     │                                    │       │
│   │ (App Insights)     │                                    │       │
│   └────────────────────┘                                    │       │
└─────────────────────────────────────────────────────────────┼───────┘
                                                              │
              ┌───────────────────────────────────────────────┘
              ▼
    ┌─────────────────────────────────┐
    │ Azure Function (Linux Y1)        │
    │ kn-reroute-fn.azurewebsites.net  │
    │ Python 3.11 · Functions v4       │
    │ POST /api/calculate_reroute      │
    └─────────────────────────────────┘
```

## Step 1 — Deploy the custom function tool (~45 min)

The Azure Function returns deterministic reroute scores. The demo always reproduces, but the call/response pattern is realistic.

```powershell
# from repo root
cd Kunden/Kuehne-Nagel/demos/2026-05-Executive-AI-Showcase/Demo-Files/Foundry/reroute_function

# one-time: pick a unique global name
$rg = "rg-kn-foundry-demo"
$loc = "switzerlandnorth"
$fnName = "kn-reroute-fn-$(Get-Random -Maximum 9999)"
$storage = ("knfn" + (Get-Random -Maximum 99999)).ToLower()

az group create --name $rg --location $loc
az storage account create --name $storage --resource-group $rg --location $loc --sku Standard_LRS
az functionapp create `
    --resource-group $rg `
    --consumption-plan-location $loc `
    --runtime python --runtime-version 3.11 --functions-version 4 `
    --name $fnName `
    --storage-account $storage `
    --os-type Linux

func azure functionapp publish $fnName --python

# capture the function key for Foundry tool config
$key = az functionapp keys list --name $fnName --resource-group $rg `
    --query "functionKeys.default" -o tsv
"Endpoint: https://$fnName.azurewebsites.net/api/calculate_reroute?code=$key"
```

**Smoke test:**

```powershell
$body = @{
  origin = "SHA"
  destination = "HAM"
  current_carrier = "CMA"
  candidate_carriers = @("HMM", "MSK", "ONE")
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "https://$fnName.azurewebsites.net/api/calculate_reroute?code=$key" `
    -ContentType "application/json" -Body $body
```

Expected: JSON with `recommended.carrier = "HMM"` and `risk_reduction_score > 0`.

## Step 2 — Create the Foundry project + model deployment (~10 min)

1. Open <https://ai.azure.com/>
2. **Create project** → name: `KN-LaneRisk-Sentinel-v2`, region: **Switzerland North**
3. **Models + endpoints** → **Deploy model** → search `gpt-5-mini` → **Deploy** (default capacity)
4. Note the project endpoint URL (looks like `https://<resource>.ai.azure.com/api/projects/KN-LaneRisk-Sentinel-v2`)

## Step 3 — Build the File Search index (~10 min)

1. In your Foundry project → **Data + indexes** → **+ New index**
2. Name: `kn-sentinel-corpus`, embedding model: `text-embedding-3-large`
3. Upload these files from `Demo-Files/Sentinel/`:
   - `ContosoShipments.csv`
   - `Alternate-Lane-Capacity.csv`
   - `KN-Lane-Risk-Playbook.md`
   - `Sentinel-Agent-Instructions.md` *(for cross-reference)*
4. Wait for indexing to finish (~2 min)

## Step 4 — Create the Prompt Agent (~15 min)

1. In your project → **Agents** → **+ New agent** → **Prompt agent**
2. Name: `Lane-Risk-Sentinel-v2`, model: `gpt-5-mini`
3. **Instructions:** paste the contents of [`Lane-Risk-Sentinel-Foundry-Instructions.md`](./Lane-Risk-Sentinel-Foundry-Instructions.md)
4. **Tools** → add three:
   - **File Search** → select index `kn-sentinel-corpus`
   - **Web Search** → enable (Bing grounding)
   - **Custom Function** → **+ Add** → **From OpenAPI**:
     - Upload [`reroute_function/openapi.yaml`](./reroute_function/openapi.yaml)
     - Auth: **API Key** → header `x-functions-key` → value: the function key from Step 1
     - Patch the `servers[0].url` to your actual function URL
5. **Save** → the agent is versioned automatically (v1)

## Step 5 — Dry-run in the Playground (~30 min)

Open the agent in the Playground. Run these three prompts in order, screenshot each, save for the briefing.

**Prompt A (RAG only — proves File Search works):**

```
What is the current risk classification methodology for Contoso reefer
shipments? Quote the section from the playbook and explain it in 3 bullets.
```

Expect: cites `KN-Lane-Risk-Playbook.md`, returns the 5-factor model.

**Prompt B (Web + RAG — proves the agent fuses sources):**

```
Shipment CMA-2847 is on the Shanghai-Hamburg lane with CMA-CGM. Are there
any current disruptions on this lane that I should know about? Use the
playbook to classify the risk.
```

Expect: web search for Typhoon Mawar / Port of Shanghai congestion / Suez status (depending on what's live), then risk score using the playbook framework.

**Prompt C (full chain — proves the custom function fires):**

```
For shipment CMA-2847 (Shanghai-Hamburg, current carrier CMA-CGM), if the
risk is HIGH, find me the best alternate carrier from HMM, Maersk and ONE.
Give me ETA delta, cost delta and the Adaptive Card I should send to the
account owner.
```

Expect: calls `calculate_reroute`, recommends **HMM** (`carrier=HMM`, `risk_reduction_score > 10`), emits the Adaptive Card JSON.

## Step 6 — Show observability (~10 min)

1. In the Playground after Prompt C → click **View trace** (top-right)
2. The trace shows every step: model call → file_search call → web_search call → calculate_reroute call → model call. Latency + tokens per step.
3. **Project → Observability → Application Insights:** open the linked AI workspace, show the agent's invocations as a time series. This is what closes the EU AI Act conversation from DEMO-09 — *"every Annex IV requirement on logging and traceability ships in the box."*

## Step 7 — Publish to Teams (~5 min, optional but recommended)

1. Agent page → **Publish** → **Microsoft 365 Copilot + Teams**
2. Foundry generates the agent manifest, registers in the **Entra Agent Registry**, and produces an install link
3. On the demo VM, paste the link in Teams → the Sentinel v2 appears as a chat agent
4. (For the actual stage you do NOT need to publish — just **show the dialog and click Cancel**. The VPs see that one click ships the agent. Don't pollute the M365 sidebar mid-demo.)

## Live demo flow on stage (~6-8 min)

1. **Frame (20 sec):** *"DEMO-08 was Sentinel built in Copilot Studio by your business team. Same data, same problem, now built by your developers in Foundry — your tenant, your model deployment, your code."*
2. **Foundry portal → Models** (15 sec): swipe through the catalog filter (1,900+ models, GPT-5, Claude, Llama, DeepSeek, Phi). *"This is the model menu your team picks from."*
3. **Project → Agents → Lane-Risk-Sentinel-v2** → **Instructions tab**: scroll the system prompt for 5 seconds. *"This is the entire 'code' of a prompt agent. Versioned, role-based access, audit trail."*
4. **Tools tab**: point at the three tools. *"RAG over our playbook, live web for disruption news, a Python function our team wrote that lives as an Azure Function in our subscription."*
5. **Playground**: paste **Prompt C**. Wait ~8-12 seconds. Walk the audience through the streaming reasoning. The Adaptive Card JSON appears.
6. **View trace** (the money shot): expand the trace tree, point at the `calculate_reroute` tool call, show the JSON request/response. *"Every step logged. This is what the regulator means by 'sufficiently transparent AI system' under EU AI Act Annex IV."*
7. **Publish → Teams** dialog: open, point at the buttons, close without publishing. *"One click and this agent is in every Customer Service desk's Teams. Same governance lens as the M365 Copilot agents you saw earlier — because they're all in the same Entra Agent Registry."*
8. **(optional closer)**: open **Operate → Cost** dashboard. *"This entire demo cost about EUR 0.04. Linear cost scaling, no per-seat license, you pay only when you use it."*

## What you should land

- **One platform, three audiences.** Foundry is where developers build agents. Copilot Studio is where citizen developers build them. M365 Copilot is where employees use them. **Same Entra identity, same audit trail, same Content Safety.**
- **Differentiating IP lives here.** Foundry is where KN builds the agents that Maersk and DSV can't copy — because they wrap *KN-proprietary* data, models and functions.
- **Sovereignty story.** Switzerland North region, no data leaves the tenant, custom model deployments. The slot Sabrina cares about for K.AI v3.
- **Built-in compliance.** Tracing, evaluations, content safety, identity per agent, VNet — out of the box. *"What you'd otherwise build over 12 months across 8 vendors."*

## Punchline

> *"DEMO-08 proved a business analyst can build an autonomous agent in a day. DEMO-11 proves your developers can build it in the same day — with deeper customization, your own code, your own model, your own tenant. Pick the right surface for the right team. The platform is the same."*

## Gotchas

- **Region:** Switzerland North is required for the data-sovereignty talking point but has fewer models in catalog than West Europe. If `gpt-5-mini` isn't available at demo time, fall back to `gpt-4.1` (also in catalog, same agent code works).
- **Function cold start:** First call after >20 min idle can take 3-4 seconds. **Pre-warm it 5 min before stage** with the smoke-test PowerShell from Step 1.
- **Web search throttling:** If Bing rate-limits during dry-runs, switch to **File Search only** for Prompt B — drop the disruption-news line.
- **Custom Function auth:** If the OpenAPI import in Foundry rejects the key, fall back to **Custom Function from code** (paste the same `function_app.py` body in the inline editor). Less elegant but identical user experience.
- **Publish to Teams dialog:** If the CDX tenant doesn't have M365 Copilot licensed, the dialog will say "license required" — that's fine for the demo, you don't actually click publish.

## Files in this folder

- [`Lane-Risk-Sentinel-Foundry-Instructions.md`](./Lane-Risk-Sentinel-Foundry-Instructions.md) — paste into the agent Instructions field
- [`reroute_function/function_app.py`](./reroute_function/function_app.py) — Azure Function code
- [`reroute_function/requirements.txt`](./reroute_function/requirements.txt) — Python deps
- [`reroute_function/host.json`](./reroute_function/host.json) — Functions host config
- [`reroute_function/openapi.yaml`](./reroute_function/openapi.yaml) — OpenAPI spec for Foundry tool import

## Sources

- [Microsoft Foundry overview](https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-azure-ai-foundry) (Learn, 05/2026)
- [Foundry Agent Service overview](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/overview) (Learn, 04/2026)
- [Foundry quickstart — build with models and agents](https://learn.microsoft.com/en-us/azure/ai-foundry/quickstarts/get-started-code) (Learn, 03/2026)
- [Foundry Models catalog](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/foundry-models-overview) (Learn, 04/2026)
- [Tool catalog and best practices](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/tool-catalog) (Learn)
- [Publish a Foundry agent to Microsoft 365 / Teams](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/publish-copilot) (Learn)

---

**Status:** assets ready in this folder. CDX deployment is the next step (run Step 1 in your CDX subscription, then Steps 2-7 in the Foundry portal).

---

## Addendum — ACTION tools (v2: send_approval_email, create_planner_task, log_decision_sharepoint)

This addendum captures the *delta* applied 2026-05 to evolve Sentinel from
"recommends" to "decides + writes". Three new endpoints in the same
Function App, all authenticating to Microsoft Graph via the Function's
System-Assigned Managed Identity.

### Graph permissions on the Function MI

The MI principal id is `d4ef76e5-0843-474f-90f7-bad32c6a22de` (read it
from `az functionapp identity show`). Grant app permissions on the Graph
service principal (`15dab2f9-b2a5-4638-99d0-bd99ec01307a`):

| App role | Role id | For |
|---|---|---|
| `Mail.Send` | `b633e1c5-b582-4048-a93e-9f11b44c7e96` | `send_approval_email` |
| `Tasks.ReadWrite.All` | `44e666d1-d276-445b-a5fc-8815eeb81d55` | `create_planner_task` (Planner app-only) |
| `Sites.FullControl.All` | `a82116e5-55eb-4c41-a434-62fe8a61c773` | `log_decision_sharepoint` + bootstrap |

> **Trap we hit:** `Sites.ReadWrite.All` is **not enough** for SharePoint
> list *creation* — Graph returns `403 accessDenied`. Use
> `Sites.FullControl.All` (or `Sites.Manage.All` if scope-narrowing matters).
>
> **Trap we hit:** Planner app-only used to require the MI to be a member
> of the M365 group hosting the plan, but service principals can't be
> added to Unified Groups. The modern fix is the app permission
> `Tasks.ReadWrite.All` (preview, but works tenant-wide).

Grant pattern (uses temp-file because inline `--body` JSON fails with 400):

```powershell
$miOid = "d4ef76e5-0843-474f-90f7-bad32c6a22de"
$graphSp = "15dab2f9-b2a5-4638-99d0-bd99ec01307a"
foreach ($roleId in @(
  "b633e1c5-b582-4048-a93e-9f11b44c7e96",  # Mail.Send
  "44e666d1-d276-445b-a5fc-8815eeb81d55",  # Tasks.ReadWrite.All
  "a82116e5-55eb-4c41-a434-62fe8a61c773"   # Sites.FullControl.All
)) {
  $body = @{ principalId=$miOid; resourceId=$graphSp; appRoleId=$roleId } | ConvertTo-Json -Compress
  $tmp = New-TemporaryFile; Set-Content $tmp $body -Encoding ascii
  az rest --method POST --headers "Content-Type=application/json" `
    --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$miOid/appRoleAssignments" `
    --body "@$($tmp.FullName)" -o none
  Remove-Item $tmp
}
```

### M365 group + Planner plan + bucket (one-time)

```powershell
# 1. Create the M365 group that hosts the Planner plan
#    (do this as admin, not as MI — admin becomes the owner)
$groupBody = @{
  displayName = "KN Reroute Decisions"
  mailNickname = "kn-reroute-decisions"
  description = "Owner of the Sentinel Planner plan + SharePoint site"
  groupTypes = @("Unified")
  mailEnabled = $true
  securityEnabled = $false
  "owners@odata.bind" = @("https://graph.microsoft.com/v1.0/users/<admin-oid>")
  "members@odata.bind" = @("https://graph.microsoft.com/v1.0/users/<admin-oid>")
} | ConvertTo-Json -Compress
# (write to temp + az rest POST /groups — same pattern as above)

# 2. Create a Planner plan owned by that group
#    POST /planner/plans  { owner: <groupId>, title: "KN Reroute Decisions" }

# 3. Create a bucket in that plan
#    POST /planner/buckets { planId: ..., name: "Inbox", orderHint: " !" }
```

Save the IDs:
```
GROUP_ID  = e0931925-1b7b-4c30-b2b9-0ba5862a5c02
PLAN_ID   = 20JAvTM_BkS8IlfaSAQuyGUAFk8C
BUCKET_ID = 7jMNCgvD7UeK3nFP2XZYimUAD3AY
```

### SharePoint site + list (bootstrap via Function)

The site is created by Graph automatically when the M365 group is created
(it lives at `https://<tenant>.sharepoint.com/sites/<mailNickname>`). The
list is created idempotently by the Function's bootstrap endpoint:

```powershell
# After the function code is deployed and GRAPH_SP_SITE app-setting is set:
$r = Invoke-RestMethod -Method POST `
  -Uri "https://func-knfdry-e7c20f.azurewebsites.net/api/_bootstrap_sharepoint_list" `
  -ContentType "application/json" -Body '{}'
$r   # -> { status: "created", list_id: "<guid>", web_url: "..." }

# Wire the list id back into the function app
az functionapp config appsettings set -g rg-kn-foundry-demo -n func-knfdry-e7c20f `
  --settings "GRAPH_SP_LIST=$($r.list_id)" -o none
```

### Required app settings on the Function App

| Setting | Example |
|---|---|
| `GRAPH_MAIL_FROM` | `admin@M365CPI98544940.onmicrosoft.com` |
| `GRAPH_MAIL_TO`   | `admin@M365CPI98544940.onmicrosoft.com` (comma-sep) |
| `GRAPH_PLANNER_PLAN` | `20JAvTM_BkS8IlfaSAQuyGUAFk8C` |
| `GRAPH_PLANNER_BUCKET` | `7jMNCgvD7UeK3nFP2XZYimUAD3AY` |
| `GRAPH_SP_SITE` | `m365cpi98544940.sharepoint.com,<siteId>,<webId>` (the triple from `GET /sites/{host}:{path}`) |
| `GRAPH_SP_LIST` | (from bootstrap step above) |

### Deploy the updated code

`az functionapp deploy --type zip` returns **415** on this Flex Consumption
SKU. Use the legacy command instead — it tunnels through Kudu and works:

```powershell
cd Demo-Files/Foundry/reroute_function
Compress-Archive -Path .\* -DestinationPath "$env:TEMP\reroute_function.zip" -Force
az functionapp deployment source config-zip `
  -g rg-kn-foundry-demo -n func-knfdry-e7c20f `
  --src "$env:TEMP\reroute_function.zip" --build-remote true
```

After the deploy + a 30-60s warm-up, re-run `build-agent.py` so the Foundry
agent picks up the four OpenAPI ops (`calculate_reroute`,
`send_approval_email`, `create_planner_task`, `log_decision_sharepoint`).

### Smoke tests (each is also a viable stage move)

```powershell
$base = "https://func-knfdry-e7c20f.azurewebsites.net/api"
Invoke-RestMethod -Method POST -Uri "$base/send_approval_email"     -ContentType "application/json" -Body '{}'
Invoke-RestMethod -Method POST -Uri "$base/create_planner_task"     -ContentType "application/json" -Body '{}'
Invoke-RestMethod -Method POST -Uri "$base/log_decision_sharepoint" -ContentType "application/json" -Body '{}'
```

All three return a JSON body with a `markdown` receipt the agent surfaces
verbatim, plus the Graph object id (mail not exposed — Graph sendMail
returns 202 with no body).

