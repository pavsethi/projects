"""Task suites. BFCL is the built-in routing-accuracy suite."""

from orchbench.suites.bfcl import load_bfcl_native, load_jsonl

__all__ = ["load_jsonl", "load_bfcl_native"]
