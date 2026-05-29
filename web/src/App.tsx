import { useEffect, useMemo, useState } from "react";
import { inspectorApi } from "./api/client";
import { CheckpointDetail } from "./components/CheckpointDetail";
import { TopChrome } from "./components/Chrome";
import { DiagnosticsPanel } from "./components/DiagnosticsPanel";
import { ThreadSelector } from "./components/ThreadSelector";
import { Timeline } from "./components/Timeline";
import type { Checkpoint, NodeWrite, Summary, Thread, TimelineDiff } from "./types";

type ViewerTab = "state" | "diff" | "writes";

function App() {
  const [summary, setSummary] = useState<Summary>();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<string>();
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<string>();
  const [writes, setWrites] = useState<NodeWrite[]>([]);
  const [diff, setDiff] = useState<TimelineDiff>();
  const [activeTab, setActiveTab] = useState<ViewerTab>("state");

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
          }}
        />
        <div className="center-stack">
          <Timeline
            checkpoints={checkpoints}
            selectedCheckpointId={selectedCheckpointId}
            onSelectCheckpoint={(checkpointId) => {
              setSelectedCheckpointId(checkpointId);
              setActiveTab("state");
            }}
          />
          <DiagnosticsPanel checkpoints={checkpoints} />
        </div>
        <CheckpointDetail
          checkpoint={selectedCheckpoint}
          writes={writes}
          diff={diff}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
      </main>
    </div>
  );
}

export default App;
