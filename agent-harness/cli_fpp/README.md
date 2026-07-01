# cli-fpp

Remote CLI client for Falcon Player via REST API.

## Install

```bash
pip install -e ".[dev]"
```

## Configure

```bash
export FPP_BASE_URL=http://192.168.1.50
cli-fpp config set base_url http://fpp.local
```

## Usage

```bash
cli-fpp ping
cli-fpp system status --json
cli-fpp playlist list
cli-fpp playlist play "MyShow" --repeat
cli-fpp command run "Volume Set" 80
```

## Tests

```bash
pytest
FPP_BASE_URL=http://your-fpp-host pytest cli_fpp/tests/test_full_e2e.py
```
