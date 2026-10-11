# Demo scan target

`insecure_api.py` is a deliberately vulnerable API used to demonstrate that
APIShield's scanners find real issues. It is a demo fixture, not product code.

What it trips, in one scan:

| Scanner | Findings | Severity | OWASP |
| --- | --- | --- | --- |
| `headers` | 4 per endpoint | medium | API8:2023 |
| `cors` | wildcard origin + credentials | high | API8:2023 |
| `http_methods` | TRACE enabled / PUT, DELETE / OPTIONS advertises | high + medium | API8:2023 |
| `jwt` | weak secret, `alg:none`, missing `exp` | high + medium | API2:2023 |
| `idor_bola` | same object readable as two identities | medium | API1:2023 |
| `sqli_indicators` | path and query injection | high | API10:2023 |

Severity is not arbitrary: only `medium` and `high` are reachable today,
because no shipped scanner emits `low`, `info` or `critical`.

## Run it

```powershell
docker run --rm -d --name apishield-demo-target `
  --network mini_project_api_default -p 8765:8765 `
  -v "D:\Mini_project_Api\demo:/app:ro" -w /app `
  mini_project_api-backend:latest `
  uvicorn insecure_api:app --host 0.0.0.0 --port 8765
```

Check it is up: <http://localhost:8765/openapi.json>

## Scan it

1. Sign in at <http://localhost:5173>.
2. Create a project, then add a target with base URL
   `http://apishield-demo-target:8765` (the container name — the scan worker
   resolves it on the compose network, `localhost` would not work).
3. Import the OpenAPI document from `http://localhost:8765/openapi.json`.
4. Add **two** credentials (any names, type `bearer`, any values) so the
   IDOR/BOLA scanner has identities to replay with.
5. Run the scan, then open the results and the HTML/PDF/JSON report.

Stop the fixture when done:

```powershell
docker rm -f apishield-demo-target
```
