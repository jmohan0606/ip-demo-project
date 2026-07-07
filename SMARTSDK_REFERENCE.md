# SmartSDK Reference — confirmed working code from client environment (JPMC)

Transcribed verbatim from screenshots of the client's SmartSDK documentation and a
known-working example. This is the authoritative reference for building the Azure OpenAI
adapters and the LangGraph→SmartSDK swap. DO NOT invent signatures — match these exactly.
NOTE: real api_key / secret values below are placeholders or examples — never commit real ones;
load from .env.

---

## 1. Azure OpenAI Model — CONFIRMED WORKING (key/fusion-based auth) — PRIMARY

This exact pattern was confirmed working by the developer for local runs against the client's
Azure OpenAI. Use this as the primary AzureOpenAILLMClient implementation.

```python
from smart_sdk.models import Model, ModelProvider

model = Model(
    name="gpt-4o-2024-08-06",
    provider=ModelProvider.AZURE_OPENAI,
    azure_deployment_name="gpt-4o-2024-08-06",
    api_key="<from env AZURE_API_KEY>",            # "Same as OpenAI Tenant Ids" in their console
    azure_api_version="2024-02-01",
    azure_endpoint="https://llm-multitenancy-exp.jpmchase.net/ver2",  # Optional: defaults to fusion_base_url if unset
    fusion_base_url="https://llm-multitenancy-exp.jpmchase.net",       # "URL" in their console (remove /ver2 suffix in prod)
    fusion_workspace_id="906313",                  # App Developer workspaces only
    fusion_env="prod",                             # Derived from Fusion URL (e.g. "prod" for https://ifusion.prod.aws.jpmchase.net/fusion)
)
```

## 2. Azure OpenAI Model — certificate-based auth (ALTERNATE) — from architecture doc

The SmartSDK docs also show a certificate-based auth variant. Support this as an alternate auth
path selectable by env, in case the client deployment requires certificate auth rather than the
key/fusion path above.

```python
from smart_sdk.models import Model, ModelProvider, AuthMethod

model = Model(
    name="gpt-4o-mini-2024-07-18",
    auth_method=AuthMethod.CERTIFICATE,
    provider=ModelProvider.AZURE_OPENAI,
    azure_endpoint="https://llm-multitenancy-exp.jpmchase.net/ver2/",
    azure_api_version="2024-10-21",
    azure_deployment_name="gpt-4o-mini-2024-07-18",
    certificate_path="..\\..\\agentbuilder.pem",   # from env
    api_key="<from env>",
    tenant_id="<from env>",
    client_id="<from env>",
)
```

## 3. Converting a Model to a LangGraph-usable LLM

```python
from smart_sdk.ext.langgraph.models._models import _to_langgraph_model

llm = _to_langgraph_model(model)
# llm then supports the LangGraph patterns already used in this codebase:
#   llm.invoke(state.messages)
#   llm.bind_tools(tools=[...], parallel_tool_calls=False)
#   await llm_with_tools.ainvoke(state.messages)
```

The Embedding adapter uses the SAME Model(...) construction pattern (provider=AZURE_OPENAI) but
for the embedding deployment name. Embedding output dimension differs from sentence-transformers
(384) — e.g. text-embedding-3-small = 1536 — so make dimension a config value and keep the
TigerGraph EMBEDDING attribute DDL + Chroma collection consistent with it.

---

## 4. LangGraph → SmartSDK import remapping (CONFIRMED from docs)

SmartSDK re-exports LangGraph symbols; per the docs "there is no need to import from langgraph
directly." Native graph-building signatures are UNCHANGED — only import paths change.

```python
# Native LangGraph  ->  SmartSDK
from smart_sdk.ext.langgraph.graph.state import StateGraph
from smart_sdk.ext.langgraph import (
    ToolNode, InMemorySaver, BaseState, HumanMessage,
    END, CompiledStateGraph, Checkpointer, Command,
    StreamWriter, interrupt, BaseStore, CheckpointMetadata,
    ErrorCode, create_error_message,
)
from smart_sdk.ext.langgraph.adapter._adapter import LangGraphAgent
```

Graph construction is identical to native LangGraph (confirmed from docs):
```python
state_graph = StateGraph(state_schema=MyState)
state_graph.add_node("node_name", node_fn)
state_graph.add_node("tool_node", ToolNode(tools=get_tool, name="tool_name"))  # NOTE: core= is DEPRECATED, use tools=
state_graph.set_entry_point("node_name")
state_graph.add_conditional_edges(source="node_name", path=select_path_fn)
state_graph.add_edge("a", "b")
state_graph.set_finish_point("final_node")
compiled_state_graph = state_graph.compile(checkpointer=InMemorySaver())

agent = LangGraphAgent(
    name="FinTechAgent",
    description="...",
    core=compiled_state_graph,   # LangGraphAgent injects a CompiledGraph
)
```

## 5. Runner — how a compiled graph is executed

```python
from smart_sdk.runners.local_runner import Runner

runner = Runner(app_name="test_app", session_id="test_session")
asyncio.run(Runner.Console(runner.run_async(user_id="test_user", new_message="...")))
```

## 6. TelemetryService / EvaluationService (available — maps to Observability & Eval posters)

```python
from smart_sdk.telemetry import TelemetryService, AuthType
from smart_sdk.evals import EvaluationService

telemetry_service = TelemetryService(
    seal_id="<from env>",
    application_name="<app name>",
    instrumentors=["langchain"],            # required for LangGraph tracing
    genai_gw_phoenix_url="https://ai-gateway.<...>.dev.aws.jpmchase.net/observability/v1/traces",
    auth=AuthType.ID_ANYWHERE_HUMAN_KERBEROS_AUTH,
    auth_kwargs={ "client_id": "...", "resource": "...", "ida_url": "...", "redirect_uri": "..." },
)
eval_service = EvaluationService(
    evaluation_input={ "toxicity": None, "qa_correctness": {...}, "hallucination": {...} },
    model=model,
)
runner = Runner(app_name="...", session_id="...", telemetry_service=telemetry_service, evaluation_service=eval_service)
```

## 7. TigerGraph secret creation (CONFIRMED — developer has admin access)

```gsql
CREATE SECRET iperform_insights_coaching_demo
# returns e.g.: The secret: <SECRET_STRING> has been created for user "R757680".
# Save it — TigerGraph cannot restore it. Put it in .env as TG_SECRET (never commit).
```

## 8. Client artifactory (CONFIRMED — uv.toml)

```toml
[[index]]
url = "https://artifacts-read.gkp.jpmchase.net/artifactory/api/pypi/pypi/simple"
default = true
```

## 9. Confirmed client TigerGraph connection facts

- Host: https://wh-110ecdf498.svr.us.jpmchase.net  (GraphStudio/REST on :14240)
- Version: TigerGraph 4.2.2 (supports GDS, native EMBEDDING/vector attrs, pyTigerGraph[gds] GraphSAGE)
- User: R757680
- Graph name to use: iperform_insights_coaching_demo
- Auth: getToken(secret) using the TG_SECRET created above; SSL enabled.
