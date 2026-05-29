import { Activity, Database, GitBranch, Search } from "lucide-react";
import type { Summary } from "../types";

type ChromeProps = {
  summary?: Summary;
};

export function TopChrome({ summary }: ChromeProps) {
  return (
    <header className="top-chrome">
      <div className="brand-lockup">
        <div className="brand-mark">
          <GitBranch size={18} />
        </div>
        <div>
          <h1>LangGraph Memory Inspector</h1>
          <span>{summary?.adapter ?? "Checkpoint adapter"}</span>
        </div>
      </div>
      <div className="chrome-search">
        <Search size={15} />
        <span>Filter threads, checkpoints, paths</span>
      </div>
      <div className="chrome-stats">
        <div>
          <Database size={15} />
          <span>{summary?.threadCount ?? 0} threads</span>
        </div>
        <div>
          <Activity size={15} />
          <span>{summary?.diagnosticsCount ?? 0} diagnostics</span>
        </div>
        <strong>{summary?.apiMode ?? "mock"}</strong>
      </div>
    </header>
  );
}
