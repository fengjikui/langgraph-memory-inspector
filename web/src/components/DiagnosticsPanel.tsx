import { AlertOctagon, Gauge, Split } from "lucide-react";
import type { Checkpoint, Diagnostic } from "../types";

type DiagnosticsPanelProps = {
  checkpoints: Checkpoint[];
};

export function DiagnosticsPanel({ checkpoints }: DiagnosticsPanelProps) {
  const diagnostics = checkpoints.flatMap((checkpoint) => checkpoint.diagnostics);
  const uniqueDiagnostics = diagnostics.filter(
    (diagnostic, index, list) => list.findIndex((item) => item.id === diagnostic.id) === index
  );

  return (
    <section className="diagnostics-panel">
      <div className="panel-heading">
        <span>Diagnostics</span>
        <strong>{uniqueDiagnostics.length} active</strong>
      </div>
      <div className="diagnostic-grid">
        {uniqueDiagnostics.map((diagnostic: Diagnostic) => (
          <article className={`diagnostic-card ${diagnostic.severity}`} key={diagnostic.id}>
            <AlertOctagon size={18} />
            <div>
              <div className="diagnostic-title">
                <strong>{diagnostic.code}</strong>
                <code>{diagnostic.node}</code>
              </div>
              <p>{diagnostic.message}</p>
            </div>
          </article>
        ))}
        <article className="diagnostic-card info">
          <Split size={18} />
          <div>
            <div className="diagnostic-title">
              <strong>node_write_attribution</strong>
              <code>extract_profile</code>
            </div>
            <p>Hangzhou was appended at checkpoint 3 without replacing the Shanghai residence value.</p>
          </div>
        </article>
        <article className="diagnostic-card info">
          <Gauge size={18} />
          <div>
            <div className="diagnostic-title">
              <strong>checkpoint_growth</strong>
              <code>26.1 KB</code>
            </div>
            <p>Message history and profile memories are small in this demo; no size spike detected.</p>
          </div>
        </article>
      </div>
    </section>
  );
}
