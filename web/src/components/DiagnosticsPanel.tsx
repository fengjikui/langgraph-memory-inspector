import { AlertOctagon, LocateFixed } from "lucide-react";
import type { Checkpoint, Diagnostic } from "../types";

type DiagnosticsPanelProps = {
  checkpoints: Checkpoint[];
  selectedCheckpointId?: string;
  onSelectDiagnostic: (diagnostic: Diagnostic) => void;
};

export function DiagnosticsPanel({
  checkpoints,
  selectedCheckpointId,
  onSelectDiagnostic
}: DiagnosticsPanelProps) {
  const diagnostics = firstDiagnosticPerCode(checkpoints.flatMap((checkpoint) => checkpoint.diagnostics));

  return (
    <section className="diagnostics-panel">
      <div className="panel-heading">
        <span>Diagnostics</span>
        <strong>{diagnostics.length} actionable</strong>
      </div>
      <div className="diagnostic-grid">
        {diagnostics.map((diagnostic: Diagnostic) => (
          <button
            className={`diagnostic-card ${diagnostic.severity} ${diagnostic.checkpointId === selectedCheckpointId ? "selected" : ""}`}
            key={diagnostic.id}
            onClick={() => onSelectDiagnostic(diagnostic)}
            type="button"
          >
            <AlertOctagon size={18} />
            <div>
              <div className="diagnostic-title">
                <strong>{diagnostic.code}</strong>
                <code>{diagnostic.node}</code>
              </div>
              <p>{diagnostic.message}</p>
              <div className="diagnostic-evidence">
                <span>
                  <LocateFixed size={13} />
                  checkpoint {shortId(diagnostic.checkpointId)}
                </span>
                {diagnostic.statePath ? <code>{diagnostic.statePath}</code> : null}
                {diagnostic.writeChannel ? <code>write {diagnostic.writeChannel}</code> : null}
              </div>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

function firstDiagnosticPerCode(diagnostics: Diagnostic[]): Diagnostic[] {
  const byCode = new Map<string, Diagnostic>();

  for (const diagnostic of diagnostics) {
    const existing = byCode.get(diagnostic.code);
    if (!existing || preferredDiagnostic(diagnostic, existing)) {
      byCode.set(diagnostic.code, diagnostic);
    }
  }

  return [...byCode.values()].sort((left, right) => severityRank(left) - severityRank(right));
}

function preferredDiagnostic(candidate: Diagnostic, existing: Diagnostic): boolean {
  if (candidate.writeChannel && !existing.writeChannel) return true;
  return false;
}

function severityRank(diagnostic: Diagnostic): number {
  if (diagnostic.severity === "critical") return 0;
  if (diagnostic.severity === "warning") return 1;
  return 2;
}

function shortId(checkpointId: string): string {
  if (checkpointId.length <= 10) return checkpointId;
  return `${checkpointId.slice(0, 8)}...${checkpointId.slice(-4)}`;
}
