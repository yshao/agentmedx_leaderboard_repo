# A2A Streaming Connection Fix - Complete Plan

## Problem
GitHub Actions workflow fails with `httpcore.ConnectError: All connection attempts failed` when agentbeats-client tries to establish SSE streaming connection to green-agent.

## Root Cause
The green-agent's A2A server lacks CORS middleware, preventing cross-origin SSE streaming requests from agentbeats-client (running in separate Docker container).

---

## Fix Applied

### File: `medbench/medbench_judge.py`

#### Change 1: Add CORS Import (Line ~716)
```python
# Add health check and root info endpoints using middleware
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware  # <-- ADD THIS
```

#### Change 2: Add CORS Middleware FIRST, Before InfoMiddleware (Around Line 747)
```python
# Build the app and add middleware
app = server.build()

# CRITICAL: Add CORS MIDDLEWARE FIRST - must process before InfoMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)
app.add_middleware(InfoMiddleware)  # InfoMiddleware processes AFTER CORS
```

**Key Fix:** Middleware order matters! CORSMiddleware must be added FIRST so it processes requests BEFORE InfoMiddleware. This ensures CORS preflight OPTIONS requests are handled correctly.

---

## Build & Deploy Instructions

### 1. Build Docker Image
```bash
cd /mnt/c/Users/yshao/Desktop/2025/codes/ai_interview/agentx2_leader/source2/project2
docker build -f Dockerfile -t ghcr.io/yshao/medapp:latest-green-agent .
```

### 2. Push to GHCR
```bash
docker push ghcr.io/yshao/medapp:latest-green-agent
```

### 3. Trigger GitHub Workflow
```bash
cd /mnt/c/Users/yshao/Desktop/2025/codes/ai_interview/agentx2_leader/staging/agentmedx_leaderboard_repo
sed -i 's/# Trigger: .*/# Trigger: CORS-FIX-APPLIED/' scenario.toml
git add scenario.toml
git commit -m "Trigger workflow with CORS fix for A2A streaming"
git push origin evaluate-purple-agent-019ba9ee
```

---

## Expected Results

### Before Fix
```
green-agent | "GET /.well-known/agent-card.json HTTP/1.1" 200 OK
agentbeats-client | httpcore.ConnectError: All connection attempts failed
agentbeats-client exited with code 1
```

### After Fix
```
green-agent | "GET /.well-known/agent-card.json HTTP/1.1" 200 OK
agentbeats-client | Successfully connected to green-agent
green-agent | Processing message with GROQ_API_KEY
agentbeats-client | Received streaming response
[Assessment runs to completion]
```

---

## Files Modified

| File | Path | Change |
|------|------|--------|
| medbench_judge.py | `source2/project2/medbench/medbench_judge.py` | Added CORS middleware |
| Dockerfile | `source2/project2/Dockerfile` | Rebuild with changes |
| Docker Image | `ghcr.io/yshao/medapp:latest-green-agent` | Push new version |
