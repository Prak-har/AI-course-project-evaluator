import { toDisplayText } from "../utils/errors";

function renderItems(items, fallback) {
  if (!items?.length) {
    return [fallback];
  }
  return items.map((item) => toDisplayText(item, fallback));
}

function FeedbackColumn({ title, items, tone }) {
  const tones = {
    good: "border-emerald-100 bg-emerald-50 text-emerald-900",
    risk: "border-rose-100 bg-rose-50 text-rose-900",
    next: "border-amber-100 bg-amber-50 text-amber-900",
  };

  return (
    <div className={`rounded-3xl border p-4 ${tones[tone]}`}>
      <p className="text-sm font-semibold uppercase tracking-[0.18em]">{title}</p>
      <div className="mt-3 space-y-2 text-sm leading-6">
        {renderItems(items, "Insufficient data").map((item) => (
          <p key={`${title}-${item}`} className="rounded-2xl bg-white/70 px-3 py-2">
            {item}
          </p>
        ))}
      </div>
    </div>
  );
}

export default function FeedbackFocusPanel({ evaluation, title = "Current Feedback Focus", subtitle, action = null }) {
  if (!evaluation) {
    return (
      <div className="section-shell">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h2 className="text-2xl font-bold text-ink">{title}</h2>
          {action}
        </div>
        <p className="mt-3 text-sm text-slate-600">{subtitle || "Upload work to surface the latest strong areas, risks, and next steps here."}</p>
      </div>
    );
  }

  const carryForward = evaluation.feedback?.carry_forward || null;

  return (
    <div className="section-shell">
      <div className="mb-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-2xl font-bold text-ink">{title}</h2>
            <p className="mt-2 text-sm text-slate-600">
              {subtitle || "This summary keeps the strongest signals from the latest evaluation visible without digging through the full history."}
            </p>
          </div>
          {action}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <FeedbackColumn title="Strong Areas" items={evaluation.feedback?.strengths} tone="good" />
        <FeedbackColumn title="Needs Work" items={evaluation.feedback?.weaknesses} tone="risk" />
        <FeedbackColumn title="Next Actions" items={evaluation.feedback?.suggestions} tone="next" />
      </div>

      {carryForward ? (
        <div className="mt-6 rounded-3xl border border-slate-200 bg-slate-50/80 p-5">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Carry Forward Check</p>
          <p className="mt-3 rounded-2xl bg-white px-4 py-3 text-sm leading-6 text-slate-700">
            {toDisplayText(carryForward.summary, "Insufficient data")}
          </p>

          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            <FeedbackColumn title="Addressed Earlier" items={carryForward.addressed_items} tone="good" />
            <FeedbackColumn title="Still Pending" items={carryForward.pending_items} tone="next" />
          </div>
        </div>
      ) : null}
    </div>
  );
}
