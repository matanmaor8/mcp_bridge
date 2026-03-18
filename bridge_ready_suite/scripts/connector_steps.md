# ChatGPT Connector Steps

After `chatgpt_bridge_app/server.js` is running and ngrok is exposing port `8787`:

1. Copy the public HTTPS URL from ngrok
2. Append `/mcp`
3. In ChatGPT, add a connector/custom MCP endpoint using that full URL
4. If you set `MCP_BEARER_TOKEN` in `chatgpt_bridge_app/.env`, use the same bearer token when configuring the connector

Example endpoint:

```text
https://YOUR-NGROK-SUBDOMAIN.ngrok-free.app/mcp
```

Before connecting ChatGPT, you can test the bridge locally:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8787/run -ContentType 'application/json' -Body '{"task":"Improve logging in the sample repo and add tests","mode":"repo","repo":"sample_repo_template"}'
```
