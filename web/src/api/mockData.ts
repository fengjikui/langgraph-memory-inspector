import type { CausalChain, Checkpoint, Diagnostic, Summary, Thread, TimelineDiff } from "../types";

export const mockThreads: Thread[] = [
  {
    id: "thread_relocation_demo",
    title: "Relocation Policy Agent",
    namespace: "relocation_policy_agent",
    namespaces: ["relocation_policy_agent", "shadow_replay"],
    namespaceCounts: {
      relocation_policy_agent: 5,
      shadow_replay: 2
    },
    lastNode: "answer_benefits",
    checkpointCount: 7,
    updatedAt: "2026-05-29T10:42:00+08:00",
    diagnosticCount: 1
  },
  {
    id: "thread_clean_baseline",
    title: "Clean baseline run",
    namespace: "relocation_policy_agent",
    namespaces: ["relocation_policy_agent"],
    namespaceCounts: {
      relocation_policy_agent: 4
    },
    lastNode: "answer_benefits",
    checkpointCount: 4,
    updatedAt: "2026-05-29T09:18:00+08:00",
    diagnosticCount: 0
  }
];

const conflictDiagnostic: Diagnostic = {
  id: "diag_conflicting_residence_memory",
  code: "conflicting_residence_memory",
  severity: "critical",
  checkpointId: "ckpt_003_hangzhou_appended",
  node: "extract_profile",
  statePath: "memory_events[type=residence_city]",
  writeChannel: "memory_events",
  suggestedTab: "state",
  title: "Conflicting residence memory",
  message:
    "Two residence memories exist: Shanghai was written first, Hangzhou was appended later, but selected_city still resolves to Shanghai."
};

export const mockCheckpoints: Record<string, Checkpoint[]> = {
  thread_relocation_demo: [
    {
      id: "ckpt_001_start",
      namespace: "relocation_policy_agent",
      ordinal: 1,
      node: "__start__",
      title: "Thread initialized",
      timestamp: "2026-05-29T10:31:12+08:00",
      status: "ok",
      sizeBytes: 4212,
      state: {
        selected_city: "",
        residence_memories: [],
        messages: []
      },
      writes: [],
      diagnostics: []
    },
    {
      id: "ckpt_002_shanghai",
      namespace: "relocation_policy_agent",
      ordinal: 2,
      node: "extract_profile",
      title: "User states Shanghai residence",
      timestamp: "2026-05-29T10:33:05+08:00",
      parentId: "ckpt_001_start",
      status: "ok",
      sizeBytes: 10488,
      state: {
        selected_city: "Shanghai",
        residence_memories: [
          {
            key: "residence_city",
            value: "Shanghai",
            source: "extract_profile",
            createdAt: "2026-05-29T10:33:05+08:00"
          }
        ],
        messages: [{ role: "user", content: "I live in Shanghai." }]
      },
      writes: [
        {
          id: "write_001",
          node: "extract_profile",
          path: "state.residence_memories[0]",
          operation: "append",
          before: [],
          after: { key: "residence_city", value: "Shanghai" },
          timestamp: "2026-05-29T10:33:05+08:00"
        },
        {
          id: "write_002",
          node: "extract_profile",
          path: "state.selected_city",
          operation: "set",
          before: "",
          after: "Shanghai",
          timestamp: "2026-05-29T10:33:05+08:00"
        }
      ],
      diagnostics: []
    },
    {
      id: "ckpt_003_hangzhou_appended",
      namespace: "relocation_policy_agent",
      ordinal: 3,
      node: "extract_profile",
      title: "Move to Hangzhou appended",
      timestamp: "2026-05-29T10:37:44+08:00",
      parentId: "ckpt_002_shanghai",
      status: "diagnostic",
      sizeBytes: 17124,
      state: {
        selected_city: "Shanghai",
        residence_memories: [
          {
            key: "residence_city",
            value: "Shanghai",
            source: "extract_profile",
            createdAt: "2026-05-29T10:33:05+08:00",
            stale: true
          },
          {
            key: "residence_city",
            value: "Hangzhou",
            source: "extract_profile",
            createdAt: "2026-05-29T10:37:44+08:00"
          }
        ],
        messages: [
          { role: "user", content: "I live in Shanghai." },
          { role: "user", content: "I moved to Hangzhou." }
        ]
      },
      writes: [
        {
          id: "write_003",
          node: "extract_profile",
          path: "state.memory_events",
          operation: "append",
          before: [{ key: "residence_city", value: "Shanghai" }],
          after: { key: "residence_city", value: "Hangzhou" },
          timestamp: "2026-05-29T10:37:44+08:00"
        }
      ],
      diagnostics: [conflictDiagnostic]
    },
    {
      id: "ckpt_004_retrieve",
      namespace: "relocation_policy_agent",
      ordinal: 4,
      node: "retrieve_policy_context",
      title: "Retrieval reads stale city",
      timestamp: "2026-05-29T10:40:18+08:00",
      parentId: "ckpt_003_hangzhou_appended",
      status: "diagnostic",
      sizeBytes: 22942,
      state: {
        selected_city: "Shanghai",
        retrieved_city: "Shanghai",
        residence_memories: [
          {
            key: "residence_city",
            value: "Shanghai",
            source: "extract_profile",
            createdAt: "2026-05-29T10:33:05+08:00",
            stale: true
          },
          {
            key: "residence_city",
            value: "Hangzhou",
            source: "extract_profile",
            createdAt: "2026-05-29T10:37:44+08:00"
          }
        ],
        messages: [
          { role: "user", content: "I live in Shanghai." },
          { role: "user", content: "I moved to Hangzhou." },
          { role: "user", content: "Which local benefits should I check first?" }
        ]
      },
      writes: [
        {
          id: "write_004",
          node: "retrieve_policy_context",
          path: "state.retrieved_city",
          operation: "read",
          before: undefined,
          after: "Shanghai",
          timestamp: "2026-05-29T10:40:18+08:00"
        }
      ],
      diagnostics: [conflictDiagnostic]
    },
    {
      id: "ckpt_005_answer",
      namespace: "relocation_policy_agent",
      ordinal: 5,
      node: "answer_benefits",
      title: "Final answer grounded in Shanghai",
      timestamp: "2026-05-29T10:42:00+08:00",
      parentId: "ckpt_004_retrieve",
      status: "diagnostic",
      sizeBytes: 26740,
      state: {
        selected_city: "Shanghai",
        retrieved_city: "Shanghai",
        residence_memories: [
          {
            key: "residence_city",
            value: "Shanghai",
            source: "extract_profile",
            createdAt: "2026-05-29T10:33:05+08:00",
            stale: true
          },
          {
            key: "residence_city",
            value: "Hangzhou",
            source: "extract_profile",
            createdAt: "2026-05-29T10:37:44+08:00"
          }
        ],
        messages: [
          { role: "user", content: "I live in Shanghai." },
          { role: "user", content: "I moved to Hangzhou." },
          { role: "user", content: "Which local benefits should I check first?" },
          {
            role: "assistant",
            content:
              "Start with Shanghai residency-linked benefits and community service programs."
          }
        ],
        answer: "Start with Shanghai residency-linked benefits and community service programs."
      },
      writes: [
        {
          id: "write_005",
          node: "answer_benefits",
          path: "state.answer",
          operation: "set",
          before: undefined,
          after: "Start with Shanghai residency-linked benefits and community service programs.",
          timestamp: "2026-05-29T10:42:00+08:00"
        }
      ],
      diagnostics: [conflictDiagnostic]
    }
  ],
  thread_clean_baseline: []
};

mockCheckpoints.thread_clean_baseline = mockCheckpoints.thread_relocation_demo
  .slice(0, 4)
  .map((checkpoint, index) => ({
    ...checkpoint,
    id: `clean_${index + 1}`,
    status: "ok",
    diagnostics: [],
    state: {
      ...checkpoint.state,
      selected_city: "Hangzhou",
      retrieved_city: index > 2 ? "Hangzhou" : checkpoint.state.retrieved_city,
      residence_memories: [
        {
          key: "residence_city",
          value: "Hangzhou",
          source: "extract_profile",
          createdAt: "2026-05-29T09:11:20+08:00"
        }
      ]
    }
  }));

mockCheckpoints["thread_relocation_demo::relocation_policy_agent"] =
  mockCheckpoints.thread_relocation_demo;

mockCheckpoints["thread_relocation_demo::shadow_replay"] =
  mockCheckpoints.thread_relocation_demo.slice(0, 2).map((checkpoint, index) => ({
    ...checkpoint,
    id: `shadow_${index + 1}`,
    namespace: "shadow_replay",
    title: index === 0 ? "Shadow replay initialized" : "Shadow replay profile check",
    status: "ok",
    diagnostics: [],
    state: {
      ...checkpoint.state,
      selected_city: index === 0 ? "" : "Hangzhou",
      retrieved_city: undefined,
      residence_memories: index === 0 ? [] : [
        {
          key: "residence_city",
          value: "Hangzhou",
          source: "shadow_replay",
          createdAt: "2026-05-29T10:36:00+08:00"
        }
      ]
    },
    writes: []
  }));

export const mockSummary: Summary = {
  databasePath: "examples/relocation_policy_agent/data/checkpoints.sqlite",
  threadCount: mockThreads.length,
  checkpointCount: mockCheckpoints.thread_relocation_demo.length + mockCheckpoints.thread_clean_baseline.length,
  diagnosticsCount: 1,
  adapter: "LangGraph SQLite Checkpointer",
  apiMode: "mock"
};

export const mockDiff: TimelineDiff = {
  fromCheckpointId: "ckpt_002_shanghai",
  toCheckpointId: "ckpt_003_hangzhou_appended",
  summary: "Hangzhou was appended, but selected_city did not change from Shanghai.",
  rows: [
    {
      path: "state.residence_memories[1]",
      before: "(missing)",
      after: "{ key: residence_city, value: Hangzhou }",
      kind: "added"
    },
    {
      path: "state.selected_city",
      before: "Shanghai",
      after: "Shanghai",
      kind: "unchanged"
    },
    {
      path: "diagnostics[0].code",
      before: "(missing)",
      after: "conflicting_residence_memory",
      kind: "added"
    }
  ]
};

export const mockCausalChain: CausalChain = {
  threadId: "thread_relocation_demo",
  checkpointNs: "relocation_policy_agent",
  diagnosticId: "conflicting_residence_memory",
  selectedCheckpointId: "ckpt_003_hangzhou_appended",
  statePaths: ["memory_events[type=residence_city]"],
  writeChannels: ["memory_events"],
  range: {
    fromCheckpointId: "ckpt_001_start",
    toCheckpointId: "ckpt_003_hangzhou_appended",
    scannedCheckpointCount: 3,
    returnedStepCount: 2
  },
  summary: "conflicting_residence_memory is linked to 2 checkpoint step(s) and 2 relevant write(s).",
  steps: [
    {
      checkpointId: "ckpt_002_shanghai",
      checkpointNs: "relocation_policy_agent",
      ordinal: 2,
      node: "extract_profile",
      relation: "related_write",
      statePaths: ["memory_events[type=residence_city]"],
      writeChannels: ["memory_events"],
      updatedChannels: ["memory_events"],
      writes: [
        {
          rowid: 1,
          taskId: "task-profile-1",
          idx: 0,
          channel: "memory_events",
          statePath: "state.memory_events",
          node: "extract_profile",
          valuePreview: "{ key: 'residence_city', value: 'Shanghai' }"
        }
      ],
      statePreview: [
        {
          statePath: "memory_events[type=residence_city]",
          valuePreview: "[{ key: 'residence_city', value: 'Shanghai' }]"
        }
      ]
    },
    {
      checkpointId: "ckpt_003_hangzhou_appended",
      checkpointNs: "relocation_policy_agent",
      ordinal: 3,
      node: "extract_profile",
      relation: "introduced_diagnostic",
      statePaths: ["memory_events[type=residence_city]"],
      writeChannels: ["memory_events"],
      updatedChannels: ["memory_events"],
      writes: [
        {
          rowid: 3,
          taskId: "task-profile-2",
          idx: 0,
          channel: "memory_events",
          statePath: "state.memory_events",
          node: "extract_profile",
          valuePreview: "{ key: 'residence_city', value: 'Hangzhou' }"
        }
      ],
      statePreview: [
        {
          statePath: "memory_events[type=residence_city]",
          valuePreview: "[{ value: 'Shanghai' }, { value: 'Hangzhou' }]"
        }
      ]
    }
  ]
};
