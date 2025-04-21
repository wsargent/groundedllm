
export GITHUB_DYNAMIC_TOOLSETS=1
export GITHUB_PERSONAL_ACCESS_TOKEN=$(op read "op://Private/Github Personal Access Token Vault/token")
mcp-proxy --sse-port=8080 \
  --pass-environment \
  -- ./github-mcp-server stdio