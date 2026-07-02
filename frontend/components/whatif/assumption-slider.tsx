"use client";

export function AssumptionSlider({
  label,
  value,
  onChange,
  min = 0,
  max = 50,
  suffix = "%"
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  suffix?: string;
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
      <div className="flex items-center justify-between">
        <div className="font-bold">{label}</div>
        <div className="text-lg font-black">{value}{suffix}</div>
      </div>
      <input
        className="mt-4 w-full accent-blue-600"
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </div>
  );
}
