from app.agents.registry.agent_registry import AgentRegistry
from app.agents.workflows.native_langgraph_collaboration import NativeLangGraphCollaborationWorkflow
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
        from langgraph.graph import END, StateGraph
        def make_node(agent_name):
            def node(data):
                model=AgentWorkflowState.model_validate(data['state']); model=self.registry.get(agent_name).run(model); return {'state':model.model_dump()}
            return node
        workflow=StateGraph(dict)
        for agent_name in state.route_plan: workflow.add_node(agent_name, make_node(agent_name))
        for idx,agent_name in enumerate(state.route_plan):
            if idx==0: workflow.set_entry_point(agent_name)
            workflow.add_edge(agent_name, state.route_plan[idx+1] if idx < len(state.route_plan)-1 else END)
        out=workflow.compile().invoke({'state':state.model_dump()})
        return AgentWorkflowState.model_validate(out['state'])
