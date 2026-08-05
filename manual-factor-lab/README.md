# Manual Factor Laboratory

This directory is a researcher-owned laboratory for ten frozen daily factors.
It deliberately supplies contracts rather than factor calculations: each
function in `src/factors.py` raises a clear `NotImplementedError` until a
researcher implements and validates it with a licensed point-in-time panel.

The immutable candidate list, field contract, availability rule, hypothesis,
and direction are in [factor_registry.csv](factor_registry.csv). The evaluation
and admission rules are in [research_protocol.md](research_protocol.md).

Run the contract check after installing the repository requirements:

```bash
python -m pytest manual-factor-lab/tests/test_factor_contracts.py -v
```

No daily market data, derived panels, research results, or executable factor
formulas belong in this public laboratory.
