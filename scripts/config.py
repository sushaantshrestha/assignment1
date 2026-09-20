"""Central configuration for model calls (OpenAI-compatible endpoint).

Values are read from environment variables first so no credentials need to be
committed; fall back to the course-provided endpoint.
"""
import os

BASE_URL = os.environ.get("MBAX_BASE_URL", "http://dobolyi.com:9000/v1")
API_KEY = os.environ.get("MBAX_API_KEY", "6418")
MODEL = os.environ.get("MBAX_MODEL", "DeepSeek-V4-Flash-0731")

# Absolute path to the project's prompt template (keyed to repo layout).
PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompt.txt"
)

DATA_PATH = "data/Gift_Cards.jsonl.gz"
NRC_PATH = "data/NRC-emotion-lexicon-wordlevel-alphabetized-v0.92.txt"

# Core NRC emotions (excluding the two binary sentiment columns).
NRC_EMOTIONS = [
    "anger", "anticipation", "disgust", "fear", "joy",
    "sadness", "surprise", "trust",
]
NRC_EMOTIONS_SET = set(NRC_EMOTIONS)

# Fixed seed so balanced samples are reproducible.
SEED = 2026
