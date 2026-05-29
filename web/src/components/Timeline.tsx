import { AlertTriangle, CheckCircle2, CircleDot, DatabaseZap } from "lucide-react";
import type { Checkpoint } from "../types";

type TimelineProps = {
  checkpoints: Checkpoint[];
  selectedCheckpointId?: string;
  onSelectCheckpoint: (checkpointId: string) => void;
};

function StatusIcon({ checkpoint, selected }: { checkpoint: Checkpoint; selected: boolean }) {
  if (selected) return <CircleDot size={17} />;
  if (checkpoint.status === "diagnostic") return <AlertTriangle size={17} />;
  return <CheckCircle2 size={17} />;
}

export function Timeline({ checkpoints, selectedCheckpointId, onSelectCheckpoint }: TimelineProps) {
  return (
    <section className="timeline-panel">
      <div className="panel-heading">
        <span>Checkpoint Timeline</span>
        <strong>{checkpoints.length} snapshots</strong>
      </div>
      <div className="timeline-list">
        {checkpoints.map((checkpoint) => {
          const selected = checkpoint.id === selectedCheckpointId;
          return (
            <button
              className={selected ? "timeline-item selected" : `timeline-item ${checkpoint.status}`}
              key={checkpoint.id}
              onClick={() => onSelectCheckpoint(checkpoint.id)}
              type="button"
            >
              <span className="timeline-rail">
                <StatusIcon checkpoint={checkpoint} selected={selected} />
              </span>
              <span className="timeline-main">
                <span className="timeline-title">
                  <strong>{checkpoint.ordinal}. {checkpoint.title}</strong>
                  <code>{checkpoint.node}</code>
                </span>
                <span className="timeline-subline">
                  {new Date(checkpoint.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit"
                  })}
                  <span>
                    <DatabaseZap size={13} />
                    {(checkpoint.sizeBytes / 1024).toFixed(1)} KB
                  </span>
                  {checkpoint.parentId ? <span>parent {checkpoint.parentId}</span> : null}
                </span>
              </span>
              {checkpoint.diagnostics.length > 0 ? (
                <span className="timeline-badge">{checkpoint.diagnostics[0].code}</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </section>
  );
}
