import { CircleAlert, Clock3 } from "lucide-react";
import type { Thread } from "../types";

type ThreadSelectorProps = {
  threads: Thread[];
  selectedThreadId?: string;
  selectedNamespace?: string;
  onSelectThread: (threadId: string) => void;
  onSelectNamespace: (namespace: string) => void;
};

export function ThreadSelector({
  threads,
  selectedThreadId,
  selectedNamespace,
  onSelectThread,
  onSelectNamespace
}: ThreadSelectorProps) {
  const selectedThread = threads.find((thread) => thread.id === selectedThreadId);

  return (
    <aside className="thread-selector">
      <div className="panel-heading">
        <span>Threads</span>
        <strong>{threads.length}</strong>
      </div>
      {selectedThread ? (
        <div className="namespace-picker">
          <span>Active namespace</span>
          {selectedThread.namespaces.length > 1 ? (
            <select
              aria-label="Active namespace"
              onChange={(event) => onSelectNamespace(event.target.value)}
              value={selectedNamespace ?? selectedThread.namespaces[0]}
            >
              {selectedThread.namespaces.map((namespace) => (
                <option key={namespace || "default"} value={namespace}>
                  {namespace || "(default)"}
                </option>
              ))}
            </select>
          ) : (
            <code>{(selectedNamespace ?? selectedThread.namespaces[0]) || "(default)"}</code>
          )}
        </div>
      ) : null}
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
              <code>{thread.namespaces.length > 1 ? `${thread.namespaces.length} namespaces` : thread.namespace || "(default)"}</code>
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
