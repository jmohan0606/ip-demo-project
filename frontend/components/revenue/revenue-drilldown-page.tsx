
"use client";
import { Card,CardContent,CardHeader,CardTitle } from "@/components/ui/card";
export function RevenueDrilldownPage(){
 return <div className="space-y-6">
  <Card><CardHeader><CardTitle>Revenue Analytics & Drilldown</CardTitle></CardHeader>
  <CardContent>
   <div className="grid gap-4 md:grid-cols-4">
    <div>Firm → Division → Region → Market → Advisor</div>
    <div>Revenue</div><div>AUM / NNM / NCF</div><div>Product Mix</div>
   </div>
  </CardContent></Card>
  <Card><CardHeader><CardTitle>Hierarchical Drilldown</CardTitle></CardHeader>
  <CardContent>Supports revenue, product category, subcategory, account and transaction-level drilldown.</CardContent></Card>
 </div>
}
