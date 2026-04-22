import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function formatLabel(value, totalPossibleMarks) {
  if (typeof value !== "number") {
    return "Pending";
  }
  if (typeof totalPossibleMarks === "number") {
    return `${value.toFixed(2)}/${totalPossibleMarks.toFixed(2)}`;
  }
  return value.toFixed(2);
}

export default function MarksComparisonChart({ rows, meanScore, totalPossibleMarks }) {
  const data = [...(rows || [])]
    .map((row) => ({
      name: row.student.name,
      marks: row.final_marks?.earned ?? row.comparison?.current_marks,
    }))
    .filter((row) => typeof row.marks === "number")
    .sort((left, right) => right.marks - left.marks)
    .slice(0, 10);

  return (
    <div className="section-shell">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">Marks Comparison</h2>
        <p className="mt-2 text-sm text-slate-600">Compare the strongest current cumulative marks across the class.</p>
      </div>

      {data.length ? (
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ left: 12, right: 18 }}>
              <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fill: "#475569", fontSize: 12 }} />
              <YAxis dataKey="name" type="category" width={96} tick={{ fill: "#475569", fontSize: 12 }} />
              <Tooltip
                formatter={(value) => formatLabel(Number(value), totalPossibleMarks)}
                cursor={{ fill: "rgba(15, 118, 110, 0.08)" }}
              />
              {typeof meanScore === "number" ? (
                <ReferenceLine
                  x={meanScore}
                  stroke="#ea580c"
                  strokeDasharray="6 4"
                  label={{ value: "Avg", position: "top", fill: "#ea580c", fontSize: 12 }}
                />
              ) : null}
              <Bar dataKey="marks" fill="#0f766e" radius={[0, 12, 12, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="rounded-3xl border border-dashed border-slate-300 px-5 py-8 text-sm text-slate-500">
          Once stage evaluations exist, the class marks comparison will appear here.
        </div>
      )}
    </div>
  );
}
