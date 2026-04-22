import { useState } from "react";

export default function UploadCard({ onUpload, loading }) {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onUpload({ title, text, file });
    setTitle("");
    setText("");
    setFile(null);
    event.target.reset();
  };

  return (
    <div className="section-shell">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-ink">Upload Project</h2>
          <p className="mt-2 text-sm text-slate-600">
            Upload a PDF or paste project text. Draft evaluation is triggered immediately after upload.
          </p>
        </div>
        <span className="data-pill bg-amber-50 text-amber-700">PDF or plain text</span>
      </div>

      <form className="space-y-5" onSubmit={handleSubmit}>
        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">Project title</label>
          <input
            className="input-shell"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="AI Attendance Monitoring System"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">Paste project text</label>
          <textarea
            className="input-shell min-h-40 resize-y"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Paste an abstract, README, or full project write-up here."
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-semibold text-slate-700">Attach project file</label>
          <input
            type="file"
            accept=".pdf,.txt,.md,.text"
            className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-2xl file:border-0 file:bg-accent file:px-4 file:py-3 file:font-semibold file:text-white hover:file:bg-teal-700"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </div>

        <button type="submit" className="action-button" disabled={loading || (!text.trim() && !file)}>
          {loading ? "Uploading and evaluating..." : "Upload and run draft evaluation"}
        </button>
      </form>
    </div>
  );
}

