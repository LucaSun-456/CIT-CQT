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


def generate_gsr_waveform(analysis: dict, duration_seconds: int = 15) -> list:
    """
    Generate a realistic GSR waveform data series based on analysis.
    Returns list of {timestamp, value} points.
    """
    sample_rate = GSR_CONFIG["sampling_rate_hz"]
    total_points = duration_seconds * sample_rate
    gsr_value = analysis.get("gsr_value", 30)
    baseline = GSR_CONFIG["baseline_mean"]
    noise_amp = GSR_CONFIG["noise_amplitude"]

    waveform = []
    response_start = int(sample_rate * 0.3)  # response starts after 30% of duration

    for i in range(total_points):
        progress = i / total_points

        if i < int(sample_rate * 0.1):
            # Initial baseline
            val = baseline + random.gauss(0, noise_amp)
        elif i < response_start:
            # Pre-response baseline with slight anticipation
            val = baseline + random.gauss(0, noise_amp) + random.uniform(0, 3)
        elif i < response_start + int(sample_rate * 2):
            # Rise phase (rapid increase over ~2 seconds)
            rise_progress = (i - response_start) / (sample_rate * 2)
            val = baseline + (gsr_value - baseline) * rise_progress + random.gauss(0, noise_amp * 0.8)
        elif i < response_start + int(sample_rate * 5):
            # Recovery phase (slow decrease over ~3 seconds)
            rec_progress = (i - response_start - int(sample_rate * 2)) / (sample_rate * 3)
            val = baseline + (gsr_value - baseline) * (1 - rec_progress * 0.7) + random.gauss(0, noise_amp * 0.6)
        else:
            # Post-response baseline with slight lingering elevation
            lingering = (gsr_value - baseline) * 0.15 * (1 - (i - response_start - int(sample_rate * 5)) / (sample_rate * 7))
            val = baseline + max(0, lingering) + random.gauss(0, noise_amp)

        val = max(0, min(100, val))
        waveform.append({"t": round(progress * duration_seconds, 2), "v": round(val, 2)})

    return waveform
