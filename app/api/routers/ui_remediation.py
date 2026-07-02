from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from app.shared.responses import ok

router = APIRouter(prefix="/ui-remediation", tags=["UI Remediation"])

class Context(BaseModel):
    persona: str = "Executive"
    scope_type: str = "Region"
    scope_id: str = "REG101"
    period: str = "YTD"
    compare_to: str = "Prior Year"

class AssistantRequest(Context):
    question: str

class IngestRequest(BaseModel):
    document_name: str = "managed_account_playbook.pdf"
    document_type: str = "pdf"
    content: str = "Managed account review playbook."

def kpis(mult=1.0):
    return [
        {"label":"Total Revenue","value":f"${55.43*mult:.2f}M","delta":"+12.6%","status":"good"},
        {"label":"Managed Revenue","value":f"${25.07*mult:.2f}M","delta":"+18.4%","status":"good"},
        {"label":"Managed Revenue %","value":"45.2%","delta":"+3.6 pp","status":"good"},
        {"label":"Households","value":"804","delta":"+8.1%","status":"good"},
        {"label":"NNM","value":"$65.3M","delta":"+5.2%","status":"good"},
        {"label":"NCF","value":"$17.9M","delta":"+4.2%","status":"good"},
        {"label":"AUM","value":"$1.107B","delta":"+9.7%","status":"good"},
        {"label":"Goal Attainment","value":"72%","delta":"On Track","status":"warn"},
    ]

@router.post("/dashboard")
def dashboard(context: Context):
    return ok(data={
        "kpis": kpis(),
        "insight": {"headline":"Strong revenue growth driven by managed accounts","summary":"Revenue is up 12.6% vs prior year, driven by managed account growth and new household acquisition. Fixed income remains the key watch-out.","drivers":[{"label":"Managed Accounts","value":"+18.4%","status":"good"},{"label":"New Households","value":"+23.3%","status":"good"},{"label":"Fixed Income Revenue","value":"-6.4%","status":"bad"}]},
        "coaching":["Prioritize managed account reviews for top 15 households.","Schedule fixed-income follow-up for households with recent redemptions.","Increase meeting frequency by 15% for at-risk clients."],
        "trend":[{"month":"Jan","revenue":42,"managed":17,"prior":38},{"month":"Feb","revenue":46,"managed":19,"prior":41},{"month":"Mar","revenue":50,"managed":21,"prior":44},{"month":"Apr","revenue":53,"managed":23,"prior":47},{"month":"May","revenue":55.4,"managed":25.1,"prior":49}],
        "mix":[{"name":"Managed Accounts","value":45.2},{"name":"Equities","value":24.6},{"name":"Fixed Income","value":15.8},{"name":"Mutual Funds","value":10.0},{"name":"Other","value":4.4}],
        "opportunities":[{"name":"Managed Account Expansion","score":92,"impact":"$212K","status":"good"},{"name":"NNM Outflow Recovery","score":88,"impact":"$156K","status":"warn"},{"name":"Fixed Income Ladder","score":76,"impact":"$84K","status":"warn"}],
        "recommendations":[{"name":"Schedule Managed Account Review","confidence":91,"impact":"$212K","status":"Passed"},{"name":"Launch NNM Recovery Sequence","confidence":86,"impact":"$156K","status":"Review Required"},{"name":"Increase Client Meeting Cadence","confidence":79,"impact":"$84K","status":"Passed"}],
        "agentTrace":["SupervisorAgent","ContextAgent","InsightAgent","CoachingAgent","MemoryAgent"]
    })

@router.post("/revenue-analytics")
def revenue(context: Context):
    return ok(data={
        "kpis": kpis(),
        "hierarchy":[{"level":"Firm","name":"iPerform Wealth","revenue":"$125.4M","growth":"+8.7%","status":"good"},{"level":"Division","name":"East Division","revenue":"$71.2M","growth":"+10.1%","status":"good"},{"level":"Region","name":"New York Region","revenue":"$55.4M","growth":"+12.6%","status":"good"},{"level":"Market","name":"Downtown Market","revenue":"$43.4M","growth":"-4.8%","status":"bad"},{"level":"Advisor","name":"Alex Morgan","revenue":"$4.82M","growth":"+12.6%","status":"good"}],
        "top":[{"name":"North Shore","growth":"+22.7%"},{"name":"West City","growth":"+16.8%"},{"name":"South Ridge","growth":"+12.3%"}],
        "bottom":[{"name":"Downtown","growth":"-8.4%"},{"name":"East Valley","growth":"-6.2%"},{"name":"Midtown","growth":"-3.7%"}],
        "transactions":[{"date":"May 12","household":"Parker Family","product":"Managed Account","impact":"+$12,450","status":"good"},{"date":"May 8","household":"Rivera Trust","product":"Fixed Income","impact":"-$4,120","status":"bad"},{"date":"May 5","household":"Chen Foundation","product":"Equities","impact":"+$8,230","status":"good"}],
        "trend":[{"month":"Jan","revenue":42,"aum":860,"nnm":44,"ncf":12},{"month":"Feb","revenue":46,"aum":900,"nnm":49,"ncf":13},{"month":"Mar","revenue":50,"aum":970,"nnm":55,"ncf":15},{"month":"Apr","revenue":53,"aum":1030,"nnm":60,"ncf":16},{"month":"May","revenue":55.4,"aum":1107,"nnm":65,"ncf":17.9}],
    })

@router.post("/advisor-360")
def advisor(context: Context):
    return ok(data={"profile":{"name":"Alex Morgan","role":"Financial Advisor","market":"Downtown Market","region":"New York Region","health":82,"risk":"Moderate"},"kpis":kpis(.078),"households":[{"name":"Parker Family","aum":"$18.2M","nnm":"$1.1M","action":"Managed account review","status":"good"},{"name":"Rivera Trust","aum":"$11.7M","nnm":"-$340K","action":"Outflow recovery call","status":"bad"},{"name":"Chen Foundation","aum":"$24.9M","nnm":"$2.5M","action":"Fixed income ladder review","status":"good"}],"crm":[{"title":"Portfolio Review","date":"2026-06-04","type":"Meeting","status":"Completed"},{"title":"Liquidity Event","date":"2026-06-09","type":"Call","status":"Follow-up"},{"title":"AGP Coaching Note","date":"2026-06-13","type":"Note","status":"Logged"}],"predictions":[{"label":"Revenue Growth","value":"+12.4%","status":"good"},{"label":"Churn Risk","value":"15%","status":"good"},{"label":"Goal Attainment","value":"72%","status":"warn"}],"similar":[{"name":"Maya Chen","similarity":"92%","reason":"Similar product mix and AGP stage"},{"name":"Noah Williams","similarity":"87%","reason":"Similar managed revenue trajectory"}]})

@router.post("/recommendations")
def recommendations(context: Context):
    return ok(data={"pipeline":[{"stage":"Detected","count":28},{"stage":"Qualified","count":18},{"stage":"Recommended","count":12},{"stage":"Accepted","count":7},{"stage":"Implemented","count":5}],"recommendations":[{"title":"Schedule Managed Account Review","priority":"High","confidence":91,"impact":"$212K","status":"Passed","why":"Managed revenue gap and household suitability are both high."},{"title":"Launch NNM Recovery Sequence","priority":"High","confidence":86,"impact":"$156K","status":"Review Required","why":"Negative NCF households show recoverable outflow pattern."},{"title":"Increase Client Meeting Cadence","priority":"Medium","confidence":79,"impact":"$84K","status":"Passed","why":"Meeting cadence is below peer benchmark."}],"learning":{"accepted":68,"rejected":18,"ignored":14,"reward":0.61,"impact":"$512K"},"agentTrace":["OpportunityAgent","RecommendationAgent","ComplianceAgent","FeedbackAgent","MemoryAgent"]})

@router.post("/graph-explorer")
def graph(context: Context):
    return ok(data={"nodes":[{"id":"ADV0001","label":"Alex Morgan","type":"Advisor"},{"id":"HH001","label":"Parker Family","type":"Household"},{"id":"ACC001","label":"Managed Account","type":"Account"},{"id":"PRD001","label":"Managed Accounts","type":"Product"},{"id":"OPP001","label":"Expansion Opportunity","type":"Opportunity"},{"id":"REC001","label":"Schedule Review","type":"Recommendation"},{"id":"MEM001","label":"Reasoning Memory","type":"Memory"}],"edges":[{"source":"ADV0001","target":"HH001","label":"SERVES"},{"source":"HH001","target":"ACC001","label":"OWNS"},{"source":"ACC001","target":"PRD001","label":"HOLDS"},{"source":"HH001","target":"OPP001","label":"HAS_OPPORTUNITY"},{"source":"OPP001","target":"REC001","label":"GENERATES"},{"source":"MEM001","target":"OPP001","label":"USED_BY"}],"selected":{"id":"ADV0001","name":"Alex Morgan","score":88,"relationships":6}})

@router.post("/features-embeddings")
def features(context: Context):
    return ok(data={"featureSets":[{"name":"Advisor Revenue Features","count":38,"freshness":"Current","status":"good"},{"name":"Household Behavior Features","count":44,"freshness":"Current","status":"good"},{"name":"Opportunity Propensity Features","count":27,"freshness":"1 day","status":"warn"},{"name":"Graph Relationship Features","count":19,"freshness":"Current","status":"good"}],"similarity":[{"name":"Advisor Maya Chen","score":92,"reason":"Similar product mix and growth trajectory"},{"name":"Advisor Noah Williams","score":87,"reason":"Similar AGP cohort and revenue stage"},{"name":"Household Rivera Trust","score":81,"reason":"Similar liquidity profile"}],"projection":[{"x":12,"y":18,"label":"Alex Morgan"},{"x":22,"y":25,"label":"Maya Chen"},{"x":18,"y":30,"label":"Noah Williams"},{"x":45,"y":42,"label":"Parker Family"},{"x":58,"y":50,"label":"Rivera Trust"}]})

@router.post("/memory-explainability")
def memory(context: Context):
    return ok(data={"timeline":[{"title":"Advisor asked about revenue decline","date":"2026-06-01","type":"Conversation","status":"good"},{"title":"Managed revenue gap detected","date":"2026-06-03","type":"Reasoning","status":"warn"},{"title":"Managed account review generated","date":"2026-06-05","type":"Recommendation","status":"good"},{"title":"Recommendation accepted","date":"2026-06-10","type":"Feedback","status":"good"}],"path":["Revenue Mix Gap","Peer Benchmark Gap","Household Suitability","Compliance Playbook","Recommendation"],"evidence":[{"source":"TigerGraph","detail":"Advisor-Household-Account path"},{"source":"Chroma","detail":"Managed account review playbook"},{"source":"Feature Store","detail":"Managed revenue mix feature"}]})

@router.post("/assistant")
def assistant(request: AssistantRequest):
    q = request.question.lower()
    answer = "Revenue pressure is tied to fixed income redemptions, partially offset by managed account growth. Recommended action: prioritize managed account reviews and schedule outflow recovery calls for top at-risk households." if "revenue" in q else "Top opportunities are Managed Account Expansion ($212K), NNM Recovery ($156K), and Client Meeting Cadence ($84K)."
    return ok(data={"answer":answer,"sources":["TigerGraph context","Feature Store","Memory Timeline","Chroma Playbook"],"actions":["View opportunities","Open explainability","Create recommendation"]})

@router.post("/document-ingestion")
def ingest(request: IngestRequest):
    return ok(data={"document_id":"DOC-DEMO-001","document_name":request.document_name,"status":"indexed","chunks":12,"embeddings":12,"collection":"iperform_knowledge_base","lineage":["uploaded","chunked","embedded","indexed","available_to_agents"]})
