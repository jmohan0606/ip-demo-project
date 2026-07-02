"use client";
import { Card,CardContent,CardHeader,CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const data={
 advisor:"Avery Morgan",
 completion:83,
 goals:[
  {name:"Revenue Goal",target:100,actual:91,status:"At Risk"},
  {name:"Meetings",target:100,actual:86,status:"At Risk"},
  {name:"Prospect Conversion",target:100,actual:92,status:"On Track"}
 ],
 actions:[
  {title:"Increase weekly client meetings",owner:"Advisor",due:"2026-07-01",priority:"High"},
  {title:"Managed account campaign",owner:"MDW",due:"2026-07-05",priority:"Medium"}
 ]
};

export function AgpWorkspace(){
 return <div className="space-y-6">
  <div>
   <Badge variant="glass">Advisor Growth Program</Badge>
   <h2 className="mt-3 text-3xl font-black">AGP Goals & Coaching Workspace</h2>
  </div>

  <Card>
   <CardHeader><CardTitle>AGP Progress</CardTitle></CardHeader>
   <CardContent>
    <div className="text-5xl font-black">{data.completion}%</div>
    <div className="text-muted-foreground">Overall Goal Completion</div>
   </CardContent>
  </Card>

  <Card>
   <CardHeader><CardTitle>Goals & KPI Tracking</CardTitle></CardHeader>
   <CardContent className="space-y-3">
    {data.goals.map(g=><div key={g.name} className="rounded-xl border p-3 flex justify-between">
      <div>{g.name}</div><Badge>{g.status}</Badge>
    </div>)}
   </CardContent>
  </Card>

  <Card>
   <CardHeader><CardTitle>Coaching Actions</CardTitle></CardHeader>
   <CardContent className="space-y-3">
    {data.actions.map(a=><div key={a.title} className="rounded-xl border p-3">
      <div className="font-bold">{a.title}</div>
      <div>{a.owner} · {a.due} · {a.priority}</div>
    </div>)}
   </CardContent>
  </Card>

  <Card>
   <CardHeader><CardTitle>MDW / DDW Review</CardTitle></CardHeader>
   <CardContent>
    MDW Feedback, DDW Feedback, coaching notes, approvals and advisor review workflow.
   </CardContent>
  </Card>
 </div>
}
