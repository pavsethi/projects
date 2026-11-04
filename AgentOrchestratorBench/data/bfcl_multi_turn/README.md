# BFCL multi-turn data (vendored)

From the Berkeley Function Calling Leaderboard, `bfcl-eval` 2026.3.23
(<https://github.com/ShishirPatil/gorilla>), Apache License 2.0 (see `LICENSE`).
Unmodified.

| File | Contents |
|---|---|
| `BFCL_v4_multi_turn_{base,miss_func,miss_param,long_context}.json` | 200 scenarios each: user turns, initial API state, involved API classes |
| `possible_answer/…` | ground-truth calls per user turn |
| `multi_turn_func_doc/*.json` | tool documentation for each API class |

Loaded by `orchbench.suites.bfcl_multi_turn`; executed against the vendored APIs
in `src/orchbench/vendor/bfcl_multi_turn/`.
