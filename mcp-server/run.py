"""Entrypoint for MCP clients. Adds this dir to sys.path so `study_agent_mcp` imports
work without a pip install step."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from study_agent_mcp.server import mcp  # noqa: E402

if __name__ == "__main__":
    mcp.run()
