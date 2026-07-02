from app.agents.core.base_agent import BaseAgent
from app.agents.state.agent_state import AgentEvidence
from app.agents.tools.service_tools import AgentToolbox
class RagKnowledgeAgent(BaseAgent):
    name='rag_knowledge_agent'; description='Retrieves Chroma/RAG document context.'
    def __init__(self): self.tools=AgentToolbox()
    def run(self,state):
        task=self.create_task('Search knowledge')
        try:
            search=self.tools.search_knowledge(state.request.question); state.context['knowledge']=search
            for item in search.get('results',[])[:5]: state.evidence.append(AgentEvidence(source='Knowledge RAG',title=item.get('document_name','Document'),content=item.get('chunk_text',''),score=item.get('score'),metadata=item))
            state.reasoning_steps.append('RAG Knowledge Agent retrieved document evidence.'); state.tasks.append(self.complete_task(task, {'results': len(search.get('results',[]))}))
        except Exception as e: state.errors.append('RAG unavailable: '+str(e)); state.tasks.append(self.fail_task(task,e))
        return state
