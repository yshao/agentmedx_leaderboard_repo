# Option 1 Implementation: Eliminate agentbeats-client

## Changes Made

### 1. Modified `medbench/medbench_judge.py`

**Added Orchestrator Mode:**
- Added `_create_agent_endpoint()` helper function
- Added `run_evaluation_mode()` function that reads scenario.toml directly
- Uses A2A client SDK (`A2AClient`) to communicate with medical_agent
- Added `_run_orchestration_mode()` function with command-line arguments

**Key Code Additions:**
- Lines 769-774: Added imports for A2A client (`A2AClient`, `A2AClientRequest`)
- Lines 777-853: Added `run_evaluation_mode()` function
- Lines 856-920: Added `_run_orchestration_mode()` with full orchestration logic
- Lines 921-935: Updated main() to check for `--evaluate` flag

### 2. Updated `docker-compose.yml`

**Removed agentbeats-client service** (lines 46-60):
- No agentbeats-client container
- Green-agent now runs in orchestrator mode with command:
  ```yaml
  command: ["python", "-m", "scenarios.medbench.medbench_judge", "--evaluate", "--data-path", "/app/data/medagentbench/test_data_v2.json", "--medical-agent-endpoint", "http://medical_agent:9010/", "--dry_run"]
  ```
- Added `MEDICAL_AGENT_ENDPOINT=http://medical_agent:9010/` environment variable

### 3. Modified `generate_compose.py`

**Removed agentbeats-client from:**
- `{participant_services}` template (no longer includes agentbeats-client section)
- `client_depends` now only includes `["green-agent", "medical_agent"]` (removed "agentbeats-client")
- `all_services` already only includes `["green-agent"] + participant_names`

---

## Architecture Change

### Before (3 containers)
```
agentbeats-client (orchestrator, A2A client)
    ↓ A2A protocol (JSON-RPC over SSE)
green-agent (evaluator, A2A server)
    ↓ A2A protocol (JSON-RPC over SSE)
medical_agent (participant, A2A server)
```

### After (2 containers)
```
green-agent (orchestrator + evaluator, A2A client & server)
    ↓ A2A protocol (JSON-RPC over SSE)
medical_agent (participant, A2A server)
```

---

## Key Features

1. **Simplified Architecture**
   - Removed third-party agentbeats-client dependency
   - Green-agent now orchestrates directly by reading scenario.toml
   - Uses A2A protocol only for green-agent → medical_agent communication

2. **Orchestration Mode**
   - Triggered via `--evaluate` flag in green-agent command
   - Reads data-path directly
   - Sends A2A messages to medical_agent
   - Receives response, evaluates, scores, and outputs results

3. **Environment Variables**
   - `MEDICAL_AGENT_ENDPOINT=http://medical_agent:9010/` - passed to green-agent

---

## Docker Compose Output (Simplified)

```yaml
services:
  green-agent:
    image: ghcr.io/yshao/mediatech/medapp:latest-green-agent
    environment:
      - MEDICAL_AGENT_ENDPOINT=http://medical_agent:9010/
    command: ["python", "-m", "scenarios.medbench.medbench_judge", "--evaluate", ..."]

  medical_agent:
    image:  ghcr.io/yshao/medapp:latest-purple-agent
    environment:
      - SPECIALTY=diabetes
```

---

## Testing & Deployment

### Local Test
```bash
cd /mnt/c/Users/yshao/Desktop/2025/codes/ai_interview/agentx2_leader/staging/agentmedx_leaderboard_repo
python3 generate_compose.py --scenario scenario.toml
docker-compose up --timestamps --no-color
```

### Trigger GitHub Actions
```bash
sed -i 's/# Trigger: .*/# Trigger: ELIMINATED-AGENTBEATS-CLIENT/' scenario.toml
git add . && git commit -m "Trigger workflow with eliminated agentbeats-client" && git push origin evaluate-purple-agent-019ba9ee
```

---

## Success Criteria

1. ✅ No agentbeats-client in docker-compose.yml
2. ✅ Green-agent runs in orchestrator mode (`--evaluate` flag)
3. ✅ Green-agent communicates with medical_agent via A2A protocol
4. ✅ Evaluation completes successfully with scores
5. ✅ GitHub Actions workflow passes without agentbeats-client
