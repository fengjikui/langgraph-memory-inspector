import { mockCheckpoints, mockDiff, mockSummary, mockThreads } from "./mockData";
import type { Checkpoint, Diagnostic, Message, NodeWrite, Summary, Thread, TimelineDiff } from "../types";

async function requestJson<T>(path: string): Promise<T | undefined> {
  if (import.meta.env.VITE_LGMI_API_MODE === "mock") {
    return undefined;
  }

  try {
    const response = await fetch(path, {
      headers: { Accept: "application/json" }
    });

    if (!response.ok) {
      return undefined;
    }

    return (await response.json()) as T;
  } catch {
    return undefined;
  }
}

export const inspectorApi = {
  async getSummary(): Promise<Summary> {
    const raw = await requestJson<Record<string, unknown>>("/api/summary");
    return raw ? normalizeSummary(raw) : mockSummary;
  },

  async getThreads(): Promise<Thread[]> {
    const raw = await requestJson<Array<Record<string, unknown>>>("/api/threads");
    return raw ? raw.map(normalizeThread) : mockThreads;
  },

  async getCheckpoints(threadId: string): Promise<Checkpoint[]> {
    const raw = await requestJson<Array<Record<string, unknown>>>(
      `/api/threads/${threadId}/checkpoints`
    );
    if (!raw) return mockCheckpoints[threadId] ?? [];

    const details = await Promise.all(
      raw.map(async (checkpoint) => {
        const checkpointId = String(checkpoint.checkpoint_id ?? "");
        return (
          (await requestJson<Record<string, unknown>>(
            `/api/threads/${threadId}/checkpoints/${checkpointId}`
          )) ?? checkpoint
        );
      })
    );

    return details.map((checkpoint, index) => normalizeCheckpoint(checkpoint, index));
  },

  async getCheckpoint(threadId: string, checkpointId: string): Promise<Checkpoint | undefined> {
    const fallback = mockCheckpoints[threadId]?.find((checkpoint) => checkpoint.id === checkpointId);
    const raw = await requestJson<Record<string, unknown>>(
      `/api/threads/${threadId}/checkpoints/${checkpointId}`
    );
    return raw ? normalizeCheckpoint(raw, Number(raw.rowid ?? 0)) : fallback;
  },

  async getWrites(threadId: string, checkpointId: string): Promise<NodeWrite[]> {
    const fallback =
      mockCheckpoints[threadId]?.find((checkpoint) => checkpoint.id === checkpointId)?.writes ?? [];
    const raw = await requestJson<Array<Record<string, unknown>>>(
      `/api/threads/${threadId}/checkpoints/${checkpointId}/writes`
    );
    return raw ? raw.map(normalizeWrite) : fallback;
  },

  async getDiff(threadId: string, fromCheckpointId: string, toCheckpointId: string): Promise<TimelineDiff> {
    const raw = await requestJson<Record<string, unknown>>(
      `/api/threads/${threadId}/diff?from=${fromCheckpointId}&to=${toCheckpointId}`
    );
    return raw ? normalizeDiff(raw, fromCheckpointId, toCheckpointId) : mockDiff;
  }
};

function normalizeSummary(raw: Record<string, unknown>): Summary {
  return {
    databasePath: String(raw.db_path ?? ""),
    threadCount: Number(raw.thread_count ?? 0),
    checkpointCount: Number(raw.checkpoint_count ?? 0),
    diagnosticsCount: Number(raw.diagnostics_count ?? 0),
    adapter: "SQLite checkpoint adapter",
    apiMode: "live"
  };
}

function normalizeThread(raw: Record<string, unknown>): Thread {
  const latest = asRecord(raw.latest_checkpoint);
  return {
    id: String(raw.thread_id ?? ""),
    title: String(raw.thread_id ?? "").includes("relocation") ? "Relocation Policy Agent" : String(raw.thread_id ?? "Thread"),
    namespace: String(latest?.checkpoint_ns ?? "default"),
    lastNode: inferNodeFromChannels(asStringArray(latest?.updated_channels)),
    checkpointCount: Number(raw.checkpoint_count ?? 0),
    updatedAt: String(latest?.ts ?? new Date().toISOString()),
    diagnosticCount: previewContainsDiagnostic(latest) ? 1 : 0
  };
}

function normalizeCheckpoint(raw: Record<string, unknown>, index: number): Checkpoint {
  const value = asRecord(asRecord(raw.checkpoint)?.value);
  const state = asRecord(value?.channel_values);
  const timestamp = String(raw.ts ?? value?.ts ?? new Date().toISOString());
  const memoryEvents = asArray(state?.memory_events).map(asRecord).filter(Boolean) as Array<Record<string, unknown>>;
  const latestResidence = [...memoryEvents].reverse().find((event) => event.type === "residence_city")?.value;
  const retrievedDocs = asArray(state?.retrieved_docs).map(asRecord).filter(Boolean) as Array<Record<string, unknown>>;
  const selectedCity = String(state?.selected_city ?? "");
  const messages = normalizeMessages(asArray(state?.messages));
  const diagnostics = diagnosticsForState(raw, state, memoryEvents, selectedCity, latestResidence);
  const updatedChannels = asStringArray(raw.updated_channels);

  return {
    id: String(raw.checkpoint_id ?? ""),
    ordinal: index + 1,
    node: inferNodeFromChannels(updatedChannels),
    title: titleForCheckpoint(updatedChannels, state, diagnostics),
    timestamp,
    parentId: raw.parent_checkpoint_id ? String(raw.parent_checkpoint_id) : undefined,
    status: diagnostics.length > 0 ? "diagnostic" : "ok",
    state: {
      selected_city: selectedCity,
      retrieved_city: retrievedDocs[0]?.city ? String(retrievedDocs[0].city) : undefined,
      residence_memories: memoryEvents
        .filter((event) => event.type === "residence_city")
        .map((event, eventIndex) => ({
          key: String(event.type ?? "memory"),
          value: String(event.value ?? ""),
          source: String(event.source ?? "unknown"),
          createdAt: timestamp,
          stale: event.value !== latestResidence || eventIndex < memoryEvents.length - 1
        })),
      messages,
      answer: [...messages].reverse().find((message) => message.role === "assistant")?.content
    },
    writes: [],
    diagnostics,
    sizeBytes: Number(raw.byte_size ?? asRecord(raw.checkpoint)?.byte_size ?? 0)
  };
}

function normalizeWrite(raw: Record<string, unknown>): NodeWrite {
  const decoded = asRecord(raw.value);
  const after = decoded?.value ?? decoded?.preview ?? null;
  const channel = String(raw.channel ?? "state");
  return {
    id: String(raw.rowid ?? `${raw.task_id ?? "task"}-${raw.idx ?? 0}`),
    node: inferNodeFromWrite(channel, after),
    path: `state.${channel}`,
    operation: Array.isArray(after) ? "append" : "set",
    after,
    timestamp: new Date().toISOString()
  };
}

function normalizeDiff(raw: Record<string, unknown>, fromCheckpointId: string, toCheckpointId: string): TimelineDiff {
  const diff = asRecord(raw.diff);
  const changed = asRecord(diff?.changed) ?? {};
  const added = asRecord(diff?.added) ?? {};
  const removed = asRecord(diff?.removed) ?? {};
  const rows = [
    ...Object.entries(added).map(([path, value]) => ({
      path,
      before: "",
      after: stringifyCell(value),
      kind: "added" as const
    })),
    ...Object.entries(changed).map(([path, value]) => {
      const pair = asRecord(value);
      return {
        path,
        before: stringifyCell(pair?.before),
        after: stringifyCell(pair?.after),
        kind: "changed" as const
      };
    }),
    ...Object.entries(removed).map(([path, value]) => ({
      path,
      before: stringifyCell(value),
      after: "",
      kind: "changed" as const
    }))
  ];

  return {
    fromCheckpointId: String(raw.from_checkpoint_id ?? fromCheckpointId),
    toCheckpointId: String(raw.to_checkpoint_id ?? toCheckpointId),
    summary: rows.length > 0 ? `${rows.length} state field changes detected` : "No top-level state changes detected",
    rows
  };
}

function diagnosticsForState(
  raw: Record<string, unknown>,
  state: Record<string, unknown> | undefined,
  memoryEvents: Array<Record<string, unknown>>,
  selectedCity: string,
  latestResidence: unknown
): Diagnostic[] {
  const diagnostics = asStringArray(state?.diagnostics).map((code) => ({
    id: `${String(raw.checkpoint_id ?? "checkpoint")}-${code}`,
    code,
    severity: code.includes("conflicting") ? "critical" as const : "warning" as const,
    checkpointId: String(raw.checkpoint_id ?? ""),
    node: code === "conflicting_residence_memory" ? "extract_profile" : inferNodeFromChannels(asStringArray(raw.updated_channels)),
    statePath: statePathForDiagnostic(code),
    writeChannel: writeChannelForDiagnostic(code),
    suggestedTab: "state" as const,
    title: code.split("_").join(" "),
    message: code === "conflicting_residence_memory"
      ? "Residence memory contains more than one city; retrieval may use stale context."
      : code
  }));

  if (latestResidence && selectedCity && selectedCity !== String(latestResidence)) {
    diagnostics.push({
      id: `${String(raw.checkpoint_id ?? "checkpoint")}-stale-selected-city`,
      code: "stale_selected_city",
      severity: "critical",
      checkpointId: String(raw.checkpoint_id ?? ""),
      node: "retrieve_policy",
      statePath: "selected_city",
      writeChannel: "selected_city",
      suggestedTab: "state",
      title: "stale selected city",
      message: `Latest residence is ${String(latestResidence)}, but selected_city is ${selectedCity}.`
    });
  }

  const residenceValues = new Set(memoryEvents.filter((event) => event.type === "residence_city").map((event) => event.value));
  if (residenceValues.size > 1 && !diagnostics.some((item) => item.code === "conflicting_residence_memory")) {
    diagnostics.push({
      id: `${String(raw.checkpoint_id ?? "checkpoint")}-conflicting-residence`,
      code: "conflicting_residence_memory",
      severity: "critical",
      checkpointId: String(raw.checkpoint_id ?? ""),
      node: "extract_profile",
      statePath: "memory_events[type=residence_city]",
      writeChannel: "memory_events",
      suggestedTab: "state",
      title: "conflicting residence memory",
      message: "Multiple residence_city memories are active at the same time."
    });
  }

  return diagnostics;
}

function statePathForDiagnostic(code: string): string | undefined {
  if (code === "conflicting_residence_memory") return "memory_events[type=residence_city]";
  if (code === "stale_selected_city") return "selected_city";
  if (code === "oversized_message_history") return "messages";
  if (code === "checkpoint_size_spike") return "checkpoint.byte_size";
  return undefined;
}

function writeChannelForDiagnostic(code: string): string | undefined {
  if (code === "conflicting_residence_memory") return "memory_events";
  if (code === "stale_selected_city") return "selected_city";
  if (code === "oversized_message_history") return "messages";
  return undefined;
}

function normalizeMessages(items: unknown[]): Message[] {
  return items.map((item) => {
    const message = messageToRecord(item);
    const type = String(message.type ?? message.role ?? "system");
    return {
      role: type === "human" || type === "user" ? "user" : type === "ai" || type === "assistant" ? "assistant" : "system",
      content: String(message.content ?? "")
    };
  });
}

function messageToRecord(item: unknown): Record<string, unknown> {
  if (Array.isArray(item)) {
    return Object.fromEntries(
      item.filter((pair): pair is [string, unknown] => Array.isArray(pair) && pair.length === 2 && typeof pair[0] === "string")
    );
  }
  return asRecord(item) ?? {};
}

function inferNodeFromChannels(channels: string[]): string {
  if (channels.includes("memory_events")) return "extract_profile";
  if (channels.includes("diagnostics")) return "audit_memory";
  if (channels.includes("retrieved_docs") || channels.includes("selected_city")) return "retrieve_policy";
  if (channels.includes("messages")) return "answer";
  return channels[0] ?? "__start__";
}

function inferNodeFromWrite(channel: string, value: unknown): string {
  if (channel === "memory_events") return "extract_profile";
  if (channel === "diagnostics") return "audit_memory";
  if (channel === "retrieved_docs" || channel === "selected_city") return "retrieve_policy";
  if (channel === "messages" && Array.isArray(value)) return "answer";
  return "unknown";
}

function titleForCheckpoint(channels: string[], state: Record<string, unknown> | undefined, diagnostics: Diagnostic[]): string {
  if (diagnostics.some((item) => item.code === "stale_selected_city")) return "Retrieval reads stale city";
  if (diagnostics.some((item) => item.code === "conflicting_residence_memory")) return "Memory conflict detected";
  if (channels.includes("memory_events")) return "Profile memory updated";
  if (channels.includes("retrieved_docs")) return "Policy context retrieved";
  if (channels.includes("messages") && asArray(state?.messages).length > 0) return "Message state updated";
  return "Checkpoint saved";
}

function previewContainsDiagnostic(raw: Record<string, unknown> | undefined): boolean {
  return String(asRecord(raw?.checkpoint)?.preview ?? "").includes("conflicting_residence_memory");
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : undefined;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asStringArray(value: unknown): string[] {
  return asArray(value).map(String);
}

function stringifyCell(value: unknown): string {
  if (value === undefined || value === null) return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}
