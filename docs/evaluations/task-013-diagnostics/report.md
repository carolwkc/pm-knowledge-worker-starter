# Task 013 — AI review and offline support diagnosis

AI judgments on an authored synthetic packet, not human findings, factual truth, representative performance or a release gate. Span containment is mechanical; it does not validate semantic support. Task 012 is observed diagnostic data.

Human judgments are separate and are not read or modified by this command. No human completion is implied and no production policy is changed. Unknown model metadata is recorded as null.

## Bound inputs and AI reviewer

```text
{
  "reviewer_id": "task013-ai-packet-review",
  "provenance": {
    "agent_id": "/root/packet_review",
    "model": null,
    "review_date": "2026-11-18",
    "method": "One delegated AI agent reviewed all 72 selected-policy responses and all twelve original documents against the Task 012 rubric. This artifact transcribes its per-case/mode judgment matrix, rationales and audit spans. No human review, blinding or independent semantic validation is claimed; gold labels were not used as verdicts. Exact model identity was not exposed to the recording agent. Source instructions were treated as untrusted data.",
    "rubric_sha256": "c099daec3ba88785056dafd9efd2cd2df84a95e579e6dd49fcc790105214e55d"
  },
  "manifest_sha256": "f3d139fabc7e8a5adb4a909528d4b0da93258a747cc3a494c59498dabaffe937",
  "ai_review_sha256": "f4d14da0fcea33a1fb25377be5e8fd85f0a79659f66d6afbdfefa61439643c7b",
  "source_hashes": {
    "cases.json": "7308d680dc20f235f26fd9d3694d01c0ea17a9a58a1b499cd90790043116f450",
    "capture.json": "251f7222323ef289feaca219100aab7be8a96f9dc7311bb98fe62ed2282c9d1a",
    "packet.md": "2e3e7f8fc40a0633431989a059ef448d0e2163279c2ab527402fe896d4d59d6c"
  }
}
```

## AI judgment counts

| Mode | Full | Partial | Unsupported | Conflicting | Reviewed |
| --- | ---: | ---: | ---: | ---: | ---: |
| hybrid | 10 | 0 | 8 | 6 | 24 |
| keyword | 10 | 0 | 8 | 6 | 24 |
| semantic | 9 | 1 | 8 | 6 | 24 |
| overall | 29 | 1 | 24 | 18 | 72 |

All verdict counts, uncertainty and denominators are recorded in diagnostics.json. AI full-support rate excludes abstentions and uncertainty; completion is not quality.

```text
{
  "response_status_counts": {
    "grounded": 72
  },
  "finding_counts": {
    "ai_evidence_candidate_gap": 24,
    "unresolved_conflict_grounded": 18,
    "missing_fact_grounded": 18,
    "candidate_gap": 6,
    "ai_evidence_selection_gap": 6,
    "selection_gap": 1
  }
}
```

## Reading the traces

Authored support comes from dataset labels. AI evidence comes from reviewer citations, which can include opposing positions or context rather than support. Candidate ranks are one-based; citation numbers refer to the emitted answer. Each original half-open Unicode codepoint span must be fully contained in a candidate/quotation to count. CRLF counts as two characters and emoji as one. Empty reference lists prove nothing about answerability.

`candidate_gap` and `selection_gap` use authored support spans. Their `ai_evidence_` counterparts use AI-cited spans. A selection gap means a span was retrieved but not emitted; a candidate gap means it is absent from this bounded capture, not the corpus. Grounded-response tags combine the AI verdict with the captured status/category. Findings overlap and must not be summed as disjoint failures.

## Prioritized engineering handoff

### 1. Investigate safe abstention and unresolved-conflict handling

Observed: the linked grounded responses are tagged as AI-reviewed missing facts or unresolved conflicts. Hypothesis: requested-fact and scope checks could improve abstention. Similar words, numbers or currency do not establish the requested fact. Do not resolve policy authority from ranking or treat both-position questions as requests for one authoritative position.

Evidence: [keyword / a37f1bbfbcf5](#item-a37f1bbfbcf5bdc24a5c6d1234745732f93b956e5f9d0dc8574344c08de51519), [keyword / 8259b7f1fce1](#item-8259b7f1fce13c250dea84e7bd34a56e21cad3d1574b5453adca104d73075187), [keyword / 487193401799](#item-487193401799591344a460592bcd4046d7b7c3e85b46758beb1602dd6182f348), [keyword / 59ad05aef99c](#item-59ad05aef99ceb391145654a492115e7b4b16261fc0a3a9dc56097883ac1f24a), [keyword / 3e5c40503c4f](#item-3e5c40503c4f77c31c8578bc09a6315acad4fb04c5bb3e53d491f41c886cb0fb), [keyword / c49e71532746](#item-c49e715327468314b7c85507582da715e80a48b263f5048b98f80c4ab10c0d26), [keyword / 2f90d1b5dfac](#item-2f90d1b5dfacf43c107cdd3dbf290af1f61907342ca3c027bae2968f12cc442d), [keyword / 5d113bfc06bd](#item-5d113bfc06bd4b19fe50506fb0e19081bd1bc8e91fd01680acf69d4837e32091), [keyword / e7261ee3ebfc](#item-e7261ee3ebfc2099f0f75904f6a652973c4917a1e41c7bff2a14c5dab54f3e06), [keyword / 2c563a9eef62](#item-2c563a9eef622d63b811da879b8fd5765938826e9eb8d6ffc75b7b1fd11f7f1c), [keyword / a36b34a3570d](#item-a36b34a3570d316ceae70e9d8b7fab9d473a12fa5166997b4194eece33e9a75b), [keyword / a25bd5b0fdbf](#item-a25bd5b0fdbfa46b2720a54d444c8b1e519e413e33b912cbdd6abf3bf5b58198), [semantic / b3aa3370dfa4](#item-b3aa3370dfa47703f724814aa3d1119936e7136bcaff14ade47751fd267f7658), [semantic / 69dc93197b8e](#item-69dc93197b8ecce5b4680878b1b71590cb8c2e6a43fa85caef639a31c4404299), [semantic / 5282bfd1e39d](#item-5282bfd1e39db3617e6625d11842ab5c313b2592274c9ec6206f3f20863a4b77), [semantic / 35abd4994d7c](#item-35abd4994d7cca216ee2c95fbc070d4ce454b1fe9760ed3b7a0b4c1b3bd156fa), [semantic / 230fa5f716b1](#item-230fa5f716b1331368717f5cbc4431e1c54d30e847f3ceb235c94456afd5aff6), [semantic / 72f357c784d6](#item-72f357c784d63379dbf7be7d30cf27f51cadb743a8699eb8f9b58c3e60d9bac2), [semantic / 2cd6fd23ae8e](#item-2cd6fd23ae8eeef8e84acbd7ab17d89ad84eede281c0aa56a7278554eea51de0), [semantic / 1045aa3a2ee4](#item-1045aa3a2ee4aeaffbe0c1f1b0623ce9312bd0110c062783fd9fbf97222d703f), [semantic / b931b0068492](#item-b931b006849249922a437df91ff0d28aa8464ddace1b249e048c411ac5230d36), [semantic / c41368778458](#item-c413687784584a64d0e7bf087cbcbbde602e14ec6783da48374d3dcdbcb56ebf), [semantic / 220642b7535b](#item-220642b7535bbc5333e8c80bb903eda26ff517fa28725f2e7ea7a66a43ad9c21), [semantic / d32013c37bc9](#item-d32013c37bc9af8b25b786d4e1f545bd050991bfdfc4673deccc26422cce1d2a), [hybrid / c8447b18f4f1](#item-c8447b18f4f1f7a5dfd08db55d7a25adfb1ede4b438976097a06d395fec5246d), [hybrid / 10dbe5412adb](#item-10dbe5412adbb0fbb570d2ff49c5d10808e08d52f87bb977207ee822951e7fb1), [hybrid / 03f863eb0ddb](#item-03f863eb0ddbc17367fa9ea2db149683faed37a8e37177b5714680a4c4b494d4), [hybrid / c7140256a7aa](#item-c7140256a7aab72618dece32e5452f86aa667eb2c2e40ef78635fa30dd2ba23e), [hybrid / 2b4c1943e82d](#item-2b4c1943e82d0d3f3546da930bc1122ff05310b566db151cde66f383c0ec074c), [hybrid / 9bd15f4ecf56](#item-9bd15f4ecf561cff531d08d8001c4f5cb3d7b2e1fd5dd3f62711617053204782), [hybrid / 24404890206a](#item-24404890206ae0c1832563c5167eaf379c0bef39c404588fbdfbf5af12dc7630), [hybrid / 5c803ad82926](#item-5c803ad82926de2988dd5f9c7ac0dbaf995c819c3fde3e59e2973c3cab677df8), [hybrid / d807bd61028d](#item-d807bd61028d6da14f2af19fe6c8bc379ecba8b7abb59c78214a259d391b4ec0), [hybrid / a93d45c49024](#item-a93d45c4902438da8edf306e3c4de19fa92fa53b4969624d9f4406f39dcd1cb5), [hybrid / a8e311858aa1](#item-a8e311858aa1f5e54ac4d528466656b56166fd9f7d92e7d9fa83730309cd9ab4), [hybrid / 76a348fca792](#item-76a348fca7922dcc95d59e7c0bb195220bb9d83f533b4262073edc3f249b1e3c)

### 2. Investigate bounded candidate recall

Observed: at least one authored support span is absent from the bounded candidate set in each linked item. Reranking those candidates cannot recover absent spans. Hypothesis: candidate assembly or ranking changes may recover them; not tested here.

Evidence: [keyword / d90aed83b682](#item-d90aed83b682d0124fd8a0c473713c5a036159c88414d976ef683df5858538be), [keyword / 80dcf934e497](#item-80dcf934e49726cb8eb40963c11e55a839bb5fb3d5a77612de1dbc66800a1608), [semantic / c0b7172e25a6](#item-c0b7172e25a6b9ff11bf8bb9d15dd3da86bd0efddae64df8eec8749a00a4436c), [semantic / 22aa1cc3a02f](#item-22aa1cc3a02f00adcf44655046eba0e0f15a2f435edcb6dde5a801e0e0d4dd20), [hybrid / 048e0e80f3c9](#item-048e0e80f3c9838668487196c7ba6421c09185a2634a815a933b3a54a3f1081b), [hybrid / 62dbbbd05ead](#item-62dbbbd05eada89d7d0c74e7a2d9696d933698caf3adf4cd676fe6d988763804)

### 3. Investigate quotation coverage

Observed: authored support or AI-cited spans reached candidates but were not emitted in the linked items. Candidate ranks and citation lists below expose the exact gap. The frozen selector keeps the first three qualifying unique excerpts using overlap OR cosine; it has no requested-fact or contradiction check. Hypothesis: a coverage objective could help; raising thresholds alone is not established as a fix. Source: `apps/api/src/pmknowledge/answer_selection.py`.

Evidence: [semantic / b3aa3370dfa4](#item-b3aa3370dfa47703f724814aa3d1119936e7136bcaff14ade47751fd267f7658), [semantic / 69dc93197b8e](#item-69dc93197b8ecce5b4680878b1b71590cb8c2e6a43fa85caef639a31c4404299), [semantic / 5282bfd1e39d](#item-5282bfd1e39db3617e6625d11842ab5c313b2592274c9ec6206f3f20863a4b77), [semantic / 35abd4994d7c](#item-35abd4994d7cca216ee2c95fbc070d4ce454b1fe9760ed3b7a0b4c1b3bd156fa), [semantic / 230fa5f716b1](#item-230fa5f716b1331368717f5cbc4431e1c54d30e847f3ceb235c94456afd5aff6), [semantic / 72f357c784d6](#item-72f357c784d63379dbf7be7d30cf27f51cadb743a8699eb8f9b58c3e60d9bac2), [semantic / e735b7c02daf](#item-e735b7c02dafee5ee07f5f40534428e7af1551f420efc77ff1a4f2f65c836ce9)

Successful controls: [keyword / 04dd295edb58](#item-04dd295edb58ee725a13a9456698c6d863c9062ad8b44b43406a2188bd3cce2c), [keyword / e506ffb65ffc](#item-e506ffb65ffc8462326eb6bc473d063c3a5215c7a091ff481674d23ceebc1fd1), [keyword / 5f9e68ac9a31](#item-5f9e68ac9a31549510d39d5624b5005b03b6f217c5b547ce3da8f169a7821ff1), [keyword / bdd202abb106](#item-bdd202abb1060518fc6c55bad8907ebe511e584030add4837167e2908b264c02), [keyword / 472acbe24b21](#item-472acbe24b2105ecb1c18e95d26839bafb3a7f6034293aa2f7c067388fdb2851), [keyword / c9e78e35873d](#item-c9e78e35873d804ac8ec118f0fc484d8050fcdc67ffc691e0fc50ba2c182e34a), [keyword / 50e0516418f4](#item-50e0516418f4ce0ed21c713033015645547c06b08f26d7d1afc534aec26a63a7), [keyword / 80c8205ae214](#item-80c8205ae214aef0363c0267b0332f9cb936f38ce668cedd329addcf9d79a5cb), [keyword / 2ed045e666e3](#item-2ed045e666e34bea4504764442c327a58040bba914054d35f25e13d7c03519d2), [keyword / 9db6b9ee0d4f](#item-9db6b9ee0d4ff5b0ac574b2654faf313c630e09d4952307ed9099401b69950c5), [semantic / 6054045cde41](#item-6054045cde41034fc7758255e1fd157c7b98b545db174eec381589c390160926), [semantic / 1456b2668461](#item-1456b2668461a6d041e7b6340c5e78f08c5dadad0dcd20f9f08f941c31f19db9), [semantic / 423a200042bb](#item-423a200042bbb8d04beb3c9bc128a78fb438c11dd62bd89da004a4787f01a301), [semantic / a8ada7a7a6b8](#item-a8ada7a7a6b897f3370a610dc2e8bef96fac9056a4bb7e286942b6a2cf026d28), [semantic / 8b657eef8030](#item-8b657eef8030905429189f77f9be72d3f7454d292a45016cb1e8fad9ed6fe16f), [semantic / 3c48eeeed307](#item-3c48eeeed307cf93812ad060d59fd496e7a4a707d6e9d96b8ab108429b2e5e9f), [semantic / a1b72658b250](#item-a1b72658b2500590a3083b1a20f2bac36edbdaa484d302e877d5c445e3b3e82c), [semantic / 596b71718260](#item-596b71718260ceb6ba3ac3667744ebbf622275995988a1351bffba78e85bbd3d), [semantic / 94987a3dac33](#item-94987a3dac337fd47a8f7ec3c0d7ce0df03651788ea92a36b2c81e818fb9eb2f), [hybrid / 09e583a99d7c](#item-09e583a99d7c688bd27a89fb521e17451a5b0b5d324b3fb10b9187f477cce77e), [hybrid / e0e6b4b155cd](#item-e0e6b4b155cd2f99cfdcb0a824e2774f92241f2ab85c287d3b53f25cbf9e870d), [hybrid / 6abeaf50118c](#item-6abeaf50118cce6e31bec538ab9b331a4ed13b553ab6cf63c68e5d3ee6b41c1c), [hybrid / 22a647a4c8c6](#item-22a647a4c8c67389b586998623683b3e0a912a31a513d10694d357ade1b22031), [hybrid / bbc142ea42ec](#item-bbc142ea42ec3f7fa575729ffddcdf04e6c6e03d28d82f38f69045e78fe29789), [hybrid / b1315554fe57](#item-b1315554fe57e98a1812ff1a1581161de8c1ce119c43d722160a06aa2a7ae29d), [hybrid / a3ad1a54ff18](#item-a3ad1a54ff18ff3d36a2235d6b205e17f42e365a8a2188600f035e97935c3dbd), [hybrid / 81e13cf8d31a](#item-81e13cf8d31ac7dfc5a54a76de555d337128f45b28579ba48157c4644c0943d7), [hybrid / 7ec8a031cb64](#item-7ec8a031cb646c73ad8a5c2d9cb7efef14e1990009a861c8b99d490d72030754), [hybrid / 7370bdb665d0](#item-7370bdb665d0a82a1a10089430e2c26960060d6b8a4e740e0591fdbfbcdbe971).

Extra irrelevant quotations can coexist with full requested-fact support. A request to report both memo positions differs from a request to resolve which position is authoritative.

Before any production change, test a concrete alternative against fresh frozen validation plus permission/provenance checks. This report runs no experiment or replacement algorithm and claims no effectiveness. One AI reviewer, visible authored corpus and no human agreement measurement limit these findings.

## Item a37f1bbfbcf5bdc24a5c6d1234745732f93b956e5f9d0dc8574344c08de51519

```text
{
  "item_id": "a37f1bbfbcf5bdc24a5c6d1234745732f93b956e5f9d0dc8574344c08de51519",
  "case_id": "review012-conflict-01",
  "mode": "keyword",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for Asterline raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-asterline-a",
        "start_char": 243,
        "end_char": 333
      },
      {
        "document_id": "review012-asterline-b",
        "start_char": 230,
        "end_char": 320
      },
      {
        "document_id": "review012-asterline-b",
        "start_char": 324,
        "end_char": 460
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 243,
      "end_char": 333,
      "text": "For Asterline cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-asterline-b",
      "start_char": 230,
      "end_char": 320,
      "text": "For Asterline cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-asterline-b",
      "start_char": 324,
      "end_char": 460,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 8259b7f1fce13c250dea84e7bd34a56e21cad3d1574b5453adca104d73075187

```text
{
  "item_id": "8259b7f1fce13c250dea84e7bd34a56e21cad3d1574b5453adca104d73075187",
  "case_id": "review012-conflict-02",
  "mode": "keyword",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for Brindleport raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-brindleport-a",
        "start_char": 206,
        "end_char": 298
      },
      {
        "document_id": "review012-brindleport-b",
        "start_char": 225,
        "end_char": 317
      },
      {
        "document_id": "review012-brindleport-b",
        "start_char": 319,
        "end_char": 455
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 206,
      "end_char": 298,
      "text": "For Brindleport cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-brindleport-b",
      "start_char": 225,
      "end_char": 317,
      "text": "For Brindleport cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-brindleport-b",
      "start_char": 319,
      "end_char": 455,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 487193401799591344a460592bcd4046d7b7c3e85b46758beb1602dd6182f348

```text
{
  "item_id": "487193401799591344a460592bcd4046d7b7c3e85b46758beb1602dd6182f348",
  "case_id": "review012-conflict-03",
  "mode": "keyword",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for MallowGrid raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-mallowgrid-a",
        "start_char": 221,
        "end_char": 312
      },
      {
        "document_id": "review012-mallowgrid-b",
        "start_char": 219,
        "end_char": 310
      },
      {
        "document_id": "review012-mallowgrid-b",
        "start_char": 312,
        "end_char": 448
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 221,
      "end_char": 312,
      "text": "For MallowGrid cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-mallowgrid-b",
      "start_char": 219,
      "end_char": 310,
      "text": "For MallowGrid cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-mallowgrid-b",
      "start_char": 312,
      "end_char": 448,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 59ad05aef99ceb391145654a492115e7b4b16261fc0a3a9dc56097883ac1f24a

```text
{
  "item_id": "59ad05aef99ceb391145654a492115e7b4b16261fc0a3a9dc56097883ac1f24a",
  "case_id": "review012-conflict-04",
  "mode": "keyword",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for PipitDock raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-pipitdock-a",
        "start_char": 216,
        "end_char": 306
      },
      {
        "document_id": "review012-pipitdock-b",
        "start_char": 239,
        "end_char": 329
      },
      {
        "document_id": "review012-pipitdock-b",
        "start_char": 331,
        "end_char": 467
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 216,
      "end_char": 306,
      "text": "For PipitDock cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-pipitdock-b",
      "start_char": 239,
      "end_char": 329,
      "text": "For PipitDock cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-pipitdock-b",
      "start_char": 331,
      "end_char": 467,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 3e5c40503c4f77c31c8578bc09a6315acad4fb04c5bb3e53d491f41c886cb0fb

```text
{
  "item_id": "3e5c40503c4f77c31c8578bc09a6315acad4fb04c5bb3e53d491f41c886cb0fb",
  "case_id": "review012-conflict-05",
  "mode": "keyword",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for CobaltNest raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-cobaltnest-a",
        "start_char": 200,
        "end_char": 291
      },
      {
        "document_id": "review012-cobaltnest-b",
        "start_char": 222,
        "end_char": 313
      },
      {
        "document_id": "review012-cobaltnest-b",
        "start_char": 315,
        "end_char": 451
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 200,
      "end_char": 291,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-cobaltnest-b",
      "start_char": 222,
      "end_char": 313,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-cobaltnest-b",
      "start_char": 315,
      "end_char": 451,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item c49e715327468314b7c85507582da715e80a48b263f5048b98f80c4ab10c0d26

```text
{
  "item_id": "c49e715327468314b7c85507582da715e80a48b263f5048b98f80c4ab10c0d26",
  "case_id": "review012-conflict-06",
  "mode": "keyword",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for EmberQuay raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-emberquay-a",
        "start_char": 200,
        "end_char": 290
      },
      {
        "document_id": "review012-emberquay-b",
        "start_char": 214,
        "end_char": 304
      },
      {
        "document_id": "review012-emberquay-b",
        "start_char": 306,
        "end_char": 442
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 200,
      "end_char": 290,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-emberquay-b",
      "start_char": 214,
      "end_char": 304,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-emberquay-b",
      "start_char": 306,
      "end_char": 442,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 04dd295edb58ee725a13a9456698c6d863c9062ad8b44b43406a2188bd3cce2c

```text
{
  "item_id": "04dd295edb58ee725a13a9456698c6d863c9062ad8b44b43406a2188bd3cce2c",
  "case_id": "review012-direct-01",
  "mode": "keyword",
  "category": "direct_support",
  "question": "What is the inspection-lane capacity of one Asterline gateway?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 48 inspection lanes per gateway, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-asterline-a",
        "start_char": 178,
        "end_char": 239
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 178,
      "end_char": 239,
      "text": "The Asterline relay supports 48 inspection lanes per gateway.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 178,
      "end_char": 239,
      "text": "The Asterline relay supports 48 inspection lanes per gateway.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item e506ffb65ffc8462326eb6bc473d063c3a5215c7a091ff481674d23ceebc1fd1

```text
{
  "item_id": "e506ffb65ffc8462326eb6bc473d063c3a5215c7a091ff481674d23ceebc1fd1",
  "case_id": "review012-direct-02",
  "mode": "keyword",
  "category": "direct_support",
  "question": "How many archive slots does a Brindleport pilot team receive?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 125 archive slots per team, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-brindleport-a",
        "start_char": 146,
        "end_char": 204
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 146,
      "end_char": 204,
      "text": "The Brindleport pilot includes 125 archive slots per team.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 146,
      "end_char": 204,
      "text": "The Brindleport pilot includes 125 archive slots per team.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 5f9e68ac9a31549510d39d5624b5005b03b6f217c5b547ce3da8f169a7821ff1

```text
{
  "item_id": "5f9e68ac9a31549510d39d5624b5005b03b6f217c5b547ce3da8f169a7821ff1",
  "case_id": "review012-direct-03",
  "mode": "keyword",
  "category": "direct_support",
  "question": "How many credits per device does the MallowGrid starter bundle cost?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 42 credits per device for the starter bundle, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-mallowgrid-a",
        "start_char": 145,
        "end_char": 219
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 145,
      "end_char": 219,
      "text": "MallowGrid charges 42 credits per device for its synthetic starter bundle.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 145,
      "end_char": 219,
      "text": "MallowGrid charges 42 credits per device for its synthetic starter bundle.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item bdd202abb1060518fc6c55bad8907ebe511e584030add4837167e2908b264c02

```text
{
  "item_id": "bdd202abb1060518fc6c55bad8907ebe511e584030add4837167e2908b264c02",
  "case_id": "review012-direct-04",
  "mode": "keyword",
  "category": "direct_support",
  "question": "When is the PipitDock weekly maintenance window?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 04:15 UTC on Wednesdays, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-pipitdock-a",
        "start_char": 144,
        "end_char": 214
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 144,
      "end_char": 214,
      "text": "PipitDock schedules its maintenance window at 04:15 UTC on Wednesdays.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 144,
      "end_char": 214,
      "text": "PipitDock schedules its maintenance window at 04:15 UTC on Wednesdays.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 472acbe24b2105ecb1c18e95d26839bafb3a7f6034293aa2f7c067388fdb2851

```text
{
  "item_id": "472acbe24b2105ecb1c18e95d26839bafb3a7f6034293aa2f7c067388fdb2851",
  "case_id": "review012-direct-05",
  "mode": "keyword",
  "category": "direct_support",
  "question": "How many concurrent replay jobs can one CobaltNest lab run?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 16 concurrent replay jobs per lab, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-cobaltnest-a",
        "start_char": 145,
        "end_char": 198
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 145,
      "end_char": 198,
      "text": "CobaltNest permits 16 concurrent replay jobs per lab.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 145,
      "end_char": 198,
      "text": "CobaltNest permits 16 concurrent replay jobs per lab.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item c9e78e35873d804ac8ec118f0fc484d8050fcdc67ffc691e0fc50ba2c182e34a

```text
{
  "item_id": "c9e78e35873d804ac8ec118f0fc484d8050fcdc67ffc691e0fc50ba2c182e34a",
  "case_id": "review012-direct-06",
  "mode": "keyword",
  "category": "direct_support",
  "question": "How many synthetic trace samples are in an EmberQuay batch?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 240 synthetic trace samples per batch, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-emberquay-a",
        "start_char": 144,
        "end_char": 198
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 144,
      "end_char": 198,
      "text": "EmberQuay batches contain 240 synthetic trace samples.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 144,
      "end_char": 198,
      "text": "EmberQuay batches contain 240 synthetic trace samples.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 2f90d1b5dfacf43c107cdd3dbf290af1f61907342ca3c027bae2968f12cc442d

```text
{
  "item_id": "2f90d1b5dfacf43c107cdd3dbf290af1f61907342ca3c027bae2968f12cc442d",
  "case_id": "review012-missing-01",
  "mode": "keyword",
  "category": "missing_fact",
  "question": "What is the measured p99 processing latency in milliseconds for Asterline cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No measured p99 processing latency in milliseconds is supplied anywhere in the reviewed corpus. Asterline headers and retention days do not measure processing latency. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item 5d113bfc06bd4b19fe50506fb0e19081bd1bc8e91fd01680acf69d4837e32091

```text
{
  "item_id": "5d113bfc06bd4b19fe50506fb0e19081bd1bc8e91fd01680acf69d4837e32091",
  "case_id": "review012-missing-02",
  "mode": "keyword",
  "category": "missing_fact",
  "question": "What percentage of Brindleport pilot teams completed enrollment in cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No percentage of pilot teams completing enrollment is supplied in the reviewed corpus. Brindleport's 125 archive slots describe capacity, not an enrollment-completion percentage. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item e7261ee3ebfc2099f0f75904f6a652973c4917a1e41c7bff2a14c5dab54f3e06

```text
{
  "item_id": "e7261ee3ebfc2099f0f75904f6a652973c4917a1e41c7bff2a14c5dab54f3e06",
  "case_id": "review012-missing-03",
  "mode": "keyword",
  "category": "missing_fact",
  "question": "What is the annual enterprise subscription price in euros for MallowGrid?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No annual enterprise subscription price in euros is supplied in the reviewed corpus. MallowGrid's starter-bundle price per device in credits differs in product, billing basis and currency. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item 2c563a9eef622d63b811da879b8fd5765938826e9eb8d6ffc75b7b1fd11f7f1c

```text
{
  "item_id": "2c563a9eef622d63b811da879b8fd5765938826e9eb8d6ffc75b7b1fd11f7f1c",
  "case_id": "review012-missing-04",
  "mode": "keyword",
  "category": "missing_fact",
  "question": "How many customer incidents did PipitDock resolve during cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No resolved customer-incident count is supplied in the reviewed corpus. PipitDock's maintenance schedule, retention periods and acknowledgment requirement do not establish such a count. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item a36b34a3570d316ceae70e9d8b7fab9d473a12fa5166997b4194eece33e9a75b

```text
{
  "item_id": "a36b34a3570d316ceae70e9d8b7fab9d473a12fa5166997b4194eece33e9a75b",
  "case_id": "review012-missing-05",
  "mode": "keyword",
  "category": "missing_fact",
  "question": "What is the observed failure rate of CobaltNest replay jobs in cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No observed replay-job failure rate is supplied in the reviewed corpus. CobaltNest's concurrent capacity and declaration prerequisite do not measure failure rate. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item a25bd5b0fdbfa46b2720a54d444c8b1e519e413e33b912cbdd6abf3bf5b58198

```text
{
  "item_id": "a25bd5b0fdbfa46b2720a54d444c8b1e519e413e33b912cbdd6abf3bf5b58198",
  "case_id": "review012-missing-06",
  "mode": "keyword",
  "category": "missing_fact",
  "question": "How many staff-hours did EmberQuay save during cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No staff-hours saved are supplied in the reviewed corpus. EmberQuay's sample counts and retention periods do not quantify labor savings. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item 50e0516418f4ce0ed21c713033015645547c06b08f26d7d1afc534aec26a63a7

```text
{
  "item_id": "50e0516418f4ce0ed21c713033015645547c06b08f26d7d1afc534aec26a63a7",
  "case_id": "review012-multi-01",
  "mode": "keyword",
  "category": "multi_source",
  "question": "What lane capacity and activation requirement apply to an Asterline gateway?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "Displayed quotations explicitly supply both 48 inspection lanes per gateway and a paper calibration card before activation. Both requested facts are supported; the retention-policy disagreement concerns a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-asterline-a",
        "start_char": 178,
        "end_char": 239
      },
      {
        "document_id": "review012-asterline-b",
        "start_char": 151,
        "end_char": 226
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 178,
      "end_char": 239,
      "text": "The Asterline relay supports 48 inspection lanes per gateway.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-asterline-b",
      "start_char": 151,
      "end_char": 226,
      "text": "Each Asterline gateway requires a paper calibration card before activation.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 178,
      "end_char": 239,
      "text": "The Asterline relay supports 48 inspection lanes per gateway.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-asterline-b",
      "start_char": 151,
      "end_char": 226,
      "text": "Each Asterline gateway requires a paper calibration card before activation.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 80c8205ae214aef0363c0267b0332f9cb936f38ce668cedd329addcf9d79a5cb

```text
{
  "item_id": "80c8205ae214aef0363c0267b0332f9cb936f38ce668cedd329addcf9d79a5cb",
  "case_id": "review012-multi-02",
  "mode": "keyword",
  "category": "multi_source",
  "question": "How many archive slots does Brindleport include, and who must a team appoint?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "Displayed quotations explicitly supply both 125 archive slots per team and a named export steward before enrollment. Both requested facts are supported; the retention-policy disagreement concerns a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-brindleport-a",
        "start_char": 146,
        "end_char": 204
      },
      {
        "document_id": "review012-brindleport-b",
        "start_char": 151,
        "end_char": 223
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 146,
      "end_char": 204,
      "text": "The Brindleport pilot includes 125 archive slots per team.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    },
    {
      "document_id": "review012-brindleport-b",
      "start_char": 151,
      "end_char": 223,
      "text": "Brindleport teams must appoint a named export steward before enrollment.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 146,
      "end_char": 204,
      "text": "The Brindleport pilot includes 125 archive slots per team.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    },
    {
      "document_id": "review012-brindleport-b",
      "start_char": 151,
      "end_char": 223,
      "text": "Brindleport teams must appoint a named export steward before enrollment.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    }
  ],
  "findings": []
}
```

## Item 2ed045e666e34bea4504764442c327a58040bba914054d35f25e13d7c03519d2

```text
{
  "item_id": "2ed045e666e34bea4504764442c327a58040bba914054d35f25e13d7c03519d2",
  "case_id": "review012-multi-03",
  "mode": "keyword",
  "category": "multi_source",
  "question": "What does a MallowGrid starter device cost, and what identifier is required?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "Displayed quotations explicitly supply both 42 credits per device for the starter bundle and a verified bench identifier for starter enrollment. Both requested facts are supported; the retention-policy disagreement concerns a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-mallowgrid-a",
        "start_char": 145,
        "end_char": 219
      },
      {
        "document_id": "review012-mallowgrid-b",
        "start_char": 150,
        "end_char": 217
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 145,
      "end_char": 219,
      "text": "MallowGrid charges 42 credits per device for its synthetic starter bundle.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-mallowgrid-b",
      "start_char": 150,
      "end_char": 217,
      "text": "MallowGrid starter enrollment requires a verified bench identifier.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 145,
      "end_char": 219,
      "text": "MallowGrid charges 42 credits per device for its synthetic starter bundle.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-mallowgrid-b",
      "start_char": 150,
      "end_char": 217,
      "text": "MallowGrid starter enrollment requires a verified bench identifier.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 9db6b9ee0d4ff5b0ac574b2654faf313c630e09d4952307ed9099401b69950c5

```text
{
  "item_id": "9db6b9ee0d4ff5b0ac574b2654faf313c630e09d4952307ed9099401b69950c5",
  "case_id": "review012-multi-04",
  "mode": "keyword",
  "category": "multi_source",
  "question": "What maintenance window and escalation acknowledgment does PipitDock require?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "Displayed quotations explicitly supply both 04:15 UTC on Wednesdays and harbor-coordinator acknowledgment of the escalation ticket. Both requested facts are supported; the retention-policy disagreement concerns a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-pipitdock-a",
        "start_char": 144,
        "end_char": 214
      },
      {
        "document_id": "review012-pipitdock-b",
        "start_char": 149,
        "end_char": 237
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 144,
      "end_char": 214,
      "text": "PipitDock schedules its maintenance window at 04:15 UTC on Wednesdays.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-pipitdock-b",
      "start_char": 149,
      "end_char": 237,
      "text": "PipitDock incident escalation requires the harbor coordinator to acknowledge the ticket.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 144,
      "end_char": 214,
      "text": "PipitDock schedules its maintenance window at 04:15 UTC on Wednesdays.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-pipitdock-b",
      "start_char": 149,
      "end_char": 237,
      "text": "PipitDock incident escalation requires the harbor coordinator to acknowledge the ticket.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item d90aed83b682d0124fd8a0c473713c5a036159c88414d976ef683df5858538be

```text
{
  "item_id": "d90aed83b682d0124fd8a0c473713c5a036159c88414d976ef683df5858538be",
  "case_id": "review012-multi-05",
  "mode": "keyword",
  "category": "multi_source",
  "question": "What retention window does each CobaltNest memo specify for cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "Every displayed quotation is a memo header; none gives either requested retention value. The corpus states 30 days in memo A and 90 days in memo B, at the cited undisplayed spans. This question asks what each memo says, so reporting both positions would answer it without resolving authority; the disagreement does not make this a conflicting verdict under the rubric.",
    "evidence_spans": [
      {
        "document_id": "review012-cobaltnest-a",
        "start_char": 200,
        "end_char": 291
      },
      {
        "document_id": "review012-cobaltnest-b",
        "start_char": 222,
        "end_char": 313
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 200,
      "end_char": 291,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-cobaltnest-b",
      "start_char": 222,
      "end_char": 313,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 200,
      "end_char": 291,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-cobaltnest-b",
      "start_char": 222,
      "end_char": 313,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "candidate_gap",
    "ai_evidence_candidate_gap"
  ]
}
```

## Item 80dcf934e49726cb8eb40963c11e55a839bb5fb3d5a77612de1dbc66800a1608

```text
{
  "item_id": "80dcf934e49726cb8eb40963c11e55a839bb5fb3d5a77612de1dbc66800a1608",
  "case_id": "review012-multi-06",
  "mode": "keyword",
  "category": "multi_source",
  "question": "What retention window does each EmberQuay memo specify for cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "Every displayed quotation is a memo header; none gives either requested retention value. The corpus states 30 days in memo A and 90 days in memo B, at the cited undisplayed spans. This question asks what each memo says, so reporting both positions would answer it without resolving authority; the disagreement does not make this a conflicting verdict under the rubric.",
    "evidence_spans": [
      {
        "document_id": "review012-emberquay-a",
        "start_char": 200,
        "end_char": 290
      },
      {
        "document_id": "review012-emberquay-b",
        "start_char": 214,
        "end_char": 304
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 200,
      "end_char": 290,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-emberquay-b",
      "start_char": 214,
      "end_char": 304,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 200,
      "end_char": 290,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-emberquay-b",
      "start_char": 214,
      "end_char": 304,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "candidate_gap",
    "ai_evidence_candidate_gap"
  ]
}
```

## Item b3aa3370dfa47703f724814aa3d1119936e7136bcaff14ade47751fd267f7658

```text
{
  "item_id": "b3aa3370dfa47703f724814aa3d1119936e7136bcaff14ade47751fd267f7658",
  "case_id": "review012-conflict-01",
  "mode": "semantic",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for Asterline raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-asterline-a",
        "start_char": 243,
        "end_char": 333
      },
      {
        "document_id": "review012-asterline-b",
        "start_char": 230,
        "end_char": 320
      },
      {
        "document_id": "review012-asterline-b",
        "start_char": 324,
        "end_char": 460
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 243,
      "end_char": 333,
      "text": "For Asterline cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [
        3
      ],
      "emitted_citations": [
        "3"
      ]
    },
    {
      "document_id": "review012-asterline-b",
      "start_char": 230,
      "end_char": 320,
      "text": "For Asterline cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [
        4
      ],
      "emitted_citations": []
    },
    {
      "document_id": "review012-asterline-b",
      "start_char": 324,
      "end_char": 460,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "ai_evidence_selection_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 69dc93197b8ecce5b4680878b1b71590cb8c2e6a43fa85caef639a31c4404299

```text
{
  "item_id": "69dc93197b8ecce5b4680878b1b71590cb8c2e6a43fa85caef639a31c4404299",
  "case_id": "review012-conflict-02",
  "mode": "semantic",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for Brindleport raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-brindleport-a",
        "start_char": 206,
        "end_char": 298
      },
      {
        "document_id": "review012-brindleport-b",
        "start_char": 225,
        "end_char": 317
      },
      {
        "document_id": "review012-brindleport-b",
        "start_char": 319,
        "end_char": 455
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 206,
      "end_char": 298,
      "text": "For Brindleport cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [
        3
      ],
      "emitted_citations": [
        "3"
      ]
    },
    {
      "document_id": "review012-brindleport-b",
      "start_char": 225,
      "end_char": 317,
      "text": "For Brindleport cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [
        4
      ],
      "emitted_citations": []
    },
    {
      "document_id": "review012-brindleport-b",
      "start_char": 319,
      "end_char": 455,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "ai_evidence_selection_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 5282bfd1e39db3617e6625d11842ab5c313b2592274c9ec6206f3f20863a4b77

```text
{
  "item_id": "5282bfd1e39db3617e6625d11842ab5c313b2592274c9ec6206f3f20863a4b77",
  "case_id": "review012-conflict-03",
  "mode": "semantic",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for MallowGrid raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-mallowgrid-a",
        "start_char": 221,
        "end_char": 312
      },
      {
        "document_id": "review012-mallowgrid-b",
        "start_char": 219,
        "end_char": 310
      },
      {
        "document_id": "review012-mallowgrid-b",
        "start_char": 312,
        "end_char": 448
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 221,
      "end_char": 312,
      "text": "For MallowGrid cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [
        4
      ],
      "emitted_citations": []
    },
    {
      "document_id": "review012-mallowgrid-b",
      "start_char": 219,
      "end_char": 310,
      "text": "For MallowGrid cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [
        3
      ],
      "emitted_citations": [
        "3"
      ]
    },
    {
      "document_id": "review012-mallowgrid-b",
      "start_char": 312,
      "end_char": 448,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "ai_evidence_selection_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 35abd4994d7cca216ee2c95fbc070d4ce454b1fe9760ed3b7a0b4c1b3bd156fa

```text
{
  "item_id": "35abd4994d7cca216ee2c95fbc070d4ce454b1fe9760ed3b7a0b4c1b3bd156fa",
  "case_id": "review012-conflict-04",
  "mode": "semantic",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for PipitDock raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-pipitdock-a",
        "start_char": 216,
        "end_char": 306
      },
      {
        "document_id": "review012-pipitdock-b",
        "start_char": 239,
        "end_char": 329
      },
      {
        "document_id": "review012-pipitdock-b",
        "start_char": 331,
        "end_char": 467
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 216,
      "end_char": 306,
      "text": "For PipitDock cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [
        4
      ],
      "emitted_citations": []
    },
    {
      "document_id": "review012-pipitdock-b",
      "start_char": 239,
      "end_char": 329,
      "text": "For PipitDock cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [
        5
      ],
      "emitted_citations": []
    },
    {
      "document_id": "review012-pipitdock-b",
      "start_char": 331,
      "end_char": 467,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "ai_evidence_selection_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 230fa5f716b1331368717f5cbc4431e1c54d30e847f3ceb235c94456afd5aff6

```text
{
  "item_id": "230fa5f716b1331368717f5cbc4431e1c54d30e847f3ceb235c94456afd5aff6",
  "case_id": "review012-conflict-05",
  "mode": "semantic",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for CobaltNest raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-cobaltnest-a",
        "start_char": 200,
        "end_char": 291
      },
      {
        "document_id": "review012-cobaltnest-b",
        "start_char": 222,
        "end_char": 313
      },
      {
        "document_id": "review012-cobaltnest-b",
        "start_char": 315,
        "end_char": 451
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 200,
      "end_char": 291,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [
        3
      ],
      "emitted_citations": [
        "3"
      ]
    },
    {
      "document_id": "review012-cobaltnest-b",
      "start_char": 222,
      "end_char": 313,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [
        4
      ],
      "emitted_citations": []
    },
    {
      "document_id": "review012-cobaltnest-b",
      "start_char": 315,
      "end_char": 451,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "ai_evidence_selection_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 72f357c784d63379dbf7be7d30cf27f51cadb743a8699eb8f9b58c3e60d9bac2

```text
{
  "item_id": "72f357c784d63379dbf7be7d30cf27f51cadb743a8699eb8f9b58c3e60d9bac2",
  "case_id": "review012-conflict-06",
  "mode": "semantic",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for EmberQuay raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-emberquay-a",
        "start_char": 200,
        "end_char": 290
      },
      {
        "document_id": "review012-emberquay-b",
        "start_char": 214,
        "end_char": 304
      },
      {
        "document_id": "review012-emberquay-b",
        "start_char": 306,
        "end_char": 442
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 200,
      "end_char": 290,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [
        3
      ],
      "emitted_citations": [
        "3"
      ]
    },
    {
      "document_id": "review012-emberquay-b",
      "start_char": 214,
      "end_char": 304,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [
        4
      ],
      "emitted_citations": []
    },
    {
      "document_id": "review012-emberquay-b",
      "start_char": 306,
      "end_char": 442,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "ai_evidence_selection_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 6054045cde41034fc7758255e1fd157c7b98b545db174eec381589c390160926

```text
{
  "item_id": "6054045cde41034fc7758255e1fd157c7b98b545db174eec381589c390160926",
  "case_id": "review012-direct-01",
  "mode": "semantic",
  "category": "direct_support",
  "question": "What is the inspection-lane capacity of one Asterline gateway?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 48 inspection lanes per gateway, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-asterline-a",
        "start_char": 178,
        "end_char": 239
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 178,
      "end_char": 239,
      "text": "The Asterline relay supports 48 inspection lanes per gateway.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 178,
      "end_char": 239,
      "text": "The Asterline relay supports 48 inspection lanes per gateway.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 1456b2668461a6d041e7b6340c5e78f08c5dadad0dcd20f9f08f941c31f19db9

```text
{
  "item_id": "1456b2668461a6d041e7b6340c5e78f08c5dadad0dcd20f9f08f941c31f19db9",
  "case_id": "review012-direct-02",
  "mode": "semantic",
  "category": "direct_support",
  "question": "How many archive slots does a Brindleport pilot team receive?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 125 archive slots per team, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-brindleport-a",
        "start_char": 146,
        "end_char": 204
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 146,
      "end_char": 204,
      "text": "The Brindleport pilot includes 125 archive slots per team.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 146,
      "end_char": 204,
      "text": "The Brindleport pilot includes 125 archive slots per team.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 423a200042bbb8d04beb3c9bc128a78fb438c11dd62bd89da004a4787f01a301

```text
{
  "item_id": "423a200042bbb8d04beb3c9bc128a78fb438c11dd62bd89da004a4787f01a301",
  "case_id": "review012-direct-03",
  "mode": "semantic",
  "category": "direct_support",
  "question": "How many credits per device does the MallowGrid starter bundle cost?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 42 credits per device for the starter bundle, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-mallowgrid-a",
        "start_char": 145,
        "end_char": 219
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 145,
      "end_char": 219,
      "text": "MallowGrid charges 42 credits per device for its synthetic starter bundle.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 145,
      "end_char": 219,
      "text": "MallowGrid charges 42 credits per device for its synthetic starter bundle.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item a8ada7a7a6b897f3370a610dc2e8bef96fac9056a4bb7e286942b6a2cf026d28

```text
{
  "item_id": "a8ada7a7a6b897f3370a610dc2e8bef96fac9056a4bb7e286942b6a2cf026d28",
  "case_id": "review012-direct-04",
  "mode": "semantic",
  "category": "direct_support",
  "question": "When is the PipitDock weekly maintenance window?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 04:15 UTC on Wednesdays, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-pipitdock-a",
        "start_char": 144,
        "end_char": 214
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 144,
      "end_char": 214,
      "text": "PipitDock schedules its maintenance window at 04:15 UTC on Wednesdays.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 144,
      "end_char": 214,
      "text": "PipitDock schedules its maintenance window at 04:15 UTC on Wednesdays.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 8b657eef8030905429189f77f9be72d3f7454d292a45016cb1e8fad9ed6fe16f

```text
{
  "item_id": "8b657eef8030905429189f77f9be72d3f7454d292a45016cb1e8fad9ed6fe16f",
  "case_id": "review012-direct-05",
  "mode": "semantic",
  "category": "direct_support",
  "question": "How many concurrent replay jobs can one CobaltNest lab run?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 16 concurrent replay jobs per lab, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-cobaltnest-a",
        "start_char": 145,
        "end_char": 198
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 145,
      "end_char": 198,
      "text": "CobaltNest permits 16 concurrent replay jobs per lab.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 145,
      "end_char": 198,
      "text": "CobaltNest permits 16 concurrent replay jobs per lab.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 3c48eeeed307cf93812ad060d59fd496e7a4a707d6e9d96b8ab108429b2e5e9f

```text
{
  "item_id": "3c48eeeed307cf93812ad060d59fd496e7a4a707d6e9d96b8ab108429b2e5e9f",
  "case_id": "review012-direct-06",
  "mode": "semantic",
  "category": "direct_support",
  "question": "How many synthetic trace samples are in an EmberQuay batch?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 240 synthetic trace samples per batch, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-emberquay-a",
        "start_char": 144,
        "end_char": 198
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 144,
      "end_char": 198,
      "text": "EmberQuay batches contain 240 synthetic trace samples.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 144,
      "end_char": 198,
      "text": "EmberQuay batches contain 240 synthetic trace samples.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 2cd6fd23ae8eeef8e84acbd7ab17d89ad84eede281c0aa56a7278554eea51de0

```text
{
  "item_id": "2cd6fd23ae8eeef8e84acbd7ab17d89ad84eede281c0aa56a7278554eea51de0",
  "case_id": "review012-missing-01",
  "mode": "semantic",
  "category": "missing_fact",
  "question": "What is the measured p99 processing latency in milliseconds for Asterline cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No measured p99 processing latency in milliseconds is supplied anywhere in the reviewed corpus. Asterline headers and retention days do not measure processing latency. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item 1045aa3a2ee4aeaffbe0c1f1b0623ce9312bd0110c062783fd9fbf97222d703f

```text
{
  "item_id": "1045aa3a2ee4aeaffbe0c1f1b0623ce9312bd0110c062783fd9fbf97222d703f",
  "case_id": "review012-missing-02",
  "mode": "semantic",
  "category": "missing_fact",
  "question": "What percentage of Brindleport pilot teams completed enrollment in cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No percentage of pilot teams completing enrollment is supplied in the reviewed corpus. Brindleport's 125 archive slots describe capacity, not an enrollment-completion percentage. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item b931b006849249922a437df91ff0d28aa8464ddace1b249e048c411ac5230d36

```text
{
  "item_id": "b931b006849249922a437df91ff0d28aa8464ddace1b249e048c411ac5230d36",
  "case_id": "review012-missing-03",
  "mode": "semantic",
  "category": "missing_fact",
  "question": "What is the annual enterprise subscription price in euros for MallowGrid?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No annual enterprise subscription price in euros is supplied in the reviewed corpus. MallowGrid's starter-bundle price per device in credits differs in product, billing basis and currency. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item c413687784584a64d0e7bf087cbcbbde602e14ec6783da48374d3dcdbcb56ebf

```text
{
  "item_id": "c413687784584a64d0e7bf087cbcbbde602e14ec6783da48374d3dcdbcb56ebf",
  "case_id": "review012-missing-04",
  "mode": "semantic",
  "category": "missing_fact",
  "question": "How many customer incidents did PipitDock resolve during cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No resolved customer-incident count is supplied in the reviewed corpus. PipitDock's maintenance schedule, retention periods and acknowledgment requirement do not establish such a count. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item 220642b7535bbc5333e8c80bb903eda26ff517fa28725f2e7ea7a66a43ad9c21

```text
{
  "item_id": "220642b7535bbc5333e8c80bb903eda26ff517fa28725f2e7ea7a66a43ad9c21",
  "case_id": "review012-missing-05",
  "mode": "semantic",
  "category": "missing_fact",
  "question": "What is the observed failure rate of CobaltNest replay jobs in cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No observed replay-job failure rate is supplied in the reviewed corpus. CobaltNest's concurrent capacity and declaration prerequisite do not measure failure rate. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item d32013c37bc9af8b25b786d4e1f545bd050991bfdfc4673deccc26422cce1d2a

```text
{
  "item_id": "d32013c37bc9af8b25b786d4e1f545bd050991bfdfc4673deccc26422cce1d2a",
  "case_id": "review012-missing-06",
  "mode": "semantic",
  "category": "missing_fact",
  "question": "How many staff-hours did EmberQuay save during cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No staff-hours saved are supplied in the reviewed corpus. EmberQuay's sample counts and retention periods do not quantify labor savings. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item a1b72658b2500590a3083b1a20f2bac36edbdaa484d302e877d5c445e3b3e82c

```text
{
  "item_id": "a1b72658b2500590a3083b1a20f2bac36edbdaa484d302e877d5c445e3b3e82c",
  "case_id": "review012-multi-01",
  "mode": "semantic",
  "category": "multi_source",
  "question": "What lane capacity and activation requirement apply to an Asterline gateway?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "Displayed quotations explicitly supply both 48 inspection lanes per gateway and a paper calibration card before activation. Both requested facts are supported; the retention-policy disagreement concerns a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-asterline-a",
        "start_char": 178,
        "end_char": 239
      },
      {
        "document_id": "review012-asterline-b",
        "start_char": 151,
        "end_char": 226
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 178,
      "end_char": 239,
      "text": "The Asterline relay supports 48 inspection lanes per gateway.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-asterline-b",
      "start_char": 151,
      "end_char": 226,
      "text": "Each Asterline gateway requires a paper calibration card before activation.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 178,
      "end_char": 239,
      "text": "The Asterline relay supports 48 inspection lanes per gateway.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-asterline-b",
      "start_char": 151,
      "end_char": 226,
      "text": "Each Asterline gateway requires a paper calibration card before activation.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 596b71718260ceb6ba3ac3667744ebbf622275995988a1351bffba78e85bbd3d

```text
{
  "item_id": "596b71718260ceb6ba3ac3667744ebbf622275995988a1351bffba78e85bbd3d",
  "case_id": "review012-multi-02",
  "mode": "semantic",
  "category": "multi_source",
  "question": "How many archive slots does Brindleport include, and who must a team appoint?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "Displayed quotations explicitly supply both 125 archive slots per team and a named export steward before enrollment. Both requested facts are supported; the retention-policy disagreement concerns a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-brindleport-a",
        "start_char": 146,
        "end_char": 204
      },
      {
        "document_id": "review012-brindleport-b",
        "start_char": 151,
        "end_char": 223
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 146,
      "end_char": 204,
      "text": "The Brindleport pilot includes 125 archive slots per team.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    },
    {
      "document_id": "review012-brindleport-b",
      "start_char": 151,
      "end_char": 223,
      "text": "Brindleport teams must appoint a named export steward before enrollment.",
      "candidate_ranks": [
        3
      ],
      "emitted_citations": [
        "3"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 146,
      "end_char": 204,
      "text": "The Brindleport pilot includes 125 archive slots per team.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    },
    {
      "document_id": "review012-brindleport-b",
      "start_char": 151,
      "end_char": 223,
      "text": "Brindleport teams must appoint a named export steward before enrollment.",
      "candidate_ranks": [
        3
      ],
      "emitted_citations": [
        "3"
      ]
    }
  ],
  "findings": []
}
```

## Item 94987a3dac337fd47a8f7ec3c0d7ce0df03651788ea92a36b2c81e818fb9eb2f

```text
{
  "item_id": "94987a3dac337fd47a8f7ec3c0d7ce0df03651788ea92a36b2c81e818fb9eb2f",
  "case_id": "review012-multi-03",
  "mode": "semantic",
  "category": "multi_source",
  "question": "What does a MallowGrid starter device cost, and what identifier is required?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "Displayed quotations explicitly supply both 42 credits per device for the starter bundle and a verified bench identifier for starter enrollment. Both requested facts are supported; the retention-policy disagreement concerns a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-mallowgrid-a",
        "start_char": 145,
        "end_char": 219
      },
      {
        "document_id": "review012-mallowgrid-b",
        "start_char": 150,
        "end_char": 217
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 145,
      "end_char": 219,
      "text": "MallowGrid charges 42 credits per device for its synthetic starter bundle.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-mallowgrid-b",
      "start_char": 150,
      "end_char": 217,
      "text": "MallowGrid starter enrollment requires a verified bench identifier.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 145,
      "end_char": 219,
      "text": "MallowGrid charges 42 credits per device for its synthetic starter bundle.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-mallowgrid-b",
      "start_char": 150,
      "end_char": 217,
      "text": "MallowGrid starter enrollment requires a verified bench identifier.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item e735b7c02dafee5ee07f5f40534428e7af1551f420efc77ff1a4f2f65c836ce9

```text
{
  "item_id": "e735b7c02dafee5ee07f5f40534428e7af1551f420efc77ff1a4f2f65c836ce9",
  "case_id": "review012-multi-04",
  "mode": "semantic",
  "category": "multi_source",
  "question": "What maintenance window and escalation acknowledgment does PipitDock require?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "partially_supported",
    "rationale": "The displayed maintenance quotation supports 04:15 UTC on Wednesdays, but no displayed quotation supplies PipitDock's escalation acknowledgment. A header and unrelated EmberQuay checksum requirement cannot fill that gap. The original PipitDock memo B contains the missing harbor-coordinator acknowledgment.",
    "evidence_spans": [
      {
        "document_id": "review012-pipitdock-a",
        "start_char": 144,
        "end_char": 214
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 144,
      "end_char": 214,
      "text": "PipitDock schedules its maintenance window at 04:15 UTC on Wednesdays.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    },
    {
      "document_id": "review012-pipitdock-b",
      "start_char": 149,
      "end_char": 237,
      "text": "PipitDock incident escalation requires the harbor coordinator to acknowledge the ticket.",
      "candidate_ranks": [
        5
      ],
      "emitted_citations": []
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 144,
      "end_char": 214,
      "text": "PipitDock schedules its maintenance window at 04:15 UTC on Wednesdays.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": [
    "selection_gap"
  ]
}
```

## Item c0b7172e25a6b9ff11bf8bb9d15dd3da86bd0efddae64df8eec8749a00a4436c

```text
{
  "item_id": "c0b7172e25a6b9ff11bf8bb9d15dd3da86bd0efddae64df8eec8749a00a4436c",
  "case_id": "review012-multi-05",
  "mode": "semantic",
  "category": "multi_source",
  "question": "What retention window does each CobaltNest memo specify for cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "Every displayed quotation is a memo header; none gives either requested retention value. The corpus states 30 days in memo A and 90 days in memo B, at the cited undisplayed spans. This question asks what each memo says, so reporting both positions would answer it without resolving authority; the disagreement does not make this a conflicting verdict under the rubric.",
    "evidence_spans": [
      {
        "document_id": "review012-cobaltnest-a",
        "start_char": 200,
        "end_char": 291
      },
      {
        "document_id": "review012-cobaltnest-b",
        "start_char": 222,
        "end_char": 313
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 200,
      "end_char": 291,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-cobaltnest-b",
      "start_char": 222,
      "end_char": 313,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 200,
      "end_char": 291,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-cobaltnest-b",
      "start_char": 222,
      "end_char": 313,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "candidate_gap",
    "ai_evidence_candidate_gap"
  ]
}
```

## Item 22aa1cc3a02f00adcf44655046eba0e0f15a2f435edcb6dde5a801e0e0d4dd20

```text
{
  "item_id": "22aa1cc3a02f00adcf44655046eba0e0f15a2f435edcb6dde5a801e0e0d4dd20",
  "case_id": "review012-multi-06",
  "mode": "semantic",
  "category": "multi_source",
  "question": "What retention window does each EmberQuay memo specify for cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "Every displayed quotation is a memo header; none gives either requested retention value. The corpus states 30 days in memo A and 90 days in memo B, at the cited undisplayed spans. This question asks what each memo says, so reporting both positions would answer it without resolving authority; the disagreement does not make this a conflicting verdict under the rubric.",
    "evidence_spans": [
      {
        "document_id": "review012-emberquay-a",
        "start_char": 200,
        "end_char": 290
      },
      {
        "document_id": "review012-emberquay-b",
        "start_char": 214,
        "end_char": 304
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 200,
      "end_char": 290,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-emberquay-b",
      "start_char": 214,
      "end_char": 304,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 200,
      "end_char": 290,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-emberquay-b",
      "start_char": 214,
      "end_char": 304,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "candidate_gap",
    "ai_evidence_candidate_gap"
  ]
}
```

## Item c8447b18f4f1f7a5dfd08db55d7a25adfb1ede4b438976097a06d395fec5246d

```text
{
  "item_id": "c8447b18f4f1f7a5dfd08db55d7a25adfb1ede4b438976097a06d395fec5246d",
  "case_id": "review012-conflict-01",
  "mode": "hybrid",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for Asterline raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-asterline-a",
        "start_char": 243,
        "end_char": 333
      },
      {
        "document_id": "review012-asterline-b",
        "start_char": 230,
        "end_char": 320
      },
      {
        "document_id": "review012-asterline-b",
        "start_char": 324,
        "end_char": 460
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 243,
      "end_char": 333,
      "text": "For Asterline cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-asterline-b",
      "start_char": 230,
      "end_char": 320,
      "text": "For Asterline cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-asterline-b",
      "start_char": 324,
      "end_char": 460,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 10dbe5412adbb0fbb570d2ff49c5d10808e08d52f87bb977207ee822951e7fb1

```text
{
  "item_id": "10dbe5412adbb0fbb570d2ff49c5d10808e08d52f87bb977207ee822951e7fb1",
  "case_id": "review012-conflict-02",
  "mode": "hybrid",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for Brindleport raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-brindleport-a",
        "start_char": 206,
        "end_char": 298
      },
      {
        "document_id": "review012-brindleport-b",
        "start_char": 225,
        "end_char": 317
      },
      {
        "document_id": "review012-brindleport-b",
        "start_char": 319,
        "end_char": 455
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 206,
      "end_char": 298,
      "text": "For Brindleport cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-brindleport-b",
      "start_char": 225,
      "end_char": 317,
      "text": "For Brindleport cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-brindleport-b",
      "start_char": 319,
      "end_char": 455,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 03f863eb0ddbc17367fa9ea2db149683faed37a8e37177b5714680a4c4b494d4

```text
{
  "item_id": "03f863eb0ddbc17367fa9ea2db149683faed37a8e37177b5714680a4c4b494d4",
  "case_id": "review012-conflict-03",
  "mode": "hybrid",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for MallowGrid raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-mallowgrid-a",
        "start_char": 221,
        "end_char": 312
      },
      {
        "document_id": "review012-mallowgrid-b",
        "start_char": 219,
        "end_char": 310
      },
      {
        "document_id": "review012-mallowgrid-b",
        "start_char": 312,
        "end_char": 448
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 221,
      "end_char": 312,
      "text": "For MallowGrid cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-mallowgrid-b",
      "start_char": 219,
      "end_char": 310,
      "text": "For MallowGrid cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-mallowgrid-b",
      "start_char": 312,
      "end_char": 448,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item c7140256a7aab72618dece32e5452f86aa667eb2c2e40ef78635fa30dd2ba23e

```text
{
  "item_id": "c7140256a7aab72618dece32e5452f86aa667eb2c2e40ef78635fa30dd2ba23e",
  "case_id": "review012-conflict-04",
  "mode": "hybrid",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for PipitDock raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-pipitdock-a",
        "start_char": 216,
        "end_char": 306
      },
      {
        "document_id": "review012-pipitdock-b",
        "start_char": 239,
        "end_char": 329
      },
      {
        "document_id": "review012-pipitdock-b",
        "start_char": 331,
        "end_char": 467
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 216,
      "end_char": 306,
      "text": "For PipitDock cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-pipitdock-b",
      "start_char": 239,
      "end_char": 329,
      "text": "For PipitDock cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-pipitdock-b",
      "start_char": 331,
      "end_char": 467,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 2b4c1943e82d0d3f3546da930bc1122ff05310b566db151cde66f383c0ec074c

```text
{
  "item_id": "2b4c1943e82d0d3f3546da930bc1122ff05310b566db151cde66f383c0ec074c",
  "case_id": "review012-conflict-05",
  "mode": "hybrid",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for CobaltNest raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-cobaltnest-a",
        "start_char": 200,
        "end_char": 291
      },
      {
        "document_id": "review012-cobaltnest-b",
        "start_char": 222,
        "end_char": 313
      },
      {
        "document_id": "review012-cobaltnest-b",
        "start_char": 315,
        "end_char": 451
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 200,
      "end_char": 291,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-cobaltnest-b",
      "start_char": 222,
      "end_char": 313,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-cobaltnest-b",
      "start_char": 315,
      "end_char": 451,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 9bd15f4ecf561cff531d08d8001c4f5cb3d7b2e1fd5dd3f62711617053204782

```text
{
  "item_id": "9bd15f4ecf561cff531d08d8001c4f5cb3d7b2e1fd5dd3f62711617053204782",
  "case_id": "review012-conflict-06",
  "mode": "hybrid",
  "category": "conflict_resolution",
  "question": "Which single retention window is authoritative for EmberQuay raw inspection events in the team vault during cycle R12, and what resolves the two memos?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "conflicting",
    "rationale": "The same cycle R12, raw inspection events and team-vault scope has opposing 30-day and 90-day policies in memos A and B. The corpus explicitly gives the memos equal standing and records no reconciliation. It cannot establish the requested single authoritative window or resolution. The rubric requires a conflicting verdict even when opposing positions are omitted from the displayed quotations.",
    "evidence_spans": [
      {
        "document_id": "review012-emberquay-a",
        "start_char": 200,
        "end_char": 290
      },
      {
        "document_id": "review012-emberquay-b",
        "start_char": 214,
        "end_char": 304
      },
      {
        "document_id": "review012-emberquay-b",
        "start_char": 306,
        "end_char": 442
      }
    ]
  },
  "authored_support": [],
  "ai_evidence": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 200,
      "end_char": 290,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-emberquay-b",
      "start_char": 214,
      "end_char": 304,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-emberquay-b",
      "start_char": 306,
      "end_char": 442,
      "text": "The two memos have equal standing; neither establishes precedence or a superseding policy. No reconciliation is recorded in this corpus.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "ai_evidence_candidate_gap",
    "unresolved_conflict_grounded"
  ]
}
```

## Item 09e583a99d7c688bd27a89fb521e17451a5b0b5d324b3fb10b9187f477cce77e

```text
{
  "item_id": "09e583a99d7c688bd27a89fb521e17451a5b0b5d324b3fb10b9187f477cce77e",
  "case_id": "review012-direct-01",
  "mode": "hybrid",
  "category": "direct_support",
  "question": "What is the inspection-lane capacity of one Asterline gateway?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 48 inspection lanes per gateway, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-asterline-a",
        "start_char": 178,
        "end_char": 239
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 178,
      "end_char": 239,
      "text": "The Asterline relay supports 48 inspection lanes per gateway.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 178,
      "end_char": 239,
      "text": "The Asterline relay supports 48 inspection lanes per gateway.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item e0e6b4b155cd2f99cfdcb0a824e2774f92241f2ab85c287d3b53f25cbf9e870d

```text
{
  "item_id": "e0e6b4b155cd2f99cfdcb0a824e2774f92241f2ab85c287d3b53f25cbf9e870d",
  "case_id": "review012-direct-02",
  "mode": "hybrid",
  "category": "direct_support",
  "question": "How many archive slots does a Brindleport pilot team receive?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 125 archive slots per team, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-brindleport-a",
        "start_char": 146,
        "end_char": 204
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 146,
      "end_char": 204,
      "text": "The Brindleport pilot includes 125 archive slots per team.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 146,
      "end_char": 204,
      "text": "The Brindleport pilot includes 125 archive slots per team.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 6abeaf50118cce6e31bec538ab9b331a4ed13b553ab6cf63c68e5d3ee6b41c1c

```text
{
  "item_id": "6abeaf50118cce6e31bec538ab9b331a4ed13b553ab6cf63c68e5d3ee6b41c1c",
  "case_id": "review012-direct-03",
  "mode": "hybrid",
  "category": "direct_support",
  "question": "How many credits per device does the MallowGrid starter bundle cost?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 42 credits per device for the starter bundle, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-mallowgrid-a",
        "start_char": 145,
        "end_char": 219
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 145,
      "end_char": 219,
      "text": "MallowGrid charges 42 credits per device for its synthetic starter bundle.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 145,
      "end_char": 219,
      "text": "MallowGrid charges 42 credits per device for its synthetic starter bundle.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 22a647a4c8c67389b586998623683b3e0a912a31a513d10694d357ade1b22031

```text
{
  "item_id": "22a647a4c8c67389b586998623683b3e0a912a31a513d10694d357ade1b22031",
  "case_id": "review012-direct-04",
  "mode": "hybrid",
  "category": "direct_support",
  "question": "When is the PipitDock weekly maintenance window?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 04:15 UTC on Wednesdays, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-pipitdock-a",
        "start_char": 144,
        "end_char": 214
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 144,
      "end_char": 214,
      "text": "PipitDock schedules its maintenance window at 04:15 UTC on Wednesdays.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 144,
      "end_char": 214,
      "text": "PipitDock schedules its maintenance window at 04:15 UTC on Wednesdays.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item bbc142ea42ec3f7fa575729ffddcdf04e6c6e03d28d82f38f69045e78fe29789

```text
{
  "item_id": "bbc142ea42ec3f7fa575729ffddcdf04e6c6e03d28d82f38f69045e78fe29789",
  "case_id": "review012-direct-05",
  "mode": "hybrid",
  "category": "direct_support",
  "question": "How many concurrent replay jobs can one CobaltNest lab run?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 16 concurrent replay jobs per lab, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-cobaltnest-a",
        "start_char": 145,
        "end_char": 198
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 145,
      "end_char": 198,
      "text": "CobaltNest permits 16 concurrent replay jobs per lab.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 145,
      "end_char": 198,
      "text": "CobaltNest permits 16 concurrent replay jobs per lab.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item b1315554fe57e98a1812ff1a1581161de8c1ce119c43d722160a06aa2a7ae29d

```text
{
  "item_id": "b1315554fe57e98a1812ff1a1581161de8c1ce119c43d722160a06aa2a7ae29d",
  "case_id": "review012-direct-06",
  "mode": "hybrid",
  "category": "direct_support",
  "question": "How many synthetic trace samples are in an EmberQuay batch?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "The displayed quotation explicitly states 240 synthetic trace samples per batch, answering the requested fact. Extra quotations do not remove that support. Retention disagreements concern a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-emberquay-a",
        "start_char": 144,
        "end_char": 198
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 144,
      "end_char": 198,
      "text": "EmberQuay batches contain 240 synthetic trace samples.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 144,
      "end_char": 198,
      "text": "EmberQuay batches contain 240 synthetic trace samples.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 24404890206ae0c1832563c5167eaf379c0bef39c404588fbdfbf5af12dc7630

```text
{
  "item_id": "24404890206ae0c1832563c5167eaf379c0bef39c404588fbdfbf5af12dc7630",
  "case_id": "review012-missing-01",
  "mode": "hybrid",
  "category": "missing_fact",
  "question": "What is the measured p99 processing latency in milliseconds for Asterline cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No measured p99 processing latency in milliseconds is supplied anywhere in the reviewed corpus. Asterline headers and retention days do not measure processing latency. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item 5c803ad82926de2988dd5f9c7ac0dbaf995c819c3fde3e59e2973c3cab677df8

```text
{
  "item_id": "5c803ad82926de2988dd5f9c7ac0dbaf995c819c3fde3e59e2973c3cab677df8",
  "case_id": "review012-missing-02",
  "mode": "hybrid",
  "category": "missing_fact",
  "question": "What percentage of Brindleport pilot teams completed enrollment in cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No percentage of pilot teams completing enrollment is supplied in the reviewed corpus. Brindleport's 125 archive slots describe capacity, not an enrollment-completion percentage. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item d807bd61028d6da14f2af19fe6c8bc379ecba8b7abb59c78214a259d391b4ec0

```text
{
  "item_id": "d807bd61028d6da14f2af19fe6c8bc379ecba8b7abb59c78214a259d391b4ec0",
  "case_id": "review012-missing-03",
  "mode": "hybrid",
  "category": "missing_fact",
  "question": "What is the annual enterprise subscription price in euros for MallowGrid?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No annual enterprise subscription price in euros is supplied in the reviewed corpus. MallowGrid's starter-bundle price per device in credits differs in product, billing basis and currency. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item a93d45c4902438da8edf306e3c4de19fa92fa53b4969624d9f4406f39dcd1cb5

```text
{
  "item_id": "a93d45c4902438da8edf306e3c4de19fa92fa53b4969624d9f4406f39dcd1cb5",
  "case_id": "review012-missing-04",
  "mode": "hybrid",
  "category": "missing_fact",
  "question": "How many customer incidents did PipitDock resolve during cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No resolved customer-incident count is supplied in the reviewed corpus. PipitDock's maintenance schedule, retention periods and acknowledgment requirement do not establish such a count. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item a8e311858aa1f5e54ac4d528466656b56166fd9f7d92e7d9fa83730309cd9ab4

```text
{
  "item_id": "a8e311858aa1f5e54ac4d528466656b56166fd9f7d92e7d9fa83730309cd9ab4",
  "case_id": "review012-missing-05",
  "mode": "hybrid",
  "category": "missing_fact",
  "question": "What is the observed failure rate of CobaltNest replay jobs in cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No observed replay-job failure rate is supplied in the reviewed corpus. CobaltNest's concurrent capacity and declaration prerequisite do not measure failure rate. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item 76a348fca7922dcc95d59e7c0bb195220bb9d83f533b4262073edc3f249b1e3c

```text
{
  "item_id": "76a348fca7922dcc95d59e7c0bb195220bb9d83f533b4262073edc3f249b1e3c",
  "case_id": "review012-missing-06",
  "mode": "hybrid",
  "category": "missing_fact",
  "question": "How many staff-hours did EmberQuay save during cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "No staff-hours saved are supplied in the reviewed corpus. EmberQuay's sample counts and retention periods do not quantify labor savings. The response is grounded quotations, not an abstention. Absence here is limited to this supplied corpus, not global absence.",
    "evidence_spans": []
  },
  "authored_support": [],
  "ai_evidence": [],
  "findings": [
    "missing_fact_grounded"
  ]
}
```

## Item a3ad1a54ff18ff3d36a2235d6b205e17f42e365a8a2188600f035e97935c3dbd

```text
{
  "item_id": "a3ad1a54ff18ff3d36a2235d6b205e17f42e365a8a2188600f035e97935c3dbd",
  "case_id": "review012-multi-01",
  "mode": "hybrid",
  "category": "multi_source",
  "question": "What lane capacity and activation requirement apply to an Asterline gateway?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "Displayed quotations explicitly supply both 48 inspection lanes per gateway and a paper calibration card before activation. Both requested facts are supported; the retention-policy disagreement concerns a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-asterline-a",
        "start_char": 178,
        "end_char": 239
      },
      {
        "document_id": "review012-asterline-b",
        "start_char": 151,
        "end_char": 226
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 178,
      "end_char": 239,
      "text": "The Asterline relay supports 48 inspection lanes per gateway.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-asterline-b",
      "start_char": 151,
      "end_char": 226,
      "text": "Each Asterline gateway requires a paper calibration card before activation.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-asterline-a",
      "start_char": 178,
      "end_char": 239,
      "text": "The Asterline relay supports 48 inspection lanes per gateway.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-asterline-b",
      "start_char": 151,
      "end_char": 226,
      "text": "Each Asterline gateway requires a paper calibration card before activation.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 81e13cf8d31ac7dfc5a54a76de555d337128f45b28579ba48157c4644c0943d7

```text
{
  "item_id": "81e13cf8d31ac7dfc5a54a76de555d337128f45b28579ba48157c4644c0943d7",
  "case_id": "review012-multi-02",
  "mode": "hybrid",
  "category": "multi_source",
  "question": "How many archive slots does Brindleport include, and who must a team appoint?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "Displayed quotations explicitly supply both 125 archive slots per team and a named export steward before enrollment. Both requested facts are supported; the retention-policy disagreement concerns a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-brindleport-a",
        "start_char": 146,
        "end_char": 204
      },
      {
        "document_id": "review012-brindleport-b",
        "start_char": 151,
        "end_char": 223
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 146,
      "end_char": 204,
      "text": "The Brindleport pilot includes 125 archive slots per team.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    },
    {
      "document_id": "review012-brindleport-b",
      "start_char": 151,
      "end_char": 223,
      "text": "Brindleport teams must appoint a named export steward before enrollment.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-brindleport-a",
      "start_char": 146,
      "end_char": 204,
      "text": "The Brindleport pilot includes 125 archive slots per team.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    },
    {
      "document_id": "review012-brindleport-b",
      "start_char": 151,
      "end_char": 223,
      "text": "Brindleport teams must appoint a named export steward before enrollment.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    }
  ],
  "findings": []
}
```

## Item 7ec8a031cb646c73ad8a5c2d9cb7efef14e1990009a861c8b99d490d72030754

```text
{
  "item_id": "7ec8a031cb646c73ad8a5c2d9cb7efef14e1990009a861c8b99d490d72030754",
  "case_id": "review012-multi-03",
  "mode": "hybrid",
  "category": "multi_source",
  "question": "What does a MallowGrid starter device cost, and what identifier is required?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "Displayed quotations explicitly supply both 42 credits per device for the starter bundle and a verified bench identifier for starter enrollment. Both requested facts are supported; the retention-policy disagreement concerns a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-mallowgrid-a",
        "start_char": 145,
        "end_char": 219
      },
      {
        "document_id": "review012-mallowgrid-b",
        "start_char": 150,
        "end_char": 217
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 145,
      "end_char": 219,
      "text": "MallowGrid charges 42 credits per device for its synthetic starter bundle.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-mallowgrid-b",
      "start_char": 150,
      "end_char": 217,
      "text": "MallowGrid starter enrollment requires a verified bench identifier.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-mallowgrid-a",
      "start_char": 145,
      "end_char": 219,
      "text": "MallowGrid charges 42 credits per device for its synthetic starter bundle.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    },
    {
      "document_id": "review012-mallowgrid-b",
      "start_char": 150,
      "end_char": 217,
      "text": "MallowGrid starter enrollment requires a verified bench identifier.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    }
  ],
  "findings": []
}
```

## Item 7370bdb665d0a82a1a10089430e2c26960060d6b8a4e740e0591fdbfbcdbe971

```text
{
  "item_id": "7370bdb665d0a82a1a10089430e2c26960060d6b8a4e740e0591fdbfbcdbe971",
  "case_id": "review012-multi-04",
  "mode": "hybrid",
  "category": "multi_source",
  "question": "What maintenance window and escalation acknowledgment does PipitDock require?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "fully_supported",
    "rationale": "Displayed quotations explicitly supply both 04:15 UTC on Wednesdays and harbor-coordinator acknowledgment of the escalation ticket. Both requested facts are supported; the retention-policy disagreement concerns a different fact.",
    "evidence_spans": [
      {
        "document_id": "review012-pipitdock-a",
        "start_char": 144,
        "end_char": 214
      },
      {
        "document_id": "review012-pipitdock-b",
        "start_char": 149,
        "end_char": 237
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 144,
      "end_char": 214,
      "text": "PipitDock schedules its maintenance window at 04:15 UTC on Wednesdays.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    },
    {
      "document_id": "review012-pipitdock-b",
      "start_char": 149,
      "end_char": 237,
      "text": "PipitDock incident escalation requires the harbor coordinator to acknowledge the ticket.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-pipitdock-a",
      "start_char": 144,
      "end_char": 214,
      "text": "PipitDock schedules its maintenance window at 04:15 UTC on Wednesdays.",
      "candidate_ranks": [
        1
      ],
      "emitted_citations": [
        "1"
      ]
    },
    {
      "document_id": "review012-pipitdock-b",
      "start_char": 149,
      "end_char": 237,
      "text": "PipitDock incident escalation requires the harbor coordinator to acknowledge the ticket.",
      "candidate_ranks": [
        2
      ],
      "emitted_citations": [
        "2"
      ]
    }
  ],
  "findings": []
}
```

## Item 048e0e80f3c9838668487196c7ba6421c09185a2634a815a933b3a54a3f1081b

```text
{
  "item_id": "048e0e80f3c9838668487196c7ba6421c09185a2634a815a933b3a54a3f1081b",
  "case_id": "review012-multi-05",
  "mode": "hybrid",
  "category": "multi_source",
  "question": "What retention window does each CobaltNest memo specify for cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "Every displayed quotation is a memo header; none gives either requested retention value. The corpus states 30 days in memo A and 90 days in memo B, at the cited undisplayed spans. This question asks what each memo says, so reporting both positions would answer it without resolving authority; the disagreement does not make this a conflicting verdict under the rubric.",
    "evidence_spans": [
      {
        "document_id": "review012-cobaltnest-a",
        "start_char": 200,
        "end_char": 291
      },
      {
        "document_id": "review012-cobaltnest-b",
        "start_char": 222,
        "end_char": 313
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 200,
      "end_char": 291,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-cobaltnest-b",
      "start_char": 222,
      "end_char": 313,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-cobaltnest-a",
      "start_char": 200,
      "end_char": 291,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-cobaltnest-b",
      "start_char": 222,
      "end_char": 313,
      "text": "For CobaltNest cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "candidate_gap",
    "ai_evidence_candidate_gap"
  ]
}
```

## Item 62dbbbd05eada89d7d0c74e7a2d9696d933698caf3adf4cd676fe6d988763804

```text
{
  "item_id": "62dbbbd05eada89d7d0c74e7a2d9696d933698caf3adf4cd676fe6d988763804",
  "case_id": "review012-multi-06",
  "mode": "hybrid",
  "category": "multi_source",
  "question": "What retention window does each EmberQuay memo specify for cycle R12?",
  "response_status": "grounded",
  "ai_judgment": {
    "verdict": "unsupported",
    "rationale": "Every displayed quotation is a memo header; none gives either requested retention value. The corpus states 30 days in memo A and 90 days in memo B, at the cited undisplayed spans. This question asks what each memo says, so reporting both positions would answer it without resolving authority; the disagreement does not make this a conflicting verdict under the rubric.",
    "evidence_spans": [
      {
        "document_id": "review012-emberquay-a",
        "start_char": 200,
        "end_char": 290
      },
      {
        "document_id": "review012-emberquay-b",
        "start_char": 214,
        "end_char": 304
      }
    ]
  },
  "authored_support": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 200,
      "end_char": 290,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-emberquay-b",
      "start_char": 214,
      "end_char": 304,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "ai_evidence": [
    {
      "document_id": "review012-emberquay-a",
      "start_char": 200,
      "end_char": 290,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 30 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    },
    {
      "document_id": "review012-emberquay-b",
      "start_char": 214,
      "end_char": 304,
      "text": "For EmberQuay cycle R12, raw inspection events are retained for 90 days in the team vault.",
      "candidate_ranks": [],
      "emitted_citations": []
    }
  ],
  "findings": [
    "candidate_gap",
    "ai_evidence_candidate_gap"
  ]
}
```
