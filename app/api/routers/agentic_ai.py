from fastapi import APIRouter
from app.agents.state.agent_state import AgenticRequest
from app.services.agentic_ai_service import AgenticAiService
from app.shared.responses import ok
router=APIRouter(prefix='/agentic-ai', tags=['True Agentic AI'])
@router.get('/agents')
def agents(): return ok(data=AgenticAiService().list_agents())
@router.get('/topology')
def topology():
    """Real agent-system graph: registry agents + supervisor routing rules + actual tool/data-source dependencies."""
    from app.agents.registry.topology import build_topology
    return ok(data=build_topology())
@router.post('/run')
def run_agentic_workflow(request:AgenticRequest): return ok(data=AgenticAiService().run(request).model_dump())
