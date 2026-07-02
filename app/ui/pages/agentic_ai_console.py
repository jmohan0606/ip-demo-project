import streamlit as st
from app.agents.state.agent_state import AgenticRequest
from app.services.agentic_ai_service import AgenticAiService

def render_agentic_ai_console_page():
    st.title('Agentic AI Console')
    st.caption('LangGraph/LangChain-ready multi-agent orchestration for advisor coaching.')
    service=AgenticAiService(); tab_run,tab_agents=st.tabs(['Run Agent Workflow','Agent Registry'])
    with tab_run:
        persona=st.selectbox('Persona',['Advisor','MDW','DDW','Firm']); scope_type=st.selectbox('Scope Type',['Advisor','Market','Region','Division','Firm']); scope_id=st.text_input('Scope ID',value='ADV0001'); question=st.text_area('Question',value='Why is my revenue low and what should I do next?'); caps=st.multiselect('Requested Capabilities',['rag','prediction','opportunity','recommendation','feedback'],default=['prediction','opportunity','recommendation'])
        if st.button('Run Agentic Workflow'):
            with st.status('Running supervisor and specialist agents...', expanded=True) as status:
                response=service.run(AgenticRequest(question=question,persona=persona,scope_type=scope_type,scope_id=scope_id,requested_capabilities=caps,write_to_tigergraph=False))
                st.subheader('Agentic Answer'); st.write(response.answer); st.metric('Confidence',response.confidence)
                with st.expander('Agent Tasks'): st.json([t.model_dump() for t in response.tasks])
                with st.expander('Evidence'): st.json([e.model_dump() for e in response.evidence])
                with st.expander('Reasoning Steps'): st.write(response.reasoning_steps)
                status.update(label='Agentic workflow complete', state='complete')
    with tab_agents: st.dataframe(service.list_agents(), use_container_width=True)
