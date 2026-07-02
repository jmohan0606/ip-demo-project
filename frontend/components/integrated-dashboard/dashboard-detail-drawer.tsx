"use client";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
export function DashboardDetailDrawer({ title, open, onClose, children }: { title: string; open: boolean; onClose: () => void; children: React.ReactNode }) {
  if (!open) return null;
  return <div className="fixed inset-0 z-50 bg-black/30"><div className="absolute right-0 top-0 h-full w-[420px] border-l border-border bg-background p-4 shadow-2xl"><div className="flex items-center justify-between"><div><Badge variant="glass">Details</Badge><h2 className="mt-2 text-lg font-black">{title}</h2></div><Button variant="outline" size="icon" onClick={onClose}><X className="h-4 w-4" /></Button></div><div className="mt-4">{children}</div></div></div>;
}
