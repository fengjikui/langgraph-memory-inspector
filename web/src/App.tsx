import { useEffect, useMemo, useState } from "react";
import { inspectorApi } from "./api/client";
import { CheckpointDetail } from "./components/CheckpointDetail";
import { TopChrome } from "./components/Chrome";
import { DiagnosticsPanel } from "./components/DiagnosticsPanel";
import { ThreadSelector } from "./components/ThreadSelector";
import { Timeline } from "./components/Timeline";
import type {
  Checkpoint,
  DebugBundleExportResult,
  Diagnostic,
  NodeWrite,
  Summary,
  Thread,
  TimelineDiff
} from "./types";

type ViewerTab = "state" | "diff" | "writes";
type ExportStatus =
  | { state: "idle" }
  | { state: "exporting" }
  | { state: "success"; result: DebugBundleExportResult }
  | { state: "error"; message: string };

function App() {
  const [summary, setSummary] = useState<Summary>();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<string>();
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<string>();
  const [writes, setWrites] = useState<NodeWrite[]>([]);
  const [diff, setDiff] = useState<TimelineDiff>();
  const [activeTab, setActiveTab] = useState<ViewerTab>("state");
  const [selectedDiagnostic, setSelectedDiagnostic] = useState<Diagnostic>();
  const [exportStatus, setExportStatus] = useState<ExportStatus>({ state: "idle" });

  useEffect(() => {
    async function loadShell() {
      const [nextSummary, nextThreads] = await Promise.all([
        inspectorApi.getSummary(),
        inspectorApi.getThreads()
      ]);
      setSummary(nextSummary);
      setThreads(nextThreads);
      setSelectedThreadId(nextThreads[0]?.id);
    }

    void loadShell();
  }, []);

  useEffect(() => {
    if (!selectedThreadId) return;
    const threadId = selectedThreadId;

    async function loadTimeline() {
      const nextCheckpoints = await inspectorApi.getCheckpoints(threadId);
      setCheckpoints(nextCheckpoints);
      setSelectedCheckpointId(nextCheckpoints[nextCheckpoints.length - 1]?.id);
    }

    void loadTimeline();
  }, [selectedThreadId]);

  useEffect(() => {
    if (!selectedThreadId || !selectedCheckpointId) return;
    const threadId = selectedThreadId;
    const checkpointId = selectedCheckpointId;

    async function loadDetail() {
      const selectedIndex = checkpoints.findIndex((checkpoint) => checkpoint.id === checkpointId);
      const previousCheckpoint = checkpoints[Math.max(selectedIndex - 1, 0)];
      const [nextWrites, nextDiff] = await Promise.all([
        inspectorApi.getWrites(threadId, checkpointId),
        inspectorApi.getDiff(
          threadId,
          previousCheckpoint?.id ?? checkpointId,
          checkpointId
        )
      ]);
      setWrites(nextWrites);
      setDiff(nextDiff);
    }

    void loadDetail();
  }, [checkpoints, selectedCheckpointId, selectedThreadId]);

  const selectedCheckpoint = useMemo(
    () => checkpoints.find((checkpoint) => checkpoint.id === selectedCheckpointId),
    [checkpoints, selectedCheckpointId]
  );

  function selectDiagnostic(diagnostic: Diagnostic) {
    setSelectedDiagnostic(diagnostic);
    setSelectedCheckpointId(diagnostic.checkpointId);
    setActiveTab(diagnostic.writeChannel ? "writes" : diagnostic.suggestedTab ?? "state");
    setExportStatus({ state: "idle" });
  }

  async function exportSelectedCheckpoint() {
    if (!selectedThreadId || !selectedCheckpointId) return;
    setExportStatus({ state: "exporting" });
    try {
      const result = await inspectorApi.exportDebugBundle(selectedThreadId, selectedCheckpointId);
      setExportStatus({ state: "success", result });
    } catch (error) {
      setExportStatus({
        state: "error",
        message: error instanceof Error ? error.message : "Failed to export debug bundle."
      });
    }
  }

  return (
    <div className="app-shell">
      <TopChrome summary={summary} />
      <main className="workspace">
        <ThreadSelector
          threads={threads}
          selectedThreadId={selectedThreadId}
          onSelectThread={(threadId) => {
            setSelectedThreadId(threadId);
            setActiveTab("state");
            setSelectedDiagnostic(undefined);
          }}
        />
        <div className="center-stack">
          <Timeline
            checkpoints={checkpoints}
            selectedCheckpointId={selectedCheckpointId}
            onSelectCheckpoint={(checkpointId) => {
              setSelectedCheckpointId(checkpointId);
              setActiveTab("state");
              setSelectedDiagnostic(undefined);
              setExportStatus({ state: "idle" });
            }}
          />
          <DiagnosticsPanel
            checkpoints={checkpoints}
            selectedCheckpointId={selectedCheckpointId}
            onSelectDiagnostic={selectDiagnostic}
          />
        </div>
        <CheckpointDetail
          checkpoint={selectedCheckpoint}
          writes={writes}
          diff={diff}
          selectedDiagnostic={selectedDiagnostic}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          exportStatus={exportStatus}
          onExportDebugBundle={exportSelectedCheckpoint}
        />
      </main>
    </div>
  );
}

export default App;
