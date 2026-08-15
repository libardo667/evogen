window.EVOGEN_COCKPIT_STATE = {
  "capabilities": [
    {
      "evidence": [
        {
          "href": "../architecture.md",
          "label": "Architecture"
        },
        {
          "href": "../contracts.md",
          "label": "Run contract"
        }
      ],
      "id": "cycle",
      "name": "Deterministic evolution cycle",
      "not_proven": "The reference diagnostician is deterministic; arbitrary model diagnosis is not proven.",
      "plain_language": "Runs an intentionally limited agent, finds a repeated missing capability, generates real plugin code, challenges it across four suites, and retains it only when the evidence clears every gate.",
      "proof": [
        "source",
        "static",
        "portable",
        "hosted"
      ],
      "status": "available"
    },
    {
      "evidence": [
        {
          "href": "../contracts.md",
          "label": "Evolution contracts"
        }
      ],
      "id": "resumption",
      "name": "Persisted, resumable orchestration",
      "not_proven": "Instruction-level crash recovery inside an unfinished stage is not claimed.",
      "plain_language": "Stores typed stage receipts and immutable artifacts so a completed stage can be resumed without silently rerunning prior work.",
      "proof": [
        "source",
        "static",
        "portable",
        "hosted"
      ],
      "status": "available"
    },
    {
      "evidence": [
        {
          "href": "../kenshi-integration.md",
          "label": "Integration guide"
        }
      ],
      "id": "subject_boundary",
      "name": "Subject plugin and conformance doctor",
      "not_proven": "A passing doctor is additional evidence, not certification of a live environment.",
      "plain_language": "Discovers subjects without importing demo ontology into the generic core and checks their manifests, isolation, symmetry, and retained-generation materialization.",
      "proof": [
        "source",
        "static",
        "portable",
        "hosted"
      ],
      "status": "available"
    },
    {
      "evidence": [
        {
          "href": "../research-plan.md",
          "label": "Research plan"
        }
      ],
      "id": "evaluation",
      "name": "Frozen evaluator and candidate isolation",
      "not_proven": "The deterministic demo does not establish model-generated candidate quality.",
      "plain_language": "Candidate authors cannot rewrite their evaluator, scenario authority, or baseline. Rejected work remains in lineage rather than disappearing.",
      "proof": [
        "source",
        "static",
        "portable",
        "hosted"
      ],
      "status": "available"
    },
    {
      "evidence": [
        {
          "href": "../INTEGRATION_CHECKPOINT.md",
          "label": "Current checkpoint"
        }
      ],
      "id": "kae_events",
      "name": "KAE event authority and sequence",
      "not_proven": "An event inventory and sequence do not by themselves prove what a planner received; the separate G12 event supplies that evidence.",
      "plain_language": "KAE has an audited event surface and a monotonic event sequence, closing the identity ambiguity that blocked faithful trajectory import.",
      "proof": [
        "source",
        "static",
        "portable",
        "hosted"
      ],
      "status": "available"
    },
    {
      "evidence": [
        {
          "href": "https://github.com/libardo667/kenshi-agent-env/commit/bfaa4d55ae10a34d33e7a06ee3959fc6659eceb4",
          "label": "G11 authority in Git history"
        }
      ],
      "id": "kae_generation",
      "name": "Exact KAE generation manifest",
      "not_proven": "File identity does not prove that a DLL is loaded, a process matches it, or a world effect occurred.",
      "plain_language": "Publishes a stable, redacted identity for KAE source and runtime authorities, including independent built, staged, and installed native-artifact evidence.",
      "proof": [
        "source",
        "static",
        "portable",
        "hosted",
        "built",
        "installed"
      ],
      "status": "available"
    },
    {
      "evidence": [
        {
          "href": "../INTEGRATION_CHECKPOINT.md",
          "label": "G12 checkpoint"
        },
        {
          "href": "https://github.com/libardo667/kenshi-agent-env/commit/0560b9de6e049f0dc06fab9afbef76f76d198092",
          "label": "KAE completion commit"
        }
      ],
      "id": "kae_affordances",
      "name": "Exact KAE affordance-set event",
      "not_proven": "Delivery is not selection, dispatch, completion, or a world effect; the real pre-G12 live reporting fixture still truthfully contains no such event.",
      "plain_language": "Records the exact semantic choices delivered to each hosted planner, including source completeness and typed withholding, then reconstructs selections without parsing prompts or labels.",
      "proof": [
        "source",
        "static",
        "portable",
        "replay",
        "hosted"
      ],
      "status": "available"
    },
    {
      "evidence": [
        {
          "href": "../INTEGRATION_CHECKPOINT.md",
          "label": "G13 checkpoint"
        },
        {
          "href": "https://github.com/libardo667/kenshi-agent-env/commit/a8584554e30bb793f5b60ef57e3d1500de5aaa12",
          "label": "KAE completion commit"
        },
        {
          "href": "https://github.com/libardo667/kenshi-agent-env/actions/runs/31720597916",
          "label": "Hosted matrix"
        }
      ],
      "id": "kae_capability_manifest",
      "name": "Generated KAE capability manifest",
      "not_proven": "This is an evidence-backed inventory, not proof that every operation works live or that KAE is already registered as an EvoGen subject.",
      "plain_language": "Publishes 69 KAE capabilities from their real operation, native, protocol, service, and proof owners, including one unsupported threat-response boundary that KAE does not pretend to satisfy.",
      "proof": [
        "source",
        "static",
        "portable",
        "hosted"
      ],
      "status": "available"
    },
    {
      "evidence": [
        {
          "href": "../INTEGRATION_CHECKPOINT.md",
          "label": "G14 checkpoint"
        },
        {
          "href": "../../tests/fixtures/kae_g14_export/README.md",
          "label": "Portable bundle"
        },
        {
          "href": "https://github.com/libardo667/kenshi-agent-env/commit/548658cbcef35037252e63be40248fa6a94b5ec1",
          "label": "KAE exporter commit"
        },
        {
          "href": "https://github.com/libardo667/kenshi-agent-env/actions/runs/31906703483",
          "label": "Hosted matrix"
        }
      ],
      "id": "kae_trajectory_export",
      "name": "Exact KAE trajectory export",
      "not_proven": "This proves contract compatibility and replay preparation, not KAE subject registration, a public replay run, metric equivalence, an evolved capability, or a live world effect.",
      "plain_language": "KAE now owns a strict, content-addressed raw-to-normalized boundary. EvoGen reads the exported envelope without guessing aliases, identities, order, or world effects.",
      "proof": [
        "source",
        "static",
        "portable",
        "replay",
        "hosted"
      ],
      "status": "available"
    },
    {
      "evidence": [
        {
          "href": "../SEQUENCED_SUBAGENT_EXECUTION_PLAN.md",
          "label": "KAE journey"
        }
      ],
      "id": "kae_cycle",
      "name": "Historical and new KAE evolution cycles",
      "not_proven": "G14 proves a portable export contract only; no public replay showcase, evolved capability, or live world effect has been retained.",
      "plain_language": "The exact KAE exporter and EvoGen strict-envelope boundary are now available; the replay showcase, historical evolution, and supervised live proof remain queued.",
      "proof": [
        "withheld"
      ],
      "status": "planned"
    },
    {
      "evidence": [
        {
          "href": "../SEQUENCED_SUBAGENT_EXECUTION_PLAN.md",
          "label": "OpenTTD journey"
        }
      ],
      "id": "openttd_subject",
      "name": "OpenTTD subject environment",
      "not_proven": "The local OpenTTD installation is an input, not proof of the planned environment. G30 stays blocked until both supervised live KAE work and deferred scientific depth close.",
      "plain_language": "Will provide a pinned, deterministic, headless second environment with causal command lifecycles and a narrow road-freight surface.",
      "proof": [
        "withheld"
      ],
      "status": "planned"
    },
    {
      "evidence": [
        {
          "href": "../SEQUENCED_SUBAGENT_EXECUTION_PLAN.md",
          "label": "Release journey"
        }
      ],
      "id": "genericity",
      "name": "Two-subject genericity",
      "not_proven": "Cross-subject generality remains withheld until G46–G49.",
      "plain_language": "Will prove that one CLI and artifact layout operate both KAE and OpenTTD without leaking either subject's ontology into EvoGen core.",
      "proof": [
        "withheld"
      ],
      "status": "planned"
    }
  ],
  "commands": [
    {
      "command": "uv run --frozen --extra dev python scripts/verify.py",
      "cwd": "evogen",
      "label": "Reproduce the full EvoGen verifier"
    },
    {
      "command": "uv run evogen subject doctor microworld",
      "cwd": "evogen",
      "label": "Inspect the bundled subject"
    },
    {
      "command": "./dev generation-manifest --output /tmp/kae-generation.json",
      "cwd": "kenshi-agent-env",
      "label": "Publish a KAE generation manifest"
    },
    {
      "command": "./dev capability-manifest --generation-id 0000000000000000000000000000000000000000000000000000000000000000 --output /tmp/kae-capabilities.json",
      "cwd": "kenshi-agent-env",
      "label": "Publish KAE's capability inventory"
    },
    {
      "command": "./dev trajectory-export --events <events.jsonl> --generation-manifest <generation.json> --capability-manifest <capability.json> --scenario-id <scenario-id> --output <new-bundle>",
      "cwd": "kenshi-agent-env",
      "label": "Export an exact KAE trajectory"
    }
  ],
  "current_focus": {
    "goal_id": "G15",
    "human_gate": "none",
    "state": "unstarted",
    "summary": "The optional KAE subject plugin remains the next unstarted packet. The replay showcase and any evolved capability remain withheld.",
    "title": "Register KAE as an EvoGen subject plugin"
  },
  "demo_result": {
    "label": "Deterministic microworld retention proof",
    "scope": "Portable and hosted evidence; not a live-game claim.",
    "suites": [
      {
        "baseline": "0 / 1",
        "candidate": "1 / 1",
        "label": "Revealing"
      },
      {
        "baseline": "0 / 3",
        "candidate": "3 / 3",
        "label": "Structural variants"
      },
      {
        "baseline": "2 / 2",
        "candidate": "2 / 2",
        "label": "Regressions"
      },
      {
        "baseline": "0 / 1",
        "candidate": "1 / 1",
        "label": "Long horizon"
      }
    ],
    "verdict": "retain"
  },
  "execution_route": [
    {
      "boundary": "Portable and replay proof only. No evolved or live-proven KAE capability is claimed.",
      "delivers": "A real KAE bundle flowing through the public EvoGen path with raw and normalized events, provenance, receipt versus later outcome, and metric equivalence visible in one reusable cockpit.",
      "goals": [
        "G14",
        "G15",
        "G16",
        "G17"
      ],
      "id": "replay_showcase",
      "label": "Real KAE replay showcase",
      "status": "next"
    },
    {
      "boundary": "Historical portable and replay evidence is not a newly discovered or live-proven capability.",
      "delivers": "One sealed historical KAE deficit carried through diagnosis, investigation, specification, isolated implementation, independent evaluation, and retained EvoGen lineage.",
      "goals": [
        "G18",
        "G22",
        "G23",
        "G24",
        "G25",
        "G26",
        "G27"
      ],
      "id": "historical_evolution",
      "label": "One historical evolution",
      "status": "planned"
    },
    {
      "boundary": "A dispatch, native acknowledgement, receipt, or process exit never substitutes for later world evidence.",
      "delivers": "A current supervised KAE observation that may proceed through approved installation, live variants, regressions, long-run evidence, and rollback to a retention decision.",
      "goals": [
        "G28",
        "G29"
      ],
      "id": "supervised_live_evolution",
      "label": "One supervised live evolution",
      "status": "planned"
    },
    {
      "boundary": "Deferred means later in the proof-first route, not optional; OpenTTD remains blocked until this branch closes.",
      "delivers": "A diverse sealed corpus, blind deterministic benchmark, and approved model-versus-human diagnosis study with all transcripts and failures retained.",
      "goals": [
        "G19",
        "G20",
        "G21"
      ],
      "id": "deferred_scientific_depth",
      "label": "Deferred scientific depth",
      "status": "deferred"
    },
    {
      "boundary": "The local OpenTTD installation is availability evidence only; subject and release claims begin only after both KAE branches close.",
      "delivers": "A pinned headless second subject, a retained OpenTTD capability change, two-subject genericity, and a release audit.",
      "goals": [
        "G30",
        "G31",
        "G32",
        "G33",
        "G34",
        "G35",
        "G36",
        "G37",
        "G38",
        "G39",
        "G40",
        "G41",
        "G42",
        "G43",
        "G44",
        "G45",
        "G46",
        "G47",
        "G48",
        "G49"
      ],
      "id": "openttd_and_release",
      "label": "OpenTTD and release",
      "status": "planned"
    }
  ],
  "goals": [
    {
      "depends_on": [],
      "human_gates": [],
      "id": "G01",
      "journey_id": "foundation",
      "profile": "foundation_release",
      "repositories": [
        "evogen"
      ],
      "state": "complete",
      "title": "Freeze and publish the alpha honestly"
    },
    {
      "depends_on": [
        "G01"
      ],
      "human_gates": [],
      "id": "G02",
      "journey_id": "foundation",
      "profile": "core_contract",
      "repositories": [
        "evogen"
      ],
      "state": "complete",
      "title": "Give subjects a real plugin boundary"
    },
    {
      "depends_on": [
        "G02"
      ],
      "human_gates": [],
      "id": "G03",
      "journey_id": "foundation",
      "profile": "schema_migration",
      "repositories": [
        "evogen"
      ],
      "state": "complete",
      "title": "Fix trajectory identity before importing real logs"
    },
    {
      "depends_on": [
        "G03"
      ],
      "human_gates": [],
      "id": "G04",
      "journey_id": "foundation",
      "profile": "orchestration_state",
      "repositories": [
        "evogen"
      ],
      "state": "complete",
      "title": "Make the evolution cycle resumable"
    },
    {
      "depends_on": [
        "G04"
      ],
      "human_gates": [],
      "id": "G05",
      "journey_id": "foundation",
      "profile": "lifecycle_contract",
      "repositories": [
        "evogen"
      ],
      "state": "complete",
      "title": "Make probes first-class"
    },
    {
      "depends_on": [
        "G05"
      ],
      "human_gates": [],
      "id": "G06",
      "journey_id": "foundation",
      "profile": "role_contract",
      "repositories": [
        "evogen"
      ],
      "state": "complete",
      "title": "Put every reasoning role behind typed artifacts"
    },
    {
      "depends_on": [
        "G06"
      ],
      "human_gates": [],
      "id": "G07",
      "journey_id": "foundation",
      "profile": "evaluator_security",
      "repositories": [
        "evogen"
      ],
      "state": "complete",
      "title": "Freeze evaluation authority outside candidates"
    },
    {
      "depends_on": [
        "G07"
      ],
      "human_gates": [],
      "id": "G08",
      "journey_id": "foundation",
      "profile": "conformance",
      "repositories": [
        "evogen"
      ],
      "state": "complete",
      "title": "Ship a subject conformance kit and doctor"
    },
    {
      "depends_on": [
        "G08"
      ],
      "human_gates": [],
      "id": "G09",
      "journey_id": "kenshi",
      "profile": "source_inventory",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "complete",
      "title": "Audit KAE's actual event surface"
    },
    {
      "depends_on": [
        "G09"
      ],
      "human_gates": [],
      "id": "G10",
      "journey_id": "kenshi",
      "profile": "logger_migration",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "complete",
      "title": "Add a real monotonic event sequence to KAE logs"
    },
    {
      "depends_on": [
        "G10"
      ],
      "human_gates": [],
      "id": "G11",
      "journey_id": "kenshi",
      "profile": "generation_manifest",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "complete",
      "title": "Export an exact KAE generation manifest"
    },
    {
      "depends_on": [
        "G11"
      ],
      "human_gates": [],
      "id": "G12",
      "journey_id": "kenshi",
      "profile": "event_contract",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "complete",
      "title": "Log the exact affordance set as its own event"
    },
    {
      "depends_on": [
        "G12"
      ],
      "human_gates": [],
      "id": "G13",
      "journey_id": "kenshi",
      "profile": "generated_manifest",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "complete",
      "title": "Generate KAE's capability manifest from authorities"
    },
    {
      "depends_on": [
        "G13"
      ],
      "human_gates": [],
      "id": "G14",
      "journey_id": "kenshi",
      "profile": "cross_repo_adapter",
      "repositories": [
        "kenshi-agent-env",
        "evogen"
      ],
      "state": "complete",
      "title": "Replace the provisional normalizer with an exact KAE exporter"
    },
    {
      "depends_on": [
        "G14"
      ],
      "human_gates": [],
      "id": "G15",
      "journey_id": "kenshi",
      "profile": "subject_plugin",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "next",
      "title": "Register KAE as an EvoGen subject plugin"
    },
    {
      "depends_on": [
        "G15"
      ],
      "human_gates": [],
      "id": "G16",
      "journey_id": "kenshi",
      "profile": "observer_replay",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Build observer and replay runners first"
    },
    {
      "depends_on": [
        "G16"
      ],
      "human_gates": [],
      "id": "G17",
      "journey_id": "kenshi",
      "profile": "metric_mapping",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Adapt KAE's existing metrics instead of replacing them"
    },
    {
      "depends_on": [
        "G17"
      ],
      "human_gates": [],
      "id": "G18",
      "journey_id": "kenshi",
      "profile": "sealed_case",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Package the missing-interface-close case exactly"
    },
    {
      "depends_on": [
        "G18"
      ],
      "human_gates": [],
      "id": "G19",
      "journey_id": "kenshi",
      "profile": "sealed_corpus",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Build the first KAE historical corpus"
    },
    {
      "depends_on": [
        "G19"
      ],
      "human_gates": [],
      "id": "G20",
      "journey_id": "kenshi",
      "profile": "blind_benchmark",
      "repositories": [
        "kenshi-agent-env",
        "evogen"
      ],
      "state": "unstarted",
      "title": "Add a hidden-answer diagnostic benchmark"
    },
    {
      "depends_on": [
        "G20"
      ],
      "human_gates": [
        "provider_model_cost"
      ],
      "id": "G21",
      "journey_id": "kenshi",
      "profile": "external_model_study",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Run the first model-versus-human diagnosis study"
    },
    {
      "depends_on": [
        "G18"
      ],
      "human_gates": [],
      "id": "G22",
      "journey_id": "kenshi",
      "profile": "deterministic_or_human_investigator",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Give KAE a bounded environment investigator"
    },
    {
      "depends_on": [
        "G22"
      ],
      "human_gates": [],
      "id": "G23",
      "journey_id": "kenshi",
      "profile": "capability_architect",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Give KAE a capability architect that handles more than additions"
    },
    {
      "depends_on": [
        "G23"
      ],
      "human_gates": [],
      "id": "G24",
      "journey_id": "kenshi",
      "profile": "isolated_candidate",
      "repositories": [
        "evogen",
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Build isolated KAE candidates in Git worktrees"
    },
    {
      "depends_on": [
        "G24"
      ],
      "human_gates": [],
      "id": "G25",
      "journey_id": "kenshi",
      "profile": "independent_evaluation",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Review and evaluate KAE candidates without live installation"
    },
    {
      "depends_on": [
        "G25"
      ],
      "human_gates": [],
      "id": "G26",
      "journey_id": "kenshi",
      "profile": "live_suite_definition",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Define disposable live suites and binary provenance"
    },
    {
      "depends_on": [
        "G18",
        "G26"
      ],
      "human_gates": [],
      "id": "G27",
      "journey_id": "kenshi",
      "profile": "historical_level4",
      "repositories": [
        "evogen",
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Complete a historical KAE level-4 cycle"
    },
    {
      "depends_on": [
        "G27"
      ],
      "human_gates": [
        "live_session_budget"
      ],
      "id": "G28",
      "journey_id": "kenshi",
      "profile": "supervised_observation",
      "repositories": [
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Observe a genuinely new KAE deficit without forcing one"
    },
    {
      "depends_on": [
        "G28"
      ],
      "human_gates": [
        "install",
        "live_revealing",
        "live_variants",
        "live_regressions",
        "live_long_run"
      ],
      "id": "G29",
      "journey_id": "kenshi",
      "profile": "supervised_live_candidate",
      "repositories": [
        "evogen",
        "kenshi-agent-env"
      ],
      "state": "unstarted",
      "title": "Close the first new KAE issue through supervised live proof"
    },
    {
      "depends_on": [
        "G21",
        "G29"
      ],
      "human_gates": [
        "upstream_carrying_strategy"
      ],
      "id": "G30",
      "journey_id": "openttd",
      "profile": "subject_bootstrap",
      "repositories": [
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Create `openttd-agent-env` with a pinned upstream boundary"
    },
    {
      "depends_on": [
        "G30"
      ],
      "human_gates": [],
      "id": "G31",
      "journey_id": "openttd",
      "profile": "headless_build",
      "repositories": [
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Build and run OpenTTD headlessly and reproducibly"
    },
    {
      "depends_on": [
        "G31"
      ],
      "human_gates": [],
      "id": "G32",
      "journey_id": "openttd",
      "profile": "scenario_pack",
      "repositories": [
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Create a deterministic OpenTTD scenario pack"
    },
    {
      "depends_on": [
        "G32"
      ],
      "human_gates": [
        "upstream_patch_route"
      ],
      "id": "G33",
      "journey_id": "openttd",
      "profile": "bridge_spike",
      "repositories": [
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Prove the least invasive external-control bridge"
    },
    {
      "depends_on": [
        "G33"
      ],
      "human_gates": [],
      "id": "G34",
      "journey_id": "openttd",
      "profile": "executor_shell",
      "repositories": [
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Build the minimal NoAI executor shell"
    },
    {
      "depends_on": [
        "G34"
      ],
      "human_gates": [],
      "id": "G35",
      "journey_id": "openttd",
      "profile": "protocol_freeze",
      "repositories": [
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Specify OpenTTD Protocol 1.0 as an economic network world model"
    },
    {
      "depends_on": [
        "G35"
      ],
      "human_gates": [],
      "id": "G36",
      "journey_id": "openttd",
      "profile": "command_lifecycle",
      "repositories": [
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Give OpenTTD commands a causal lifecycle"
    },
    {
      "depends_on": [
        "G36"
      ],
      "human_gates": [],
      "id": "G37",
      "journey_id": "openttd",
      "profile": "operation_surface",
      "repositories": [
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Expose a narrow road-freight operation surface"
    },
    {
      "depends_on": [
        "G37"
      ],
      "human_gates": [],
      "id": "G38",
      "journey_id": "openttd",
      "profile": "subject_runtime",
      "repositories": [
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Build the OpenTTD agent runtime and planners"
    },
    {
      "depends_on": [
        "G38"
      ],
      "human_gates": [],
      "id": "G39",
      "journey_id": "openttd",
      "profile": "subject_plugin",
      "repositories": [
        "openttd-agent-env",
        "evogen"
      ],
      "state": "unstarted",
      "title": "Register OpenTTD as an EvoGen subject"
    },
    {
      "depends_on": [
        "G39"
      ],
      "human_gates": [],
      "id": "G40",
      "journey_id": "openttd",
      "profile": "baseline_trials",
      "repositories": [
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Establish honest baseline competence"
    },
    {
      "depends_on": [
        "G40"
      ],
      "human_gates": [
        "deficit_classification_review"
      ],
      "id": "G41",
      "journey_id": "openttd",
      "profile": "deficit_observation",
      "repositories": [
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Create a route-planning capability deficit that is not a missing engine verb"
    },
    {
      "depends_on": [
        "G41"
      ],
      "human_gates": [],
      "id": "G42",
      "journey_id": "openttd",
      "profile": "blind_diagnosis_spec",
      "repositories": [
        "evogen",
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Let EvoGen diagnose and specify the route-planning gap"
    },
    {
      "depends_on": [
        "G42"
      ],
      "human_gates": [],
      "id": "G43",
      "journey_id": "openttd",
      "profile": "isolated_candidate",
      "repositories": [
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Implement and adversarially review `plan_road_route`"
    },
    {
      "depends_on": [
        "G43"
      ],
      "human_gates": [],
      "id": "G44",
      "journey_id": "openttd",
      "profile": "deterministic_selection",
      "repositories": [
        "evogen",
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Evaluate and retain the first OpenTTD generation"
    },
    {
      "depends_on": [
        "G44"
      ],
      "human_gates": [],
      "id": "G45",
      "journey_id": "openttd",
      "profile": "observability_follow_on",
      "repositories": [
        "evogen",
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Close a second OpenTTD issue in observability, not action"
    },
    {
      "depends_on": [
        "G45"
      ],
      "human_gates": [],
      "id": "G46",
      "journey_id": "release",
      "profile": "genericity_audit",
      "repositories": [
        "evogen"
      ],
      "state": "unstarted",
      "title": "Perform the two-subject genericity audit"
    },
    {
      "depends_on": [
        "G46"
      ],
      "human_gates": [],
      "id": "G47",
      "journey_id": "release",
      "profile": "cross_repo_cli",
      "repositories": [
        "evogen",
        "kenshi-agent-env",
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Make one CLI and artifact layout operate both subjects"
    },
    {
      "depends_on": [
        "G47"
      ],
      "human_gates": [
        "provider_model_cost"
      ],
      "id": "G48",
      "journey_id": "release",
      "profile": "cross_subject_study",
      "repositories": [
        "evogen",
        "kenshi-agent-env",
        "openttd-agent-env"
      ],
      "state": "unstarted",
      "title": "Run a cross-subject capability-engineering study"
    },
    {
      "depends_on": [
        "G48"
      ],
      "human_gates": [
        "final_publication"
      ],
      "id": "G49",
      "journey_id": "release",
      "profile": "release_audit",
      "repositories": [
        "evogen"
      ],
      "state": "unstarted",
      "title": "Freeze the first serious EvoGen completion state"
    }
  ],
  "journeys": [
    {
      "first_goal": 1,
      "id": "foundation",
      "label": "I · EvoGen foundation",
      "last_goal": 8,
      "summary": "Make the generic evolution engine deterministic, resumable, typed, and subject-neutral."
    },
    {
      "first_goal": 9,
      "id": "kenshi",
      "label": "II · Kenshi proof",
      "last_goal": 29,
      "summary": "Integrate a real autonomous-game subject while preserving causal and live-proof boundaries."
    },
    {
      "first_goal": 30,
      "id": "openttd",
      "label": "III · OpenTTD proof",
      "last_goal": 45,
      "summary": "Build a second subject from a pinned headless environment through retained capability changes."
    },
    {
      "first_goal": 46,
      "id": "release",
      "label": "IV · Genericity and release",
      "last_goal": 49,
      "summary": "Audit two-subject generality, unify operation, and freeze a serious completion state."
    }
  ],
  "last_closed_goal": {
    "goal_id": "G14",
    "summary": "KAE now publishes an exact trajectory exporter and EvoGen consumes its strict current envelope, retiring the broad aliasing normalizer while retaining fixture-only historical diagnosis evidence.",
    "title": "Replace the provisional normalizer with an exact KAE exporter"
  },
  "plan_revision_commit": "5e72ca364f0a1b2c5b23d41c9af5a2a15099b946",
  "product_name": "EvoGen",
  "product_thesis": "Turn repeated agent failures into evidence-backed capability changes.",
  "progress": {
    "checkpoint_current_goal_id": "G14",
    "completed_goal_count": 14,
    "current_route_id": "replay_showcase",
    "goal_count": 49,
    "last_closed_goal_id": "G14",
    "next_goal_id": "G15"
  },
  "proof_lanes": [
    {
      "description": "The authority exists in reviewed code or a checked-in contract.",
      "id": "source",
      "label": "Source"
    },
    {
      "description": "Automated tests exercise the contract without claiming an external effect.",
      "id": "static",
      "label": "Static tests"
    },
    {
      "description": "A clean locked verifier reproduces the result from the repository.",
      "id": "portable",
      "label": "Portable"
    },
    {
      "description": "Recorded evidence can reconstruct the relevant choice or outcome.",
      "id": "replay",
      "label": "Replay"
    },
    {
      "description": "The public commit passes its hosted test matrix.",
      "id": "hosted",
      "label": "Hosted CI"
    },
    {
      "description": "An artifact was built and identified; loading is not implied.",
      "id": "built",
      "label": "Built artifact"
    },
    {
      "description": "Installed bytes were independently identified; runtime use is not implied.",
      "id": "installed",
      "label": "Installed artifact"
    },
    {
      "description": "Later independent engine evidence attests a world effect.",
      "id": "live",
      "label": "Live effect"
    },
    {
      "description": "The evidence does not support this claim yet.",
      "id": "withheld",
      "label": "Withheld"
    }
  ],
  "repositories": [
    {
      "branch": "main",
      "evidence_commit": "5e72ca364f0a1b2c5b23d41c9af5a2a15099b946",
      "hosted_run": "31908510607",
      "href": "https://github.com/libardo667/evogen/commit/5e72ca364f0a1b2c5b23d41c9af5a2a15099b946",
      "id": "evogen",
      "matrix": "Python 3.11–3.13",
      "name": "EvoGen",
      "role": "generic evolution plane",
      "state": "G01–G08 and G14 complete; G15 queued"
    },
    {
      "branch": "main",
      "evidence_commit": "548658cbcef35037252e63be40248fa6a94b5ec1",
      "hosted_run": "31906703483",
      "href": "https://github.com/libardo667/kenshi-agent-env/commit/548658cbcef35037252e63be40248fa6a94b5ec1",
      "id": "kae",
      "matrix": "Python 3.11–3.14",
      "name": "Kenshi Agent Environment",
      "role": "first real subject",
      "state": "G09–G14 complete"
    },
    {
      "branch": "not created",
      "evidence_commit": null,
      "hosted_run": null,
      "href": "../SEQUENCED_SUBAGENT_EXECUTION_PLAN.md",
      "id": "openttd",
      "matrix": null,
      "name": "OpenTTD Agent Environment",
      "role": "second real subject",
      "state": "not started · begins at G30"
    }
  ],
  "schema_version": "evogen-cockpit/v1",
  "snapshot_label": "G14 closed · G15 queued",
  "source_authority": {
    "branch": "main",
    "input_digest": "9259bd10f2f4eaada1d36504a0a25259a6afbd9c080f45839f056d82da758314",
    "inputs": [
      {
        "path": "docs/SEQUENCED_SUBAGENT_EXECUTION_PLAN.md",
        "sha256": "690b1ba6a64f6e59774157bbc438fd68aca0b4d25c6e904c75ebd80b46492fe8"
      },
      {
        "path": "docs/INTEGRATION_CHECKPOINT.md",
        "sha256": "8151c4044b8ad3b847508931273c637c763a2e62c9e22907231a6413da3ced99"
      },
      {
        "path": "docs/cockpit/content.json",
        "sha256": "18b65506ba35dcf89a9ad9602590c20e94e3c090fd5dd713363366cec7d68af2"
      },
      {
        "path": "tests/fixtures/kae_g14_export/manifest.json",
        "sha256": "82ad0c3e68dbb516cb3f2073e780be47275d10cadd3b19773267af36ac416dac"
      },
      {
        "path": "tests/fixtures/kae_g14_export/raw-events.jsonl",
        "sha256": "98f3d6cfbc5173692e7bcf3b12942aab80e121695582ca82310188693490e08a"
      },
      {
        "path": "tests/fixtures/kae_g14_export/trajectory.jsonl",
        "sha256": "4500b85d077024641b5f258ea1cb0733509ee4a3ab77d1068fd53efb8277aee0"
      },
      {
        "path": "tests/fixtures/kae_g14_export/README.md",
        "sha256": "fde068a7992d709001688e91a350800e9d2109a253ec3e97f936ea689a1ae44b"
      }
    ],
    "plan_revision_commit": "5e72ca364f0a1b2c5b23d41c9af5a2a15099b946",
    "repository": "evogen"
  },
  "state_id": "sha256:8ab08483d7e642a30a5828798cd3c4ef247dafb6ab3789419d91db428f1a99c2",
  "trajectory_export_proof": {
    "boundary": "Receipt and later outcome remain separate. The historical soak proves exporter compatibility with an explicitly supplied manifest, not its original generation identity or a live world effect. G15 registration, G16 replay, and G17 metric equivalence remain unstarted.",
    "bundle_id": "b653c034424ed7e917dc25c411876a1d621cdac756d8054d8ffd0fdb39b4d946",
    "mapping": [
      {
        "normalized": "run_started",
        "source": "run_started"
      },
      {
        "normalized": "execution_receipt",
        "source": "action_receipt"
      },
      {
        "normalized": "outcome_observation",
        "source": "action_outcome"
      },
      {
        "normalized": "observation_delta",
        "source": "world_state_update"
      },
      {
        "normalized": "run_finished",
        "source": "run_finished"
      }
    ],
    "portable_source": {
      "normalized_events": 5,
      "normalized_sequence": "0..4",
      "raw_records": 5,
      "raw_sha256": "98f3d6cfbc5173692e7bcf3b12942aab80e121695582ca82310188693490e08a",
      "run_id": "kae-g14-portable",
      "source_sequence": "1..5"
    },
    "real_run_acceptance": {
      "normalized_events": 22995,
      "raw_records": 38293,
      "source_sha256": "542eff1353e00b9cd4cad4c83969e4db9156776d7c55b5e51d01a0356ffb92ef"
    },
    "scope": "KAE commit 548658c owns normalization; EvoGen only verifies and reads the strict exported envelope.",
    "title": "Exact KAE events now cross one owned boundary",
    "withheld": [
      "binding",
      "dispatch"
    ]
  },
  "withheld_claims": [
    "No general model has yet been shown to infer arbitrary missing capabilities from arbitrary environments.",
    "The KAE generation manifest does not prove that native bytes are loaded, identify a running process, or prove a world effect.",
    "KAE's production trajectory exporter is available, but KAE is not yet registered as an EvoGen subject and no replay showcase or evolved capability is retained.",
    "No OpenTTD subject repository or retained OpenTTD capability exists yet.",
    "Two-subject genericity and the first serious release remain unproven."
  ]
};
