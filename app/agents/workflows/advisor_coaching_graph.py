from app.agents.registry.agent_registry import AgentRegistry
from app.agents.state.agent_state import AgentWorkflowState
class AdvisorCoachingAgentGraph:
    def __init__(self): self.registry=AgentRegistry()
    def run(self,state:AgentWorkflowState)->AgentWorkflowState:
        state=self.registry.get('supervisor').run(state)
        try: return self._run_langgraph(state)
        except Exception as exc:
            state.reasoning_steps.append(f'LangGraph runtime fallback used: {exc}')
            return self._run_sequential(state)
    def _run_sequential(self,state):
        for agent_name in state.route_plan:
            if agent_name!='supervisor': state=self.registry.get(agent_name).run(state)
        return state
    def _run_langgraph(self,state):
        # All native-LangGraph construction lives in langgraph_builder (isolated for the SmartSDK
        # swap on the client machine — see that module's docstring). Nothing langgraph-specific
        # is imported here.
        from app.agents.workflows.langgraph_builder import build_and_run_linear_graph
        def make_node(agent_name):
            def node(data):
                model=AgentWorkflowState.model_validate(data['state']); model=self.registry.get(agent_name).run(model); return {'state':model.model_dump()}
            return node
        out=build_and_run_linear_graph(state.route_plan, make_node, {'state':state.model_dump()})
        return AgentWorkflowState.model_validate(out['state'])
