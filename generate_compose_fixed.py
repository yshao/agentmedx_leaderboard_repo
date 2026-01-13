"""Generate Docker Compose configuration from scenario.toml

This is the corrected version with the env_str issue fixed.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli
    except ImportError:
        print("Error: tomli required. Install with: pip install tomli")
        sys.exit(1)
try:
    import tomli_w
except ImportError:
    print("Error: tomli-w required. Install with: pip install tomli-w")
    sys.exit(1)
try:
    import requests
except ImportError:
    print("Error: requests required. Install with: pip install requests")
    sys.exit(1)


AGENTBEATS_API_URL = "https://agentbeats.dev/api/agents"


def fetch_agent_info(agentbeats_id: str) -> dict:
    """Fetch agent info from agentbeats.dev API."""
    url = f"{AGENTBEATS_API_URL}/{agentbeats_id}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"Error: Failed to fetch agent {agentbeats_id}: {e}")
        sys.exit(1)
    except requests.exceptions.JSONDecodeError:
        print(f"Error: Invalid JSON response for agent {agentbeats_id}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed for agent {agentbeats_id}: {e}")
        sys.exit(1)


def get_image_port(image_name: str) -> int:
    """Detect the exposed port from a Docker image using docker inspect."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format={{json .Config.ExposedPorts}}", image_name],
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
        if result.returncode != 0:
            # Image not available locally, try to pull it
            print(f"Image {image_name} not found locally, pulling...")
            pull_result = subprocess.run(
                ["docker", "pull", image_name],
                capture_output=True,
                text=True,
                timeout=300,
                check=False
            )
            if pull_result.returncode != 0:
                print(f"Warning: Failed to pull image {image_name}, using default port {DEFAULT_PORT}")
                return DEFAULT_PORT
            # Retry inspect after pulling
            result = subprocess.run(
                ["docker", "inspect", "--format={{json .Config.ExposedPorts}}", image_name],
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            if result.returncode != 0:
                print(f"Warning: Could not inspect image {image_name} after pulling, using default port {DEFAULT_PORT}")
                return DEFAULT_PORT

        exposed_ports = json.loads(result.stdout)
        if not exposed_ports:
            print(f"No exposed ports found for {image_name}, using default port {DEFAULT_PORT}")
            return DEFAULT_PORT

        # Get the first TCP port (e.g., "9008/tcp" -> 9008)
        for port_str in exposed_ports.keys():
            if "/tcp" in port_str:
                port = int(port_str.split("/")[0])
                print(f"Detected port {port} for image {image_name}")
                return port

        print(f"Warning: No TCP port found for {image_name}, using default port {DEFAULT_PORT}")
        return DEFAULT_PORT
    except subprocess.TimeoutExpired:
        print(f"Warning: Docker inspect timed out for {image_name}, using default port {DEFAULT_PORT}")
        return DEFAULT_PORT
    except json.JSONDecodeError:
        print(f"Warning: Could not parse docker inspect output for {image_name}, using default port {DEFAULT_PORT}")
        return DEFAULT_PORT
    except Exception as e:
        print(f"Warning: Error inspecting image {image_name}: {e}, using default port {DEFAULT_PORT}")
        return DEFAULT_PORT


COMPOSE_PATH = "docker-compose.yml"
A2A_SCENARIO_PATH = "a2a-scenario.toml"
ENV_PATH = ".env.example"

DEFAULT_PORT = 9009
DEFAULT_ENV_VARS = {"PYTHONUNBUFFERED": "1"}

COMPOSE_TEMPLATE = """# Auto-generated from scenario.toml

services:
  green-agent:
    image: {green_image}
    platform: linux/amd64
    container_name: green-agent
    environment:{green_env}
    ports:
      - "{green_port}:{green_port}"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{green_port}/health"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: