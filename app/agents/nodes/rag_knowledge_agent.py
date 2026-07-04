from app.agents.core.base_agent import BaseAgent
from app.agents.state.agent_state import AgentEvidence
from app.agents.tools.service_tools import AgentToolbox


class RagKnowledgeAgent(BaseAgent):
    """Real RAG, not retrieval-only: retrieves semantically-embedded document
    chunks AND generates a grounded, cited answer via the LLMClient adapter
    (RagGenerationService). Honest not-found when nothing clears the
    similarity threshold — no hallucinated answer."""

    name = 'rag_knowledge_agent'
    description = 'Answers from the document knowledge base via retrieval-augmented generation with citations.'

    def __init__(self):
        self.tools = AgentToolbox()

    def run(self, state):
        task = self.create_task('RAG knowledge answer')
        try:
            rag = self.tools.ask_knowledge(state.request.question)
            state.context['knowledge'] = rag
            for i, source in enumerate(rag.get('sources', [])[:5], start=1):
                state.evidence.append(AgentEvidence(
                    source='Knowledge RAG',
                    title=f"[{i}] {source.get('document_name', 'Document')}",
                    content=source.get('excerpt', ''),
                    score=source.get('similarity'),
                    metadata=source,
                ))
            if rag.get('found'):
                state.reasoning_steps.append(
                    f"RAG Knowledge Agent generated a grounded answer via "
                    f"{rag.get('generated_by', {}).get('mode')} LLM citing "
                    f"{len(rag.get('sources', []))} document passage(s)."
                )
            else:
                state.reasoning_steps.append(
                    'RAG Knowledge Agent found no document passage above the relevance '
                    'threshold and reported that honestly (no generation attempted).'
                )
            state.tasks.append(self.complete_task(task, {
                'found': rag.get('found'),
                'sources': len(rag.get('sources', [])),
                'generated_by': rag.get('generated_by', {}).get('mode'),
            }))
        except Exception as e:
            state.errors.append('RAG unavailable: ' + str(e))
            state.tasks.append(self.fail_task(task, e))
        return state
