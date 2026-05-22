"""Configuration for Lumen Industries multi-agent system."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# API Key
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Model hierarchy for cost efficiency
MODEL_EXECUTIVE = "claude-opus-4-7"   # COO: complex orchestration + adaptive thinking
MODEL_DIRECTOR = "claude-sonnet-4-6"  # Directors: balanced
MODEL_WORKER = "claude-haiku-4-5"     # Workers: fast tasks

# Output directory
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Company info
COMPANY_NAME = "Lumen Industries"
