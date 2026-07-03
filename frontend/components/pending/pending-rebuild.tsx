interface PendingRebuildProps {
  title: string;
  blueprint: string;
}

export function PendingRebuild({ title, blueprint }: PendingRebuildProps) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 p-8 text-center">
      <h1 className="text-xl font-bold text-slate-800">{title}</h1>
      <p className="max-w-md text-sm text-slate-500">
        This page previously rendered hardcoded demo content and has been removed. It is being
        rebuilt against the real backend per the {blueprint} blueprint.
      </p>
    </div>
  );
}
