import { CircleAlert, Clock3 } from "lucide-react";
import type { Thread } from "../types";

type ThreadSelectorProps = {
  threads: Thread[];
  selectedThreadId?: string;
  onSelectThread: (threadId: string) => void;
};

export function ThreadSelector({ threads, selectedThreadId, onSelectThread }: ThreadSelectorProps) {
  return (
    <aside className="thread-selector">
      <div className="panel-heading">
        <span>Threads</span>
        <strong>{threads.length}</strong>
      </div>
      <div className="thread-list">
        {threads.map((thread) => (
          <button
            className={thread.id === selectedThreadId ? "thread-row selected" : "thread-row"}
            key={thread.id}
            onClick={() => onSelectThread(thread.id)}
            type="button"
          >
            <span className="thread-title">{thread.title}</span>
            <span className="thread-meta">
              <Clock3 size={13} />
              {new Date(thread.updatedAt).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit"
              })}
            </span>
            <span className="thread-foot">
              <code>{thread.namespace}</code>
              {thread.diagnosticCount > 0 ? (
                <span className="diag-chip critical">
                  <CircleAlert size={12} />
                  {thread.diagnosticCount}
                </span>
              ) : (
                <span className="diag-chip clean">clean</span>
              )}
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
}
