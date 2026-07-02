# Prerequisites

## Required Local Tools

- Python 3.11+
- UV package manager
- Git or unzip utility
- Terminal / command prompt
- Browser for Streamlit and FastAPI docs

## Optional External Services

- Existing TigerGraph MCP server
- TigerGraph 4.2.2 running in AWS
- OpenAI-compatible API key

## Local Components Used

- FastAPI
- Streamlit
- SQLite
- Chroma
- NetworkX
- scikit-learn
- Mock model fallback
- Mock graph fallback

## Verify Python

```bash
python --version
```

## Install UV

Mac/Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
