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
