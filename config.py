"""
CIT/CQT System Configuration
"""

import os
from pathlib import Path

# Load .env file manually (no external dependencies needed)
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                _key, _val = _key.strip(), _val.strip().strip("\"'")
                if _key not in os.environ:
                    os.environ[_key] = _val

# Flask
SECRET_KEY = os.environ.get("SECRET_KEY", "legal-psychology-2026-ta2-secret")

# API Keys
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# DeepSeek API
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ElevenLabs Speech-to-Text (Scribe v2)
ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
ELEVENLABS_STT_MODEL = "scribe_v2"

# Active variant: "A+" (Suspect A guilty) or "B+" (Suspect B guilty)
ACTIVE_VARIANT = "A+"

# Team passwords (change these before deployment)
TEAM_PASSWORDS = {
    "prosecution": "cit2026",
    "defence": "2026cqt",
}

# Team display names
TEAM_NAMES = {
    "prosecution": "Prosecution - CIT (Concealed Information Test)",
    "defence": "Defense - CQT (Comparison Question Test)",
}

# Admin password for downloading session data
ADMIN_PASSWORD = "775852114"

# Interviewee candidates
# Each team can interview different roles
CANDIDATES = {
    "prosecution": [
        {"id": "suspect_a", "name": "Suspect A", "type": "suspect"},
        {"id": "suspect_b", "name": "Suspect B", "type": "suspect"},
    ],
    "defence": [
        {"id": "suspect_a", "name": "Suspect A", "type": "suspect"},
        {"id": "suspect_b", "name": "Suspect B", "type": "suspect"},
    ],
}

# Leaked vs Confidential Information Database
# Items marked "leaked" are known to the public via media (Case File #010 release)
# Items marked "confidential" are known only to the perpetrator and investigators
LEAKED_ITEMS = [
    "weapon_type",
    "kitchen knife",
    "building_location",
    "victim_campus_status",
    "visiting researcher",
    "approximate_time_of_death",
    "sexual_assault_element",
    "attempted sexual assault",
    "multiple stab wounds",
    "staircase",
    "female victim",
    "campus crime",
    "N823",
    "movie club",
]

CONFIDENTIAL_ITEMS = [
    "specific_wound_count",
    "exact wound count",
    "number of stab wounds",
    "exact_body_position",
    "body position on landing",
    "items_missing_from_scene",
    "specific staircase location between floors",
    "between 7th and 8th floor",
    "wound_configuration_pattern",
    "wound pattern",
    "blood coagulation details",
    "body cooling curve",
    "algor mortis",
    "Henssge nomogram",
    "time_of_death_window_0550_0710",
    "05:50 to 07:10",
    "defensive wounds pattern",
    "kitchen knife brand",
    "fingerprint placement",
    "chain_of_custody_detail",
]

# Variant-specific ground truth
VARIANT_INFO = {
    "A+": {
        "description": "Suspect A+ guilty / Suspect B- innocent",
        "guilty_suspect": "suspect_a",
        "innocent_suspect": "suspect_b",
        "cqt_guilty_ratio_range": (1.8, 2.5),
        "cqt_innocent_ratio_range": (1.2, 1.5),
    },
    "B+": {
        "description": "Suspect B+ guilty / Suspect A- innocent",
        "guilty_suspect": "suspect_b",
        "innocent_suspect": "suspect_a",
        "cqt_guilty_ratio_range": (1.8, 2.5),
        "cqt_innocent_ratio_range": (1.2, 1.5),
    },
}

# GSR simulation parameters
GSR_CONFIG = {
    "baseline_mean": 25,
    "baseline_noise": 5,
    "leaked_response_mean": 50,
    "leaked_response_range": (35, 65),
    "confidential_response_mean": 80,
    "confidential_response_range": (70, 95),
    "irrelevant_response_mean": 30,
    "irrelevant_response_range": (20, 40),
    "response_delay_ms": 1500,
    "rise_time_ms": 2000,
    "recovery_time_ms": 5000,
    "sampling_rate_hz": 20,
    "habituation_factor": 0.85,
    "noise_amplitude": 3,
}
