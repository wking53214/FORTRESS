# FORTRESS

Consolidated FORTRESS content, pulled from across this week's repo sweep
by content signature (`class Fortress`, `PredictiveStateController`,
`FortressStateTransition`), not by filename.

## Contents

- **`fortress_kernel.py`** — the one genuinely complete, working,
  tested implementation. Moved here from
  [sentinel_os](https://github.com/wking53214/sentinel_os)'s
  `sentinel_os/sage_k/kernel.py` (also still present there — sentinel_os
  has it wired into a tested package with its own test suite and
  examples, so it wasn't removed from there, just copied here as the
  canonical reference copy). Defines every dependency it uses locally
  (`IntegrityLayer`, `InvariantMonitor`, `DriftMonitor`, `MandateLayer`,
  `WorldModel`, `Policy`) — nothing external required. Its own docstring
  is explicit about scope: a single scalar KPI nudged toward a moving
  target by one of three fixed-gain linear controllers, selected by a
  softmax policy; guardrail classes clamp the action and can freeze
  learning. Docstring references to "Echo State Network reservoirs" and
  "Lyapunov Stability Engines" are marketing language from the original
  source, not implemented behavior — there's no ESN reservoir or
  Lyapunov exponent calculation, just tanh-based linear layers and a
  rolling standard deviation used as a volatility proxy.

- **`PredictiveStateController.py`** — from
  [ARCHIVE](https://github.com/wking53214/ARCHIVE)'s `artifact_8.json`
  (report 8). A second, independent, self-contained implementation:
  real numpy-based recurrent state projection, variance calculation,
  hysteresis-based override engagement/disengagement, blending
  coefficient smoothing. Checked closely for the mocked-stub pattern
  seen elsewhere in that sweep — it isn't mocked, this is genuine
  algorithmic code. Needs the standard ARCHIVE-corpus corruption
  reversed to run (`__init__`/`**` were stripped throughout that
  source; see ARCHIVE's README for the full explanation) — not fixed
  here, moved as extracted.

- **`Fortress_orchestrator_incomplete.py`** — from ARCHIVE's
  `artifact_2.json`. A third variant: real orchestration logic
  (`run_cycle` wiring together an integrity layer, regime classifier,
  invariant monitor, drift monitor, world model, policy, and three
  agent types), but references external classes (`IntegrityLayer`,
  `RegimeEngine`, `InvariantMonitor`, `DriftMonitor`, `WorldModel`,
  `Policy`, `ConservativeAgent`, `AggressiveAgent`, `ReactiveAgent`,
  `Payload`, `MandateLayer`) that aren't defined anywhere in that
  payload — genuinely incomplete, not mocked. Worth comparing against
  `fortress_kernel.py`'s version of the same guardrail classes before
  doing anything with this one; they may turn out to be the same
  design at different completeness.

- **`PredictiveIntegrityController.py`** ("FORTRESS v2 — Hardened
  Release") — from an attachment in
  [Claude_History](https://github.com/wking53214/Claude_History)'s
  `730af555-be61-438f-8f6b-25adf965dac8` conversation. A fourth,
  independent implementation, same design lineage as
  `PredictiveStateController.py` (recurrent latent-state projection,
  composite distortion/variance scoring, hysteresis-based governance
  engagement, freeze-counter lockout, slew-limited blending against a
  safe fallback) but with real additions not present in that variant:
  cryptographic provenance verification (`_verify_provenance`, checks a
  signed source_id/signature pair), Fisher-Information-Matrix-style
  gradient tracking (`self.G`/`self.g_ema`, cosine-drift between
  gradient steps), and causal-divergence detection (flags a payload
  that claims stability in its text while the actual error is high).
  Different config field names throughout — an independently-written
  version, not a renamed copy. **The only one of the four variants here
  that runs cleanly out of the box with zero corruption or missing
  dependencies** — it came from Claude's own export, not the mangled
  ARCHIVE JSON pipeline. Verified: `python3 PredictiveIntegrityController.py`
  runs its built-in 21-step stress harness end to end with real output.

Not moved here: `ARCHIVE/extracted/report_8/UGPISOmegaController.py`
mentions FORTRESS (`self.fortress = PredictiveStateController(...)`)
but it's multi-system integration code (also wires in DIT, OBSERVE,
URE, EDDP, GSA) — not FORTRESS-specific, left in ARCHIVE.
`GSA-GATEWAY/governance-stack/governance_os_security_source.py` has an
unrelated toy `class Fortress` (a single `enforce()` method checking
for the word "forbidden") that's one small stage in a much larger
single-file governance-pipeline demo alongside `Citadel` and
`Sentinel` — not substantial enough on its own to be worth fragmenting
out of that file.

No code edits were made moving any of this — same-content, different
location.
