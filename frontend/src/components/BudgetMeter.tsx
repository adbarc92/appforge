import { useProjectStore } from "../stores/projectStore";

const THRESHOLD_CLASS: Record<number, string> = {
  0: "bg-green-500",
  50: "bg-green-500",
  75: "bg-yellow-500",
  85: "bg-orange-500",
  95: "bg-red-500",
  100: "bg-red-700",
};

export function BudgetMeter() {
  const budget = useProjectStore((s) => s.budget);
  const pct = budget.limit > 0 ? Math.min(100, (budget.spent / budget.limit) * 100) : 0;
  const barClass = THRESHOLD_CLASS[budget.threshold] ?? "bg-green-500";

  return (
    <div
      data-testid="budget-meter"
      data-threshold={budget.threshold}
      className="flex items-center gap-3 px-4 py-2 border-b bg-white"
    >
      <span className="text-sm font-medium">
        ${budget.spent.toFixed(2)} / ${budget.limit.toFixed(0)}
      </span>
      <div className="flex-1 h-2 bg-gray-200 rounded overflow-hidden">
        <div className={`h-full transition-all ${barClass}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
