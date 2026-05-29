export type Severity = "info" | "warning" | "critical";

export type Summary = {
  databasePath: string;
  threadCount: number;
  checkpointCount: number;
  diagnosticsCount: number;
  adapter: string;
  apiMode: "live" | "mock";
};

export type Thread = {
  id: string;
  title: string;
  namespace: string;
  namespaces: string[];
  namespaceCounts: Record<string, number>;
  lastNode: string;
  checkpointCount: number;
  updatedAt: string;
  diagnosticCount: number;
};

export type MemoryEntry = {
  key: string;
  value: string;
  source: string;
  createdAt: string;
  stale?: boolean;
};

export type Message = {
  role: "user" | "assistant" | "system";
  content: string;
};

export type Checkpoint = {
  id: string;
  namespace: string;
  ordinal: number;
  node: string;
  title: string;
  timestamp: string;
  parentId?: string;
  status: "ok" | "diagnostic" | "selected";
  state: {
    selected_city: string;
    residence_memories: MemoryEntry[];
    retrieved_city?: string;
    messages: Message[];
    answer?: string;
  };
  writes: NodeWrite[];
  diagnostics: Diagnostic[];
  sizeBytes: number;
};

export type TimelineFilters = {
  diagnostic?: boolean;
  changedPath?: string;
  checkpointIdPrefix?: string;
};

export type TimelinePagination = {
  limit: number;
  offset: number;
  returnedCount: number;
  totalCount: number;
  unfilteredTotalCount: number;
  hasPrevious: boolean;
  hasNext: boolean;
  previousOffset?: number;
  nextOffset?: number;
};

export type CheckpointPage = {
  items: Checkpoint[];
  pagination: TimelinePagination;
};

export type NodeWrite = {
  id: string;
  node: string;
  path: string;
  operation: "append" | "set" | "read";
  before?: unknown;
  after: unknown;
  timestamp: string;
};

export type Diagnostic = {
  id: string;
  code: string;
  severity: Severity;
  checkpointId: string;
  node: string;
  statePath?: string;
  writeChannel?: string;
  suggestedTab?: "state" | "diff" | "writes";
  title: string;
  message: string;
};

export type TimelineDiff = {
  fromCheckpointId: string;
  toCheckpointId: string;
  summary: string;
  rows: Array<{
    path: string;
    before: string;
    after: string;
    kind: "added" | "changed" | "unchanged";
  }>;
};

export type CausalChainWrite = {
  rowid?: number;
  taskId: string;
  idx?: number;
  channel: string;
  statePath: string;
  node: string;
  valuePreview: string;
};

export type CausalChainStep = {
  checkpointId: string;
  checkpointNs: string;
  ordinal: number;
  node: string;
  relation: "related_write" | "introduced_diagnostic" | "selected_checkpoint" | string;
  action: string;
  statePaths: string[];
  writeChannels: string[];
  updatedChannels: string[];
  writes: CausalChainWrite[];
  statePreview: Array<{
    statePath: string;
    valuePreview: string;
  }>;
};

export type CausalChain = {
  threadId: string;
  checkpointNs: string;
  diagnosticId: string;
  selectedCheckpointId: string;
  headline: string;
  nodePath: string[];
  nextAction: string;
  statePaths: string[];
  writeChannels: string[];
  range: {
    fromCheckpointId?: string;
    toCheckpointId: string;
    scannedCheckpointCount: number;
    returnedStepCount: number;
  };
  steps: CausalChainStep[];
  summary: string;
};

export type DebugBundleExportResult = {
  path: string;
  fileSizeBytes: number;
  threadId: string;
  checkpointId: string;
  diagnosticIds: string[];
  redactionMode: "raw" | "redacted";
  redactedPaths: string[];
  redactionCount: number;
};
