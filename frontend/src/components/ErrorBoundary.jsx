import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      message: error?.message || "Unexpected UI error.",
    };
  }

  componentDidCatch(error) {
    console.error("Application error boundary caught:", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center px-4 py-10">
          <div className="glass-card w-full max-w-2xl p-8">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-500">UI Error</p>
            <h1 className="mt-4 text-3xl font-extrabold text-ink">The page hit a rendering issue.</h1>
            <p className="mt-4 text-sm leading-7 text-slate-600">
              Refresh the page once. If it still happens, sign out and sign back in. The captured error was:
            </p>
            <pre className="mt-4 overflow-x-auto rounded-2xl bg-slate-950 px-4 py-4 text-sm text-slate-100">
              {this.state.message}
            </pre>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
