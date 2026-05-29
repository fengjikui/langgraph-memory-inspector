import { AlertTriangle, CheckCircle2, CircleDot, DatabaseZap } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import type { Checkpoint, TimelineFilters, TimelinePagination } from "../types";

type TimelineProps = {
  checkpoints: Checkpoint[];
  pagination?: TimelinePagination;
  filters: TimelineFilters;
  loading: boolean;
  selectedCheckpointId?: string;
  onSelectCheckpoint: (checkpointId: string) => void;
  onLoadPrevious: () => void;
  onFiltersChange: (filters: TimelineFilters) => void;
};

function StatusIcon({ checkpoint, selected }: { checkpoint: Checkpoint; selected: boolean }) {
  if (selected) return <CircleDot size={17} />;
  if (checkpoint.status === "diagnostic") return <AlertTriangle size={17} />;
  return <CheckCircle2 size={17} />;
}

export function Timeline({
  checkpoints,
  pagination,
  filters,
  loading,
  selectedCheckpointId,
  onSelectCheckpoint,
  onLoadPrevious,
  onFiltersChange
}: TimelineProps) {
  const selectedItemRef = useRef<HTMLButtonElement | null>(null);
  const [changedPathDraft, setChangedPathDraft] = useState(filters.changedPath ?? "");

  useEffect(() => {
    setChangedPathDraft(filters.changedPath ?? "");
  }, [filters.changedPath]);

  useEffect(() => {
    selectedItemRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [selectedCheckpointId]);

  function applyPathFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onFiltersChange({ ...filters, changedPath: changedPathDraft.trim() || undefined });
  }

  const rangeStart = pagination && pagination.totalCount > 0 ? pagination.offset + 1 : 0;
  const rangeEnd = pagination ? pagination.offset + checkpoints.length : checkpoints.length;

  return (
    <section className="timeline-panel">
      <div className="panel-heading">
        <span>Checkpoint Timeline</span>
        <strong>
          {pagination ? `${rangeStart}-${rangeEnd} of ${pagination.totalCount}` : `${checkpoints.length} snapshots`}
        </strong>
      </div>
      <div className="timeline-controls">
        <label>
          <input
            checked={Boolean(filters.diagnostic)}
            onChange={(event) => onFiltersChange({ ...filters, diagnostic: event.currentTarget.checked || undefined })}
            type="checkbox"
          />
          Diagnostics only
        </label>
        <form onSubmit={applyPathFilter}>
          <input
            aria-label="State path filter"
            onChange={(event) => setChangedPathDraft(event.currentTarget.value)}
            placeholder="state.memory_events"
            value={changedPathDraft}
          />
          <button type="submit">Apply</button>
          {filters.changedPath ? (
            <button
              onClick={() => onFiltersChange({ ...filters, changedPath: undefined })}
              type="button"
            >
              Clear
            </button>
          ) : null}
        </form>
      </div>
      <div className="timeline-list">
        {pagination?.hasPrevious ? (
          <button
            className="timeline-load-more"
            disabled={loading}
            onClick={onLoadPrevious}
            type="button"
          >
            {loading ? "Loading earlier checkpoints" : "Load earlier checkpoints"}
          </button>
        ) : null}
        {checkpoints.map((checkpoint) => {
          const selected = checkpoint.id === selectedCheckpointId;
          return (
            <button
              className={selected ? "timeline-item selected" : `timeline-item ${checkpoint.status}`}
              key={checkpoint.id}
              onClick={() => onSelectCheckpoint(checkpoint.id)}
              ref={selected ? selectedItemRef : undefined}
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
        {checkpoints.length === 0 ? (
          <div className="timeline-empty">No checkpoints match the current filters.</div>
        ) : null}
      </div>
    </section>
  );
}
