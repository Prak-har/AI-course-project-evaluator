import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = ["#0f766e", "#1d4ed8", "#c2410c", "#7c2d12"];

export default function ScoreBreakdownChart({ evaluation }) {
  const rubricWeights = evaluation?.rubric_weights || evaluation?.feedback?.rubric_weights || [];
  const rubricScores = evaluation?.rubric_scores || evaluation?.feedback?.rubric_scores || {};
  const data = rubricWeights.length
    ? rubricWeights.map((rubric) => ({
        name: rubric.name,
        score: rubricScores[rubric.key] || 0,
      }))
    : [
        { name: "Innovation", score: evaluation?.innovation_score || 0 },
        { name: "Tech Depth", score: evaluation?.technical_score || 0 },
        { name: "Clarity", score: evaluation?.clarity_score || 0 },
        { name: "Impact", score: evaluation?.impact_score || 0 },
      ];

  return (
    <div className="section-shell">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">Score Breakdown</h2>
        <p className="mt-2 text-sm text-slate-600">Criterion-level view for the latest evaluation.</p>
      </div>

      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" />
            <XAxis dataKey="name" tick={{ fill: "#475569", fontSize: 12 }} />
            <YAxis domain={[0, 10]} tick={{ fill: "#475569", fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="score" radius={[12, 12, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
