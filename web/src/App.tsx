import { useEffect, useMemo, useState } from "react";
import { inspectorApi } from "./api/client";
import { CheckpointDetail } from "./components/CheckpointDetail";
import { TopChrome } from "./components/Chrome";
import { DiagnosticsPanel } from "./components/DiagnosticsPanel";
import { ThreadSelector } from "./components/ThreadSelector";
import { Timeline } from "./components/Timeline";
import type {
  Checkpoint,
  CausalChain,
  TimelineFilters,
  TimelinePagination,
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

const configuredTimelinePageSize = Number(import.meta.env.VITE_LGMI_TIMELINE_PAGE_SIZE ?? 50);
const TIMELINE_PAGE_SIZE = Number.isFinite(configuredTimelinePageSize)
  ? Math.max(1, configuredTimelinePageSize)
  : 50;

function App() {
  const [summary, setSummary] = useState<Summary>();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [timelinePagination, setTimelinePagination] = useState<TimelinePagination>();
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineFilters, setTimelineFilters] = useState<TimelineFilters>({});
  const [selectedThreadId, setSelectedThreadId] = useState<string>();
  const [selectedNamespace, setSelectedNamespace] = useState<string>();
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<string>();
  const [writes, setWrites] = useState<NodeWrite[]>([]);
  const [diff, setDiff] = useState<TimelineDiff>();
  const [causalChain, setCausalChain] = useState<CausalChain>();
  const [activeTab, setActiveTab] = useState<ViewerTab>("state");
  const [selectedDiagnostic, setSelectedDiagnostic] = useState<Diagnostic>();
  const [exportStatus, setExportStatus] = useState<ExportStatus>({ state: "idle" });
  const [exportRedacted, setExportRedacted] = useState(true);

  useEffect(() => {
    async function loadShell() {
      const [nextSummary, nextThreads] = await Promise.all([
        inspectorApi.getSummary(),
        inspectorApi.getThreads()
      ]);
      setSummary(nextSummary);
      setThreads(nextThreads);
      const firstThread = nextThreads[0];
      setSelectedThreadId(firstThread?.id);
      setSelectedNamespace(firstThread?.namespaces[0]);
    }

    void loadShell();
  }, []);

  useEffect(() => {
    if (!selectedThreadId) return;
    const threadId = selectedThreadId;
    const checkpointNs = selectedNamespace;

    async function loadTimeline() {
      setTimelineLoading(true);
      try {
        const page = await inspectorApi.getCheckpoints(threadId, checkpointNs, {
          limit: TIMELINE_PAGE_SIZE,
          fromEnd: true,
          filters: timelineFilters
        });
        setCheckpoints(page.items);
        setTimelinePagination(page.pagination);
        setSelectedCheckpointId(page.items[page.items.length - 1]?.id);
      } finally {
        setTimelineLoading(false);
      }
    }

    void loadTimeline();
  }, [selectedNamespace, selectedThreadId, timelineFilters]);

  useEffect(() => {
    if (!selectedThreadId || !selectedCheckpointId) return;
    const threadId = selectedThreadId;
    const checkpointId = selectedCheckpointId;
    const checkpointNs = selectedNamespace;

    async function loadDetail() {
      const selectedIndex = checkpoints.findIndex((checkpoint) => checkpoint.id === checkpointId);
      const previousCheckpoint = checkpoints[Math.max(selectedIndex - 1, 0)];
      const [nextWrites, nextDiff] = await Promise.all([
        inspectorApi.getWrites(threadId, checkpointId, checkpointNs),
        inspectorApi.getDiff(
          threadId,
          previousCheckpoint?.id ?? checkpointId,
          checkpointId,
          checkpointNs
        )
      ]);
      setWrites(nextWrites);
      setDiff(nextDiff);
    }

    void loadDetail();
  }, [checkpoints, selectedCheckpointId, selectedNamespace, selectedThreadId]);

  useEffect(() => {
    if (!selectedThreadId || !selectedDiagnostic) {
      setCausalChain(undefined);
      return;
    }
    const threadId = selectedThreadId;
    const checkpointNs = selectedNamespace;
    const diagnostic = selectedDiagnostic;

    async function loadCausalChain() {
      const nextChain = await inspectorApi.getCausalChain(
        threadId,
        diagnostic.checkpointId,
        diagnostic.code,
        checkpointNs
      );
      setCausalChain(nextChain);
    }

    void loadCausalChain();
  }, [selectedDiagnostic, selectedNamespace, selectedThreadId]);

  const selectedCheckpoint = useMemo(
    () => checkpoints.find((checkpoint) => checkpoint.id === selectedCheckpointId),
    [checkpoints, selectedCheckpointId]
  );

  async function loadPreviousTimelinePage() {
    if (!selectedThreadId || timelinePagination?.previousOffset === undefined) return;
    const currentOffset = timelinePagination.previousOffset;
    setTimelineLoading(true);
    try {
      const page = await inspectorApi.getCheckpoints(selectedThreadId, selectedNamespace, {
        limit: TIMELINE_PAGE_SIZE,
        offset: currentOffset,
        filters: timelineFilters
      });
      setCheckpoints((current) => mergeCheckpointPages(page.items, current));
      setTimelinePagination((current) => {
        if (!current) return page.pagination;
        return {
          ...page.pagination,
          returnedCount: page.items.length + current.returnedCount,
          hasNext: current.hasNext,
          nextOffset: current.nextOffset
        };
      });
    } finally {
      setTimelineLoading(false);
    }
  }

  function selectDiagnostic(diagnostic: Diagnostic) {
    setSelectedDiagnostic(diagnostic);
    setCausalChain(undefined);
    setSelectedCheckpointId(diagnostic.checkpointId);
    setActiveTab(diagnostic.writeChannel ? "writes" : diagnostic.suggestedTab ?? "state");
    setExportStatus({ state: "idle" });
  }

  async function exportSelectedCheckpoint() {
    if (!selectedThreadId || !selectedCheckpointId) return;
    setExportStatus({ state: "exporting" });
    try {
      const result = await inspectorApi.exportDebugBundle(
        selectedThreadId,
        selectedCheckpointId,
        selectedNamespace,
        exportRedacted ? "redacted" : "raw"
      );
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
          selectedNamespace={selectedNamespace}
          onSelectThread={(threadId) => {
            const thread = threads.find((item) => item.id === threadId);
            setSelectedThreadId(threadId);
            setSelectedNamespace(thread?.namespaces[0]);
            setActiveTab("state");
            setSelectedDiagnostic(undefined);
            setExportStatus({ state: "idle" });
          }}
          onSelectNamespace={(namespace) => {
            setSelectedNamespace(namespace);
            setActiveTab("state");
            setSelectedDiagnostic(undefined);
            setExportStatus({ state: "idle" });
          }}
        />
        <div className="center-stack">
          <Timeline
            checkpoints={checkpoints}
            pagination={timelinePagination}
            loading={timelineLoading}
            filters={timelineFilters}
            selectedCheckpointId={selectedCheckpointId}
            onLoadPrevious={loadPreviousTimelinePage}
            onFiltersChange={(filters) => {
              setTimelineFilters(filters);
              setActiveTab("state");
              setSelectedDiagnostic(undefined);
              setExportStatus({ state: "idle" });
            }}
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
          causalChain={causalChain}
          selectedDiagnostic={selectedDiagnostic}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          exportStatus={exportStatus}
          exportRedacted={exportRedacted}
          onExportRedactedChange={(enabled) => {
            setExportRedacted(enabled);
            setExportStatus({ state: "idle" });
          }}
          onExportDebugBundle={exportSelectedCheckpoint}
        />
      </main>
    </div>
  );
}

export default App;

function mergeCheckpointPages(previous: Checkpoint[], current: Checkpoint[]): Checkpoint[] {
  const existing = new Set(previous.map((checkpoint) => checkpoint.id));
  return [
    ...previous,
    ...current.filter((checkpoint) => {
      if (existing.has(checkpoint.id)) return false;
      existing.add(checkpoint.id);
      return true;
    })
  ];
}
