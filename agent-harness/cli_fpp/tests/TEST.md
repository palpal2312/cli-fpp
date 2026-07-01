# Test Plan — cli-fpp

## Test inventory

| File | Type | Planned tests |
|------|------|---------------|
| `test_core.py` | Unit (mocked HTTP) | ~13 |
| `test_full_e2e.py` | E2E (real FPP) | ~6 |

## E2E

Requires `FPP_BASE_URL`. CLI subprocess: `cli-fpp --json ping`.
