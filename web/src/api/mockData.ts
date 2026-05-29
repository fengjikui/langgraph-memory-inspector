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
    diagnosticCount: 2
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

const staleSelectedCityDiagnostic: Diagnostic = {
  id: "diag_stale_selected_city",
  code: "stale_selected_city",
  severity: "critical",
  checkpointId: "ckpt_005_answer",
  node: "retrieve_policy",
  statePath: "selected_city",
  writeChannel: "selected_city",
  suggestedTab: "writes",
  title: "Stale selected city",
  message:
    "Latest residence is Hangzhou, but retrieve_policy keeps selected_city on Shanghai and the final answer uses that stale context."
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
      diagnostics: [conflictDiagnostic, staleSelectedCityDiagnostic]
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
      diagnostics: [conflictDiagnostic, staleSelectedCityDiagnostic]
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
  diagnosticsCount: 2,
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
  headline: "conflicting_residence_memory: extract_profile",
  nodePath: ["extract_profile"],
  nextAction: "Inspect state.memory_events written by extract_profile at checkpoint ckpt_003_hangzhou_appended.",
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
      action: "extract_profile wrote state.memory_events",
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
      action: "extract_profile wrote state.memory_events",
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

export const mockStaleSelectedCityCausalChain: CausalChain = {
  threadId: "thread_relocation_demo",
  checkpointNs: "relocation_policy_agent",
  diagnosticId: "stale_selected_city",
  selectedCheckpointId: "ckpt_005_answer",
  headline: "stale_selected_city: extract_profile -> retrieve_policy -> answer_benefits",
  nodePath: ["extract_profile", "retrieve_policy", "answer_benefits"],
  nextAction: "Inspect state.messages written by answer_benefits at checkpoint ckpt_005_answer.",
  statePaths: ["memory_events[type=residence_city]", "selected_city", "retrieved_docs", "messages"],
  writeChannels: ["memory_events", "selected_city", "retrieved_docs", "messages"],
  range: {
    fromCheckpointId: "ckpt_001_start",
    toCheckpointId: "ckpt_005_answer",
    scannedCheckpointCount: 5,
    returnedStepCount: 4
  },
  summary: "stale_selected_city is linked to 4 checkpoint step(s) and 4 relevant write(s).",
  steps: [
    {
      checkpointId: "ckpt_002_shanghai",
      checkpointNs: "relocation_policy_agent",
      ordinal: 2,
      node: "extract_profile",
      relation: "related_write",
      action: "extract_profile wrote state.memory_events",
      statePaths: ["memory_events[type=residence_city]", "selected_city", "retrieved_docs", "messages"],
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
          valuePreview: "[{ value: 'Shanghai' }]"
        }
      ]
    },
    {
      checkpointId: "ckpt_003_hangzhou_appended",
      checkpointNs: "relocation_policy_agent",
      ordinal: 3,
      node: "extract_profile",
      relation: "related_write",
      action: "extract_profile wrote state.memory_events",
      statePaths: ["memory_events[type=residence_city]", "selected_city", "retrieved_docs", "messages"],
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
    },
    {
      checkpointId: "ckpt_004_retrieve",
      checkpointNs: "relocation_policy_agent",
      ordinal: 4,
      node: "retrieve_policy",
      relation: "introduced_diagnostic",
      action: "retrieve_policy wrote state.selected_city, state.retrieved_docs",
      statePaths: ["memory_events[type=residence_city]", "selected_city", "retrieved_docs", "messages"],
      writeChannels: ["selected_city", "retrieved_docs"],
      updatedChannels: ["selected_city", "retrieved_docs"],
      writes: [
        {
          rowid: 4,
          taskId: "task-retrieve",
          idx: 0,
          channel: "selected_city",
          statePath: "state.selected_city",
          node: "retrieve_policy",
          valuePreview: "Shanghai"
        },
        {
          rowid: 5,
          taskId: "task-retrieve",
          idx: 1,
          channel: "retrieved_docs",
          statePath: "state.retrieved_docs",
          node: "retrieve_policy",
          valuePreview: "[{ city: 'Shanghai', source: 'local_policy_fixture/shanghai' }]"
        }
      ],
      statePreview: [
        {
          statePath: "selected_city",
          valuePreview: "Shanghai"
        }
      ]
    },
    {
      checkpointId: "ckpt_005_answer",
      checkpointNs: "relocation_policy_agent",
      ordinal: 5,
      node: "answer_benefits",
      relation: "selected_checkpoint",
      action: "answer_benefits wrote state.messages",
      statePaths: ["memory_events[type=residence_city]", "selected_city", "retrieved_docs", "messages"],
      writeChannels: ["messages"],
      updatedChannels: ["messages"],
      writes: [
        {
          rowid: 6,
          taskId: "task-answer",
          idx: 0,
          channel: "messages",
          statePath: "state.messages",
          node: "answer_benefits",
          valuePreview: "Start with Shanghai residency-linked benefits..."
        }
      ],
      statePreview: [
        {
          statePath: "messages",
          valuePreview: "assistant answer grounded in Shanghai context"
        }
      ]
    }
  ]
};

export const mockCausalChains: Record<string, CausalChain> = {
  conflicting_residence_memory: mockCausalChain,
  stale_selected_city: mockStaleSelectedCityCausalChain
};
