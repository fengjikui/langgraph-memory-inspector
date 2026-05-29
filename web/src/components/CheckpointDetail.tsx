import { Braces, Download, FileDiff, ListTree } from "lucide-react";
import type { CausalChain, Checkpoint, DebugBundleExportResult, Diagnostic, NodeWrite, TimelineDiff } from "../types";

type ExportStatus =
  | { state: "idle" }
  | { state: "exporting" }
  | { state: "success"; result: DebugBundleExportResult }
  | { state: "error"; message: string };

type DetailProps = {
  checkpoint?: Checkpoint;
  writes: NodeWrite[];
  diff?: TimelineDiff;
  causalChain?: CausalChain;
  selectedDiagnostic?: Diagnostic;
  activeTab: "state" | "diff" | "writes";
  onTabChange: (tab: "state" | "diff" | "writes") => void;
  exportStatus: ExportStatus;
  exportRedacted: boolean;
  onExportRedactedChange: (enabled: boolean) => void;
  onExportDebugBundle: () => void;
};

function JsonBlock({ value }: { value: unknown }) {
  return <pre className="json-block">{JSON.stringify(value, null, 2)}</pre>;
}

export function CheckpointDetail({
  checkpoint,
  writes,
  diff,
  causalChain,
  selectedDiagnostic,
  activeTab,
  onTabChange,
  exportStatus,
  exportRedacted,
  onExportRedactedChange,
  onExportDebugBundle
}: DetailProps) {
  if (!checkpoint) {
    return (
      <aside className="detail-panel">
        <div className="empty-state">Select a checkpoint to inspect state.</div>
      </aside>
    );
  }

  return (
    <aside className="detail-panel">
      <div className="detail-header">
        <div>
          <span>Checkpoint Detail</span>
          <h2>{checkpoint.id}</h2>
        </div>
        <div className="detail-actions">
          <code>{checkpoint.node}</code>
          <label className="redaction-toggle">
            <input
              checked={exportRedacted}
              onChange={(event) => onExportRedactedChange(event.currentTarget.checked)}
              type="checkbox"
            />
            <span>Redact private fields</span>
          </label>
          <button
            className="export-button"
            disabled={exportStatus.state === "exporting"}
            onClick={onExportDebugBundle}
            title={
              exportRedacted
                ? "Export a redacted debug bundle for this checkpoint"
                : "Export a raw debug bundle that may contain private state"
            }
            type="button"
          >
            <Download size={14} />
            {exportStatus.state === "exporting" ? "Exporting" : exportRedacted ? "Export redacted" : "Export raw"}
          </button>
        </div>
      </div>

      {exportStatus.state === "success" ? (
        <div className="export-result" role="status">
          <strong>Debug bundle exported</strong>
          <span>
            <code>{exportStatus.result.path}</code>
          </span>
          <span>
            {formatBytes(exportStatus.result.fileSizeBytes)}
            {exportStatus.result.diagnosticIds.length > 0 ? (
              <> · {exportStatus.result.diagnosticIds.join(", ")}</>
            ) : null}
          </span>
          <span>
            Redaction: <strong>{exportStatus.result.redactionMode}</strong>
            {exportStatus.result.redactionMode === "redacted" ? (
              <> · {exportStatus.result.redactionCount} path(s)</>
            ) : (
              <> · may contain private state</>
            )}
          </span>
        </div>
      ) : null}

      {exportStatus.state === "error" ? (
        <div className="export-result error" role="alert">
          <strong>Export failed</strong>
          <span>{exportStatus.message}</span>
        </div>
      ) : null}

      <div className="state-cards">
        <div className="state-card">
          <span>selected_city</span>
          <strong className={checkpoint.state.selected_city === "Shanghai" ? "city-danger" : ""}>
            {checkpoint.state.selected_city || "(unset)"}
          </strong>
        </div>
        <div className="state-card">
          <span>retrieved_city</span>
          <strong className={checkpoint.state.retrieved_city === "Shanghai" ? "city-danger" : ""}>
            {checkpoint.state.retrieved_city ?? "(none)"}
          </strong>
        </div>
      </div>

      <div className="tab-bar" role="tablist" aria-label="Checkpoint viewers">
        <button className={activeTab === "state" ? "active" : ""} onClick={() => onTabChange("state")} type="button">
          <Braces size={14} />
          State
        </button>
        <button className={activeTab === "diff" ? "active" : ""} onClick={() => onTabChange("diff")} type="button">
          <FileDiff size={14} />
          Diff
        </button>
        <button className={activeTab === "writes" ? "active" : ""} onClick={() => onTabChange("writes")} type="button">
          <ListTree size={14} />
          Writes
        </button>
      </div>

      {activeTab === "state" ? (
        <div className="viewer-section">
          <div className="memory-list">
            {checkpoint.state.residence_memories.map((memory) => (
              <div className={memory.stale ? "memory-row stale" : "memory-row"} key={`${memory.value}-${memory.createdAt}`}>
                <span>{memory.key}</span>
                <strong>{memory.value}</strong>
                <code>{memory.source}</code>
              </div>
            ))}
          </div>
          <JsonBlock value={checkpoint.state} />
        </div>
      ) : null}

      {activeTab === "diff" ? (
        <div className="viewer-section">
          <p className="diff-summary">{diff?.summary}</p>
          <div className="diff-table">
            {diff?.rows.map((row) => (
              <div className={`diff-row ${row.kind}`} key={row.path}>
                <code>{row.path}</code>
                <span>{row.before}</span>
                <span>{row.after}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {activeTab === "writes" ? (
        <div className="viewer-section writes-list">
          {selectedDiagnostic?.writeChannel ? (
            <div className="write-focus">
              <strong>{selectedDiagnostic.code}</strong>
              <span>
                Looking for writes to <code>state.{selectedDiagnostic.writeChannel}</code>
                {selectedDiagnostic.statePath ? <> from <code>{selectedDiagnostic.statePath}</code></> : null}.
              </span>
            </div>
          ) : null}
          {selectedDiagnostic && causalChain ? (
            <div className="causal-chain" aria-label="Causal chain">
              <div className="causal-chain-header">
                <strong>Causal chain</strong>
                <span className="causal-headline">{causalChain.headline || causalChain.summary}</span>
                {causalChain.nodePath.length > 0 ? (
                  <div className="causal-node-path" aria-label="Node path">
                    {causalChain.nodePath.map((node, index) => (
                      <span key={`${node}-${index}`}>
                        <code>{node}</code>
                        {index < causalChain.nodePath.length - 1 ? <b>-&gt;</b> : null}
                      </span>
                    ))}
                  </div>
                ) : null}
                <span>{causalChain.summary}</span>
                {causalChain.nextAction ? <p>{causalChain.nextAction}</p> : null}
              </div>
              <div className="causal-chain-steps">
                {causalChain.steps.map((step) => (
                  <div className={`causal-step ${step.relation}`} key={`${step.checkpointId}-${step.relation}`}>
                    <div>
                      <strong>{step.checkpointId}</strong>
                      <code>{step.node}</code>
                    </div>
                    <span>{step.action || labelForRelation(step.relation)}</span>
                    <small>{labelForRelation(step.relation)}</small>
                    <div className="causal-step-meta">
                      {step.writeChannels.map((channel) => (
                        <code key={channel}>write {channel}</code>
                      ))}
                      {step.updatedChannels.map((channel) => (
                        <code key={channel}>updated {channel}</code>
                      ))}
                    </div>
                    {step.writes.map((write) => (
                      <p key={`${write.taskId}-${write.idx ?? "x"}-${write.channel}`}>
                        <code>{write.statePath}</code> via {write.node}: {write.valuePreview}
                      </p>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {writes.map((write) => (
            <div
              className={matchesDiagnosticWrite(write, selectedDiagnostic) ? "write-row focused" : "write-row"}
              key={write.id}
            >
              <div>
                <strong>{write.operation}</strong>
                <code>{write.path}</code>
              </div>
              <span>{write.node}</span>
              <JsonBlock value={write.after} />
            </div>
          ))}
          {selectedDiagnostic?.writeChannel && !writes.some((write) => matchesDiagnosticWrite(write, selectedDiagnostic)) ? (
            <div className="write-empty-match">
              No direct write row for <code>state.{selectedDiagnostic.writeChannel}</code> is attached to this checkpoint.
              The diagnostic is still grounded in the decoded state snapshot above.
            </div>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}

function matchesDiagnosticWrite(write: NodeWrite, diagnostic?: Diagnostic): boolean {
  if (!diagnostic?.writeChannel) return false;
  return write.path === `state.${diagnostic.writeChannel}`;
}

function labelForRelation(relation: string): string {
  if (relation === "introduced_diagnostic") return "introduced diagnostic";
  if (relation === "selected_checkpoint") return "selected checkpoint";
  return "related write";
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} bytes`;
  return `${(value / 1024).toFixed(1)} KB`;
}
