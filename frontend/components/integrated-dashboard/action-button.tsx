"use client";
import { Ban, CheckCircle2, Clock, Eye, Pencil, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
const config = {
  accept: { icon: CheckCircle2, cls: "bg-green-600 text-white hover:bg-green-700", label: "Accept" },
  reject: { icon: XCircle, cls: "bg-red-500 text-white hover:bg-red-600", label: "Reject" },
  ignore: { icon: Clock, cls: "bg-amber-500 text-white hover:bg-amber-600", label: "Ignore" },
  modify: { icon: Pencil, cls: "bg-blue-600 text-white hover:bg-blue-700", label: "Modify" },
  block: { icon: Ban, cls: "bg-red-600 text-white hover:bg-red-700", label: "Block" },
  view: { icon: Eye, cls: "bg-indigo-600 text-white hover:bg-indigo-700", label: "View" }
};
export function ActionButton({ action, onClick }: { action: keyof typeof config; onClick?: () => void }) {
  const item = config[action]; const Icon = item.icon;
  return <Button size="sm" onClick={onClick} className={cn("h-7 gap-1 rounded-md px-2 text-[11px]", item.cls)}><Icon className="h-3 w-3" />{item.label}</Button>;
}
