# Debug Plan: AgentMedX SSE Connection Failure

## Problem

The agentbeats-client cannot establish SSE (Server-Sent Events) connection to the green-agent for A2A protocol communication.

### Error Details
```
httpcore.ConnectError: All connection attempts failed
Location: httpx_sse/_api.py:aconnect_sse()
Context: agentbeats-client trying to connect to green-agent:9008 via POST
```

### What Works
- ✅ green-agent running on port 9008
- ✅ medical_agent running on port 9010
- ✅ Healthchecks pass for both
- ✅ green-agent serves agent-card.json: `GET /.well-known/agent-card.json HTTP/1.1 200 OK`

### What Fails
- ❌ agentbeats-client SSE connection to green-agent:9008 fails at TCP level

## Root Cause Analysis

**Architecture:**
- green_agent: Uses A2A SDK's `A2AStarletteApplication` for SSE streaming
- agentbeats-client: Uses `httpx_sse` for SSE connections

**Hypothesis:** A2A SDK version mismatch or SSE endpoint configuration issue in medapp

## Debugging Steps

### Step 1: Test Locally
```bash
cd /staging/agentmedx_leaderboard_repo
docker compose up
```

**Expected:** See if agentbeats-client can connect via SSE locally

### Step 2: Check SSE Endpoint
```bash
# After docker compose up, test SSE endpoint directly:
curl -X POST http://localhost:9008/ \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}' \
  -v --sse
```

### Step 3: Check A2A SDK Version
```bash
cat /source2/project2/pyproject.toml | grep -E "a2a|starlette|sse"
```

### Step 4: Verify Dependencies
```bash
# Check if SSE-related packages are installed
docker exec green-agent pip list | grep -E "a2a|sse|starlette"
```

## Next Steps Based on Results

| Local SSE Works | Local SSE Fails |
|-----------------|----------------|
| Issue is GitHub Actions specific | Issue is in medapp A2A SDK implementation |

### GitHub Actions Network Issue → Solution:
- Use self-hosted runner
- Or use dry_run mode (mock evaluation)

### Medapp Issue → Solution:
- Update A2A SDK to compatible version
- Add missing SSE dependencies
- Configure SSE endpoint properly
