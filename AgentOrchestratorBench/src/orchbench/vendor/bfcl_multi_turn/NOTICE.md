# Vendored: BFCL multi-turn API implementations

These modules are copied from the **Berkeley Function Calling Leaderboard (BFCL)**,
`bfcl-eval` 2026.3.23
(`bfcl_eval/eval_checker/multi_turn_eval/func_source_code/`), part of
<https://github.com/ShishirPatil/gorilla> — Copyright the Gorilla / BFCL authors,
licensed under the Apache License 2.0 (full text in `LICENSE` in this directory).

They are the stateful APIs (file system, messaging, trading, travel, vehicle
control, ...) that BFCL's multi-turn categories run against. orchbench executes
model tool calls against them so its multi-turn scores are computed on the same
worlds as the leaderboard.

## Modifications

Kept byte-for-byte except:

- Import paths rewritten from `bfcl_eval.eval_checker.multi_turn_eval.func_source_code.*`
  to `orchbench.vendor.bfcl_multi_turn.*`.
- An unused `import subprocess` removed from `gorilla_file_system.py`.

Only the classes used by BFCL's four multi-turn categories are included (not the
memory / web-search agentic APIs). These files are excluded from orchbench's
lint and type-check rules so they stay identical to upstream.
