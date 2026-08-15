# KAE G14 export contract fixture

This three-file bundle was produced by the public
`kenshi-agent-env` `./dev trajectory-export` command at commit
`548658cbcef35037252e63be40248fa6a94b5ec1`.

The five compact source records exercise only reviewed exact projections:
`run_started`, `action_receipt`, `action_outcome`, `world_state_update`, and
`run_finished`. The source is synthetic portable contract evidence. The
separate retained 38,293-record KAE soak is the real-run acceptance evidence;
it is identified in `docs/INTEGRATION_CHECKPOINT.md` and is not copied here.

The bundle is intentionally complete. `manifest.json` binds the exact bytes of
`raw-events.jsonl` and `trajectory.jsonl`; tests verify both digests and counts
before checking EvoGen's strict current-envelope reader.
