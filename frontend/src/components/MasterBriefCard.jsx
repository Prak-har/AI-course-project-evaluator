import { useState } from "react";

export default function MasterBriefCard({ masterBrief, onUpload, loading }) {
  const [title, setTitle] = useState(masterBrief?.title || "Course Master Brief");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onUpload({ title, text, file });
    setText("");
    setFile(null);
    event.target.reset();
  };

  return (
    <div className="section-shell">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-ink">Master Topic Brief</h2>
        <p className="mt-2 text-sm text-slate-600">
          Upload the accepted project-topic brief here. Submissions that do not align with this brief are rejected and capped at 2 marks.
        </p>
      </div>

      {masterBrief ? (
        <div className="mb-5 rounded-3xl border border-slate-200 bg-slate-50/70 p-4">
          <p className="text-sm font-semibold text-ink">{masterBrief.title}</p>
          <p className="mt-1 text-xs text-slate-500">
            {masterBrief.original_filename || "Text brief"} - updated{" "}
            {masterBrief.updated_at ? new Date(masterBrief.updated_at).toLocaleString() : "recently"}
          </p>
          <p className="mt-3 text-sm leading-6 text-slate-600">{masterBrief.content_preview}</p>
        </div>
      ) : (
        <div className="mb-5 rounded-3xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
          No master brief uploaded yet. Evaluations currently accept submissions without topic gating.
        </div>
      )}

      <form className="space-y-5" onSubmit={handleSubmit}>
        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">Brief title</label>
          <input className="input-shell" value={title} onChange={(event) => setTitle(event.target.value)} />
        </div>

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">Paste brief text</label>
          <textarea
            className="input-shell min-h-32 resize-y"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Paste the allowed project themes, accepted problem domains, and any topic constraints here."
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">Attach brief file</label>
          <input
            type="file"
            accept=".pdf,.txt,.md,.text"
            className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-2xl file:border-0 file:bg-accent file:px-4 file:py-3 file:font-semibold file:text-white hover:file:bg-teal-700"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </div>

        <button type="submit" className="action-button" disabled={loading || (!text.trim() && !file)}>
          {loading ? "Saving brief..." : masterBrief ? "Replace master brief" : "Upload master brief"}
        </button>
      </form>
    </div>
  );
}
