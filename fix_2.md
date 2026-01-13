# A2A Streaming Connection Fix - Middleware Order Issue

## Problem
GitHub Actions workflow fails with `httpcore.ConnectError: All connection attempts failed` when agentbeats-client tries to establish SSE streaming connection to green-agent.

## Root Cause
**Middleware order was wrong!** InfoMiddleware was processing requests BEFORE CORS could add headers, blocking CORS preflight OPTIONS requests.

## Evidence
```
14:48:14.434 - Agent card works: "GET /.well-known/agent-card.json HTTP/1.1" 200 OK
14:48:14.437 - SSE fails: httpcore.ConnectError: All connection attempts failed (3ms later)
```

The CORS middleware was added AFTER InfoMiddleware, meaning:
1. InfoMiddleware processed first
2. CORS preflight OPTIONS requests were blocked
3. SSE streaming connection couldn't be established

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

#### Change 2: Add CORS Middleware FIRST (Around Line 747)
```python
# Build the app and add middleware
app = server.build()

# CRITICAL: Add CORS MIDDLEWARE FIRST - must process before InfoMiddleware
# This ensures CORS preflight OPTIONS requests are handled correctly
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

**Key Insight:** In Starlette/ASGI middleware, the order matters! The first middleware added processes first during the request. CORSMiddleware MUST be added first to handle OPTIONS preflight requests before InfoMiddleware.

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
sed -i 's/# Trigger: .*/# Trigger: MIDDLEWARE-ORDER-FIX/' scenario.toml
git add scenario.toml
git commit -m "Trigger workflow with middleware order fix for A2A streaming"
git push origin evaluate-purple-agent-019ba9ee
```

---

## Expected Results

### Before Fix
```
green-agent | "GET /.well-known/agent-card.json HTTP/1.1" 200 OK
agentbeats-client | httpcore.ConnectError: All connection attempts failed
```

### After Fix
```
green-agent | "GET /.well-known/agent-card.json HTTP/1.1" 200 OK
agentbeats-client | OPTIONS request → 200 OK (CORS preflight)
agentbeats-client | SSE streaming connection established
green-agent | Processing message with GROQ_API_KEY
[Assessment runs to completion]
```

---

## Summary

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| SSE streaming fails | InfoMiddleware processes before CORS, blocking OPTIONS preflight | Swap middleware order - add CORS first |

**Files Modified:**
- `source2/project2/medbench/medbench_judge.py` - Fixed middleware order

**Docker Image to Rebuild:**
- `ghcr.io/yshao/medapp:latest-green-agent`
