"""
CIT/CQT System - Flask Application
Legal Psychology Murder Case Simulation
NYU Shanghai • Fall 2026
"""

import os
import json
import uuid
import datetime
from io import BytesIO
from flask import (
    Flask, render_template, request, jsonify, session, url_for, redirect, abort, send_file
)
import requests

from config import (
    SECRET_KEY, TEAM_PASSWORDS, TEAM_NAMES, CANDIDATES,
    ACTIVE_VARIANT, VARIANT_INFO, ADMIN_PASSWORD,
    ELEVENLABS_API_KEY, ELEVENLABS_STT_URL, ELEVENLABS_STT_MODEL,
)
from analysis_engine import (
    analyze_question_cit, analyze_question_cqt, generate_gsr_waveform
)

app = Flask(__name__)
app.secret_key = SECRET_KEY

SESSION_DIR = os.path.join(os.path.dirname(__file__), "data", "sessions")
os.makedirs(SESSION_DIR, exist_ok=True)
# Keep full waveforms server-side (avoid cookie size limits).
RUNTIME_WAVEFORMS: dict[str, dict[str, list]] = {}


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Login page."""
    return render_template("login.html", teams=TEAM_NAMES)


@app.route("/login", methods=["POST"])
def login():
    """Authenticate team login."""
    team = request.form.get("team")
    password = request.form.get("password")

    if team not in TEAM_PASSWORDS:
        return jsonify({"success": False, "error": "Invalid team selection"})

    if password != TEAM_PASSWORDS[team]:
        return jsonify({"success": False, "error": "Incorrect password"})

    session["team"] = team
    session["team_name"] = TEAM_NAMES[team]
    session["session_id"] = str(uuid.uuid4())
    session["questions"] = []

    return jsonify({"success": True})


@app.route("/dashboard")
def dashboard():
    """Role/interviewee selection page."""
    if "team" not in session:
        return redirect(url_for("index"))

    team = session["team"]
    system_type = "CIT - Concealed Information Test" if team == "prosecution" else "CQT - Comparison Question Test"
    return render_template(
        "dashboard.html",
        team_name=session["team_name"],
        system_type=system_type,
        candidates=CANDIDATES[team],
        active_variant=ACTIVE_VARIANT,
    )


@app.route("/interview/<candidate_id>")
def interview(candidate_id):
    """Main interview interface with GSR waveform display."""
    if "team" not in session:
        return redirect(url_for("index"))

    team = session["team"]
    candidate = None
    for c in CANDIDATES[team]:
        if c["id"] == candidate_id:
            candidate = c
            break

    if not candidate:
        return redirect(url_for("dashboard"))

    session["current_candidate"] = candidate_id
    session["candidate_name"] = candidate["name"]

    system_type = "CIT - Concealed Information Test" if team == "prosecution" else "CQT - Comparison Question Test"
    return render_template(
        "interview.html",
        team_name=session["team_name"],
        system_type=system_type,
        candidate=candidate,
        variant_info=VARIANT_INFO[ACTIVE_VARIANT],
    )


@app.route("/api/analyze", methods=["POST"])
def analyze_text():
    """
    Receive transcript text (from browser SpeechRecognition),
    send to DeepSeek for analysis, generate GSR waveform.
    """
    if "team" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    transcript = data.get("transcript", "").strip()
    candidate_id = data.get("candidate_id", session.get("current_candidate", "unknown"))
    team = session["team"]

    if not transcript:
        return jsonify({"error": "Empty transcript"}), 400

    # Step 1: Analyze with DeepSeek
    if team == "prosecution":
        analysis = analyze_question_cit(transcript, candidate_id, team)
    else:
        analysis = analyze_question_cqt(transcript, candidate_id, team)

    # Step 2: Generate GSR waveform
    waveform = generate_gsr_waveform(analysis)

    # Step 3: Save question record (strip waveform from session to avoid 4KB cookie limit)
    question_record = {
        "id": str(uuid.uuid4()),
        "team": team,
        "candidate_id": candidate_id,
        "candidate_name": session.get("candidate_name", candidate_id),
        "timestamp": datetime.datetime.now().isoformat(),
        "transcript": transcript,
        "analysis": analysis,
        "waveform": waveform,  # full waveform only for this response
    }

    # Store full waveform server-side and lightweight record in session.
    session_id = session.get("session_id")
    if session_id:
        RUNTIME_WAVEFORMS.setdefault(session_id, {})[question_record["id"]] = waveform

    # Store lightweight version in session (no waveform to avoid cookie overflow)
    session_record = {k: v for k, v in question_record.items() if k != "waveform"}
    session_record["waveform_summary"] = {
        "gsr_value": analysis.get("gsr_value", 50),
        "peak_time": len(waveform) // 2 if waveform else 0,
        "duration": len(waveform),
    }

    questions = session.get("questions", [])
    questions.append(session_record)
    session["questions"] = questions

    return jsonify({
        "success": True,
        "transcript": transcript,
        "analysis": analysis,
        "waveform": waveform,
        "question_id": question_record["id"],
    })


@app.route("/api/transcribe", methods=["POST"])
def transcribe_audio():
    """Transcribe uploaded audio via ElevenLabs (fallback when browser STT fails)."""
    if "team" not in session:
        return jsonify({"error": "Not logged in"}), 401

    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "No audio file"}), 400

    transcript, err_detail = transcribe_with_elevenlabs(audio_file)
    transcript = (transcript or "").strip()

    if not transcript:
        return jsonify({
            "error": "Transcription failed",
            "detail": err_detail or "Empty transcription result",
        }), 422

    return jsonify({"success": True, "transcript": transcript})


@app.route("/api/questions")
def get_questions():
    """Get all questions asked in the current session."""
    if "team" not in session:
        return jsonify({"error": "未登录"}), 401

    questions = session.get("questions", [])
    summary = []
    for q in questions:
        summary.append({
            "id": q["id"],
            "candidate_name": q["candidate_name"],
            "timestamp": q["timestamp"],
            "transcript": q["transcript"],
            "analysis": {k: v for k, v in q["analysis"].items() if k != "reasoning"},
            "waveform_summary": q.get("waveform_summary", {}),
        })
    return jsonify(summary)


@app.route("/api/save_session", methods=["POST"])
def save_session():
    """Save the current session data to disk."""
    if "team" not in session:
        return jsonify({"error": "未登录"}), 401

    team = session["team"]
    session_id = session["session_id"]
    questions = session.get("questions", [])

    session_waveforms = RUNTIME_WAVEFORMS.get(session_id, {})
    questions_with_waveform = []
    for q in questions:
        enriched = dict(q)
        enriched["waveform"] = session_waveforms.get(q["id"], [])
        questions_with_waveform.append(enriched)

    session_data = {
        "session_id": session_id,
        "team": team,
        "team_name": session["team_name"],
        "variant": ACTIVE_VARIANT,
        "created_at": datetime.datetime.now().isoformat(),
        "questions": questions_with_waveform,
    }

    filename = f"{team}_{session_id[:8]}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(SESSION_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    return jsonify({
        "success": True,
        "filename": filename,
        "filepath": filepath,
    })


@app.route("/results")
def view_results():
    """View results page."""
    if "team" not in session:
        return redirect(url_for("index"))

    questions = session.get("questions", [])
    team = session["team"]
    system_type = "CIT - Concealed Information Test" if team == "prosecution" else "CQT - Comparison Question Test"

    return render_template(
        "results.html",
        team_name=session["team_name"],
        system_type=system_type,
        questions=questions,
        session_id=session["session_id"],
    )


@app.route("/logout")
def logout():
    """Logout and clear session."""
    session.clear()
    return redirect(url_for("index"))


# ─── ElevenLabs Integration ──────────────────────────────────────────────────

def transcribe_with_elevenlabs(audio_file) -> tuple[str, str]:
    """
    Send audio to ElevenLabs Speech-to-Text API.
    Returns (transcript, error_detail). transcript is empty on failure.
    """
    if not ELEVENLABS_API_KEY:
        return "", "ELEVENLABS_API_KEY is not configured in .env"

    try:
        audio_file.seek(0)
        audio_bytes = audio_file.read()
        if not audio_bytes or len(audio_bytes) < 100:
            return "", "Recording too short or empty — speak at least 2–3 seconds"

        filename = audio_file.filename or "recording.webm"
        content_type = audio_file.content_type or "audio/webm"
        files = {"file": (filename, audio_bytes, content_type)}
        data = {"model_id": ELEVENLABS_STT_MODEL, "language_code": "en"}
        headers = {"xi-api-key": ELEVENLABS_API_KEY}

        resp = requests.post(
            ELEVENLABS_STT_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )

        if not resp.ok:
            try:
                body = resp.json()
                detail = body.get("detail")
                if isinstance(detail, list):
                    msg = "; ".join(
                        d.get("msg", str(d)) for d in detail if isinstance(d, dict)
                    )
                elif isinstance(detail, dict):
                    msg = detail.get("message") or str(detail)
                else:
                    msg = str(detail) if detail else resp.text[:300]
            except Exception:
                msg = resp.text[:300]
            print(f"ElevenLabs API error {resp.status_code}: {msg}")
            return "", f"ElevenLabs API ({resp.status_code}): {msg}"

        result = resp.json()
        text = (result.get("text") or "").strip()
        if not text:
            return "", "ElevenLabs returned empty text — try speaking louder or longer"
        return text, ""

    except requests.RequestException as e:
        print(f"ElevenLabs request error: {e}")
        return "", f"Network error calling ElevenLabs: {e}"
    except Exception as e:
        print(f"ElevenLabs error: {e}")
        return "", str(e)


# ─── Main ────────────────────────────────────────────────────────────────────

# ─── Admin Routes ──────────────────────────────────────────────────────────────

@app.route("/admin", methods=["GET"])
def admin_login():
    """Admin login page for session data download."""
    return render_template("admin.html", error=None)


@app.route("/admin/verify", methods=["POST"])
def admin_verify():
    """Verify admin password."""
    password = request.form.get("password", "")
    if password == ADMIN_PASSWORD:
        session["admin"] = True
        return redirect(url_for("admin_panel"))
    return render_template("admin.html", error="Incorrect password")


@app.route("/admin/panel")
def admin_panel():
    """Admin panel showing all saved session files."""
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    files = []
    if os.path.exists(SESSION_DIR):
        for f in sorted(os.listdir(SESSION_DIR), reverse=True):
            if f.endswith(".json"):
                filepath = os.path.join(SESSION_DIR, f)
                stat = os.stat(filepath)
                files.append({
                    "filename": f,
                    "size": stat.st_size,
                    "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

    return render_template("admin_panel.html", files=files)


@app.route("/admin/download/<filename>")
def admin_download_file(filename):
    """Download a specific session file."""
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    safe_path = os.path.normpath(os.path.join(SESSION_DIR, os.path.basename(filename)))
    if not safe_path.startswith(os.path.normpath(SESSION_DIR)) or not os.path.exists(safe_path):
        abort(404)

    return send_file(safe_path, as_attachment=True, download_name=filename)


@app.route("/admin/download_report/<filename>")
def admin_download_report(filename):
    """Download a polished PDF report with question-waveform mapping."""
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    safe_path = os.path.normpath(os.path.join(SESSION_DIR, os.path.basename(filename)))
    if not safe_path.startswith(os.path.normpath(SESSION_DIR)) or not os.path.exists(safe_path):
        abort(404)

    try:
        with open(safe_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        abort(500)

    questions = data.get("questions", [])
    if not questions:
        abort(400)

    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
    except Exception:
        return jsonify({"error": "matplotlib is required for PDF report export"}), 500

    report_name = os.path.splitext(os.path.basename(filename))[0] + "_report.pdf"
    pdf_buffer = BytesIO()

    with PdfPages(pdf_buffer) as pdf:
        for idx, q in enumerate(questions, start=1):
            fig = plt.figure(figsize=(11.69, 8.27))  # A4 landscape
            fig.patch.set_facecolor("#ffffff")

            gs = fig.add_gridspec(2, 1, height_ratios=[1, 2.2], hspace=0.25)
            ax_meta = fig.add_subplot(gs[0])
            ax_meta.axis("off")
            ax_wave = fig.add_subplot(gs[1])

            transcript = (q.get("transcript") or "").strip()
            analysis = q.get("analysis") or {}
            gsr_value = analysis.get("gsr_value", "--")
            cat = analysis.get("category") or analysis.get("question_type") or "irrelevant"
            confidence = analysis.get("confidence")
            confidence_txt = f"{int(confidence * 100)}%" if isinstance(confidence, (int, float)) else "--"
            timestamp = (q.get("timestamp") or "").replace("T", " ")[:19]

            meta_lines = [
                f"Session: {data.get('session_id', '')[:16]}    Team: {data.get('team_name', data.get('team', ''))}",
                f"Question #{idx}    Subject: {q.get('candidate_name', q.get('candidate_id', '--'))}    Time: {timestamp}",
                f"GSR: {gsr_value}    Category: {cat}    Confidence: {confidence_txt}",
                f"Question: {transcript}",
            ]
            ax_meta.text(
                0.01, 0.95, "\n".join(meta_lines),
                va="top", ha="left", fontsize=11, family="DejaVu Sans"
            )

            waveform = q.get("waveform") or []
            xs = [p.get("t", i) for i, p in enumerate(waveform)] if waveform else []
            ys = [p.get("v", 0) for p in waveform] if waveform else []
            if xs and ys:
                ax_wave.plot(xs, ys, color="#00a7d6", linewidth=2.2)
                ax_wave.fill_between(xs, ys, 0, color="#00a7d6", alpha=0.12)
            else:
                ax_wave.text(0.5, 0.5, "No waveform data found for this question.",
                             transform=ax_wave.transAxes, ha="center", va="center", fontsize=12)

            ax_wave.set_ylim(0, 100)
            ax_wave.set_xlabel("Time (s)")
            ax_wave.set_ylabel("GSR")
            ax_wave.set_title("Waveform Response", fontsize=12, pad=10)
            ax_wave.grid(True, linestyle="--", alpha=0.25)

            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=report_name,
        mimetype="application/pdf",
    )


@app.route("/admin/download_all")
def admin_download_all():
    """Download all session data as a single JSON bundle."""
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    all_sessions = []
    if os.path.exists(SESSION_DIR):
        for f in sorted(os.listdir(SESSION_DIR)):
            if f.endswith(".json"):
                filepath = os.path.join(SESSION_DIR, f)
                try:
                    with open(filepath, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                        all_sessions.append(data)
                except Exception:
                    pass

    bundle = {
        "export_time": datetime.datetime.now().isoformat(),
        "total_sessions": len(all_sessions),
        "sessions": all_sessions,
    }

    buffer = BytesIO()
    buffer.write(json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8"))
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"cit_cqt_all_sessions_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mimetype="application/json",
    )


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n{'='*60}")
    print(f"  CIT/CQT System Started")
    print(f"  URL: http://localhost:{port}")
    print(f"  Variant: {ACTIVE_VARIANT} ({VARIANT_INFO[ACTIVE_VARIANT]['description']})")
    print(f"  Prosecution password: {TEAM_PASSWORDS['prosecution']}")
    print(f"  Defense password: {TEAM_PASSWORDS['defence']}")
    print(f"  Admin: http://localhost:{port}/admin")
    print(f"{'='*60}\n")
    app.run(debug=True, host="0.0.0.0", port=port)
