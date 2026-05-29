"""
Analysis Engine: DeepSeek integration and GSR response generation
"""

import json
import time
import random
import requests
from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL,
    ACTIVE_VARIANT, VARIANT_INFO, LEAKED_ITEMS, CONFIDENTIAL_ITEMS,
    GSR_CONFIG
)


def analyze_question_cit(transcript: str, candidate_id: str, team: str) -> dict:
    """
    Analyze a question using DeepSeek for CIT (Prosecution).
    Returns GSR response data and analysis.
    """
    variant = VARIANT_INFO[ACTIVE_VARIANT]
    is_guilty = (candidate_id == variant["guilty_suspect"])

    prompt = f"""You are a CIT (Concealed Information Test) analysis engine in a forensic psychology simulation system. Analyze the interrogation question and return simulated GSR data.

Current variant: {ACTIVE_VARIANT} ({variant['description']})
Interviewee: {candidate_id}
Is guilty suspect: {'Yes' if is_guilty else 'No'}

## Leaked information (publicly reported by media):
{', '.join(LEAKED_ITEMS)}

## Confidential information (known only to perpetrator and investigators):
{', '.join(CONFIDENTIAL_ITEMS)}

## Analysis rules:
1. Question involves **confidential** info AND interviewee is guilty -> High GSR (70-95)
2. Question involves **confidential** info but interviewee is innocent -> Baseline GSR (20-40), innocent person doesn't know these details
3. Question involves **leaked** info -> Medium GSR (35-65), both sides may react to known public info
4. Irrelevant/baseline question -> Low GSR (20-40)
5. Question quality: clear, specific questions produce clearer GSR signals; vague questions produce more noise

Analyze the following interrogation question and return the result as JSON (no markdown code block markers, pure JSON only):

Question: "{transcript}"

Response format:
{{
  "gsr_value": number between 0-100,
  "category": "confidential" or "leaked" or "irrelevant",
  "confidence": confidence between 0-1,
  "question_quality": "good" or "medium" or "poor",
  "reasoning": "brief analysis explanation (English)"
}}"""

    return _call_deepseek(prompt)


def analyze_question_cqt(transcript: str, candidate_id: str, team: str) -> dict:
    """
    Analyze a question using DeepSeek for CQT (Defence).
    Returns GSR response data with R/C ratio analysis.
    """
    variant = VARIANT_INFO[ACTIVE_VARIANT]
    is_guilty = (candidate_id == variant["guilty_suspect"])
    guilty_range = variant["cqt_guilty_ratio_range"]
    innocent_range = variant["cqt_innocent_ratio_range"]

    prompt = f"""You are a CQT (Comparison Question Test) analysis engine in a forensic psychology simulation system. Analyze the interrogation question and return simulated GSR data.

Current variant: {ACTIVE_VARIANT} ({variant['description']})
Interviewee: {candidate_id}
Is guilty suspect: {'Yes' if is_guilty else 'No'}

## CQT question types:
- **Relevant**: Questions directly about the crime facts
- **Comparison**: Questions about general misconduct, used for comparison with relevant questions
- **Irrelevant**: Neutral questions unrelated to the case

## Analysis rules:
1. Relevant question + guilty suspect -> High GSR, R/C ratio in range {guilty_range[0]}-{guilty_range[1]}, "deception detected"
2. Relevant question + innocent suspect -> Medium GSR, R/C ratio in range {innocent_range[0]}-{innocent_range[1]} (weaker deception signal from anxiety/compliance)
3. Comparison question -> Medium GSR, both types produce some response
4. Irrelevant question -> Low GSR baseline

Analyze the following CQT question and return the result as JSON (no markdown code block markers, pure JSON only):

Question: "{transcript}"

Response format:
{{
  "gsr_value": number between 0-100,
  "question_type": "relevant" or "comparison" or "irrelevant",
  "rc_ratio": ratio based on suspect type and question type (1.0-3.0),
  "deception_detected": true or false,
  "confidence": confidence between 0-1,
  "question_quality": "good" or "medium" or "poor",
  "reasoning": "brief analysis explanation (English)"
}}"""

    return _call_deepseek(prompt)


def _call_deepseek(prompt: str) -> dict:
    """Call DeepSeek API and parse response."""
    if not DEEPSEEK_API_KEY:
        return _fallback_analysis(prompt)

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "You are an analysis engine for a forensic psychology simulation system. You return only JSON-formatted results, with no additional text or markdown formatting."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 500,
    }

    try:
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"].strip()
        # Remove markdown code block markers if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        result = json.loads(content)
        # Ensure required fields
        result.setdefault("gsr_value", 50)
        result.setdefault("confidence", 0.5)
        result.setdefault("category", "irrelevant")
        result.setdefault("question_quality", "medium")
        result.setdefault("reasoning", "Analysis complete")
        return result

    except Exception as e:
        print(f"DeepSeek API error: {e}")
        return _fallback_analysis(prompt)


def _fallback_analysis(prompt: str) -> dict:
    """
    Fallback analysis when DeepSeek API is unavailable.
    Uses keyword matching for basic analysis.
    """
    transcript = prompt.split('Question: "')[1].split('"')[0] if 'Question: "' in prompt else ""
    transcript_lower = transcript.lower()

    # Check for confidential items
    for item in CONFIDENTIAL_ITEMS:
        if item.lower() in transcript_lower:
            is_cqt = "cqt" in prompt.lower()
            if is_cqt:
                return {
                    "gsr_value": random.uniform(70, 90),
                    "question_type": "relevant",
                    "rc_ratio": round(random.uniform(1.8, 2.5), 2),
                    "deception_detected": True,
                    "confidence": 0.85,
                    "question_quality": "good",
                    "reasoning": "Question involves confidential information, possible deceptive response detected",
                }
            return {
                "gsr_value": random.uniform(70, 90),
                "category": "confidential",
                "confidence": 0.85,
                "question_quality": "good",
                "reasoning": "Question involves confidential information, guilty suspect shows high GSR response",
            }

    # Check for leaked items
    for item in LEAKED_ITEMS:
        if item.lower() in transcript_lower:
            return {
                "gsr_value": random.uniform(40, 60),
                "category": "leaked",
                "confidence": 0.7,
                "question_quality": "medium",
                "reasoning": "Question involves publicly leaked information, moderate GSR response expected",
            }

    # Irrelevant
    return {
        "gsr_value": random.uniform(20, 35),
        "category": "irrelevant",
        "confidence": 0.6,
        "question_quality": "poor",
        "reasoning": "Question does not relate to known case information, GSR at baseline level",
    }


def _smooth_random_walk(length: int, step_scale: float = 1.0, smooth_window: int = 5) -> list[float]:
    """Generate a smooth low-frequency random envelope (random walk + moving average)."""
    if length <= 0:
        return []
    walk = [0.0]
    for _ in range(length - 1):
        walk.append(walk[-1] + random.gauss(0, step_scale))
    half = max(1, smooth_window // 2)
    smoothed = []
    for i in range(length):
        lo = max(0, i - half)
        hi = min(length, i + half + 1)
        smoothed.append(sum(walk[lo:hi]) / (hi - lo))
    return smoothed


def generate_gsr_waveform(analysis: dict, duration_seconds: int | None = None) -> list:
    """
    Generate a realistic GSR waveform with smooth but varied shape and amplitude.
    Returns list of {timestamp, value} points.
    """
    sample_rate = GSR_CONFIG["sampling_rate_hz"]
    if duration_seconds is None:
        duration_seconds = random.randint(13, 17)
    total_points = duration_seconds * sample_rate

    base_gsr = analysis.get("gsr_value", 30)
    # Per-response variation in peak height and baseline level
    peak_gsr = base_gsr * random.uniform(0.86, 1.14)
    baseline = GSR_CONFIG["baseline_mean"] + random.uniform(-5, 5)
    noise_amp = GSR_CONFIG["noise_amplitude"] * random.uniform(0.9, 1.35)

    response_start = int(sample_rate * random.uniform(0.18, 0.28))
    rise_len = max(8, int(sample_rate * random.uniform(0.8, 1.3)))
    recover_len = max(12, int(sample_rate * random.uniform(2.4, 3.4)))

    envelope = _smooth_random_walk(total_points, step_scale=0.55, smooth_window=7)
    env_scale = random.uniform(2.5, 6.5)

    waveform = []
    for i in range(total_points):
        progress = i / total_points
        env = envelope[i] * env_scale

        if i < int(sample_rate * 0.1):
            val = baseline + env + random.gauss(0, noise_amp)
        elif i < response_start:
            val = baseline + env * 0.6 + random.gauss(0, noise_amp) + random.uniform(0, 2.5)
        elif i < response_start + rise_len:
            rise_progress = (i - response_start) / rise_len
            # Slightly non-linear rise for more natural shape
            rise_curve = rise_progress ** random.uniform(0.85, 1.15)
            val = baseline + (peak_gsr - baseline) * rise_curve + env * 0.4 + random.gauss(0, noise_amp * 0.5)
        elif i < response_start + rise_len + recover_len:
            rec_progress = (i - response_start - rise_len) / recover_len
            val = baseline + (peak_gsr - baseline) * (1 - rec_progress * random.uniform(0.65, 0.82))
            val += env * 0.35 + random.gauss(0, noise_amp * 0.4)
        else:
            tail = (i - response_start - rise_len - recover_len) / max(1, sample_rate * 8)
            lingering = (peak_gsr - baseline) * random.uniform(0.08, 0.14) * max(0, 1 - tail)
            val = baseline + lingering + env * 0.25 + random.gauss(0, noise_amp * 0.35)

        val = max(0, min(100, val))
        waveform.append({"t": round(progress * duration_seconds, 2), "v": round(val, 2)})

    # Light smoothing — keeps curve readable while preserving variation
    smoothed = []
    for i in range(len(waveform)):
        lo = max(0, i - 1)
        hi = min(len(waveform), i + 2)
        avg = sum(p["v"] for p in waveform[lo:hi]) / (hi - lo)
        smoothed.append({"t": waveform[i]["t"], "v": round(avg, 2)})

    return smoothed
