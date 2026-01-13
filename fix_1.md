# A2A Protocol Version Mismatch - Fix Specification

## Problem Summary
The GitHub Actions workflow fails because agentbeats-client sends incorrect A2A message format to green-agent. The green-agent's A2A server expects JSON-RPC 2.0 format but receives incompatible message format.

## Debug Test Results

### ✅ Test 1: Agent Card Endpoint
```
GET /.well-known/agent-card.json → 200 OK
Agent card shows:
{
  "capabilities": {"streaming": true},
  "preferredTransport": "JSONRPC",
  "protocolVersion": "0.3.0"
}
```

### ✅ Test 2: OPTIONS CORS Preflight
```
OPTIONS / → 200 OK
CORS headers present:
- access-control-allow-methods: GET, POST, OPTIONS
- access-control-allow-origin: http://test
- access-control-allow-credentials: true
```

### ✅ Test 3: POST to Root (A2A Streaming)
```
POST / → 200 OK
Response: {"error":{"code":-32600,"message":"Request payload validation error"}}
```

### ✅ Test 4: Server Logs
```
ERROR:a2a.server.apps.jsonrpc.jsonrpc_app:Failed to validate base JSON-RPC request
```

---

## Root Cause: A2A Protocol Version Mismatch

**The A2A server IS working correctly!** It successfully:
- Handles CORS preflight requests
- Receives POST requests
- Validates A2A messages

**The problem:** Agentbeats-client sends the WRONG message format.

### Current Behavior
- **Agentbeats-client sends:** `{"message": "test"}`
- **Green-agent expects:** JSON-RPC 2.0 format: `{"method": "...", "params": {}, "id": "..."}`

### Evidence from Error
```json
{
  "error": {
    "code": -32600,
    "data": [{
      "type": "missing",
      "loc": ["method"],
      "msg": "Field required",
      "input": {"message": "test"}
    }],
    "message": "Request payload validation error"
  }
}
```

---

## Fix Options

### Option 1: Rebuild agentbeats-client with Correct A2A SDK ⭐ RECOMMENDED

**Target:** `ghcr.io/agentbeats/agentbeats-client:v1.0.0`

**Action:** Rebuild agentbeats-client Docker image with updated A2A SDK version.

**How:**
1. Check A2A SDK requirements in agentbeats-client source
2. Ensure correct `a2a-sdk` version that matches green-agent's `protocolVersion: "0.3.0"`
3. Build and push: `docker build -t ghcr.io/agentbeats/agentbeats-client:v1.0.1 .`

### Option 2: Add Compatibility Layer in green-agent (WORKAROUND)

**Target:** `medbench/medbench_judge.py`

**Action:** Wrap the A2A server with a compatibility layer that handles both old and new A2A message formats.

**How:**
```python
# Create a custom request handler wrapper
class A2ACompatibilityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Parse incoming request
        if scope['method'] == 'POST':
            # Check if it's old format or new format
            body = await scope['receive']()
            try:
                data = json.loads(body)
                # Old format: {"message": "test"}
                if "message" in data and "method" not in data:
                    # Convert to A2A JSON-RPC format
                    new_data = {
                        "method": "process_message",
                        "params": data,
                        "id": str(uuid4())
                    }
                    # Rewrite the body
                    scope['_body'] = json.dumps(new_data)
            except:
                pass
        # Continue to next middleware/handler
        return await self.app(scope, receive, send)
```

---

## Recommended Fix Steps

### Step 1: Update agentbeats-client A2A SDK

Check and update `a2a-sdk` version in agentbeats-client source:
```bash
# In agentbeats-client source tree
grep -r "a2a" requirements.txt pyproject.toml setup.py 2>/dev/null | head -20
```

Ensure `a2a-sdk` version matches or exceeds version `0.3.0` to match green-agent's protocolVersion.

### Step 2: Rebuild and Push agentbeats-client

```bash
# In agentbeats-client source directory
docker build -t ghcr.io/agentbeats/agentbeats-client:v1.0.1 .
docker push ghcr.io/agentbeats-client:v1.0.1
```

### Step 3: Update docker-compose.yml

Update agentbeats-client image tag:
```yaml
services:
  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.1  # Updated version
```

### Step 4: Trigger and Test

```bash
cd staging/agentmedx_leaderboard_repo
sed -i 's/# Trigger: .*/# Trigger: A2A-SDK-FIX/' scenario.toml
git add . && git commit -m "Trigger workflow with fixed A2A SDK version" && git push
```

---

## Expected Results

### Before Fix (Current)
```
POST / → 200 OK
Response: {"error":{"code":-32600,"message":"Request payload validation error"}}
agentbeats-client exits with connection error
```

### After Fix
```
POST / → 200 OK
Response: {"result": {"type": "text", "content": "..."}}
agentbeats-client successfully streams responses
Assessment runs to completion
```

---

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `ghcr.io/agentbeats/agentbeats-client:v1.0.0` | Rebuild with correct A2A SDK version | HIGH |
| `staging/agentmedx_leaderboard_repo/docker-compose.yml` | Update agentbeats-client image tag | MEDIUM |
| Source code of agentbeats-client | Update a2a-sdk version in requirements.txt | HIGH |
| `medbench/medbench_judge.py` | Add compatibility layer if rebuilding agentbeats-client not possible | LOW |

---

## Summary

**Root Cause:** A2A protocol version mismatch
**Fix:** Update agentbeats-client with correct A2A SDK version (≥0.3.0) to send proper JSON-RPC 2.0 messages
