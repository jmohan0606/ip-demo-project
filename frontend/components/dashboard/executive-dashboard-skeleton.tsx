export function ExecutiveDashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-24 animate-pulse rounded-3xl bg-muted" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => <div key={index} className="h-36 animate-pulse rounded-2xl bg-muted" />)}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.25fr_.75fr]">
        <div className="h-[460px] animate-pulse rounded-2xl bg-muted" />
        <div className="h-[460px] animate-pulse rounded-2xl bg-muted" />
      </div>
    </div>
  );
}
