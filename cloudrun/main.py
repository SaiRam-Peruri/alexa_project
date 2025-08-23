import os, json, re
from flask import Flask, jsonify, request

app = Flask(__name__)
latest_data = {}

def speak(text: str):
    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {"type": "PlainText", "text": text},
            "shouldEndSession": True
        }
    })

def normalize_phrase(text: str) -> str:
    if not text:
        return ""
    # turn dots into spaces and strip non-alnum
    t = text.replace(".", " ")
    t = re.sub(r"[^a-zA-Z0-9 ]+", " ", t).lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def has_any(phrase: str, needles):
    return any(n in phrase for n in needles)

@app.route("/", methods=["GET", "POST"])
def alexa_handler():
    if request.method == "GET":
        return jsonify({"status": "ok", "message": "Alexa system monitor is live."})

    req = request.get_json(silent=True) or {}
    app.logger.info(f"Incoming Alexa payload: {json.dumps(req)[:2000]}")

    req_type = req.get("request", {}).get("type", "")
    if req_type == "LaunchRequest":
        return speak("Hi! You can ask about CPU, memory, storage, uptime, or say laptop status.")

    intent_obj = req.get("request", {}).get("intent", {}) or {}
    intent_name = intent_obj.get("name", "")
    input_transcript = req.get("request", {}).get("inputTranscript", "")  # often present
    phrase_from_transcript = normalize_phrase(input_transcript)
    app.logger.info(f"Intent: {intent_name} | Transcript: {phrase_from_transcript}")

    stats = (latest_data.get("stats") or {})
    summary = latest_data.get("summary")

    cpu = (stats.get("CPU") or {}).get("Usage (%)")
    mem = (stats.get("Memory") or {}).get("Used (%)")
    disk_free = (stats.get("Disk (C:)") or {}).get("Free (GB)")
    uptime = (stats.get("System Info") or {}).get("Uptime")

    def fnum(x, nd=1):
        try:
            return round(float(x), nd)
        except Exception:
            return x

    if not stats:
        return speak("I don't have fresh laptop data yet. Please make sure the laptop monitor is running.")

    # Helper to answer by metric
    def answer_cpu():
        if cpu is None: return speak("I couldn't read CPU usage yet.")
        return speak(f"Your CPU usage is {fnum(cpu)} percent.")

    def answer_mem():
        if mem is None: return speak("I couldn't read memory usage yet.")
        return speak(f"Your memory usage is {fnum(mem)} percent.")

    def answer_disk():
        if disk_free is None: return speak("I couldn't read disk information yet.")
        return speak(f"You have {fnum(disk_free, 2)} gigabytes free on disk C.")

    def answer_uptime():
        if uptime is None: return speak("I couldn't read uptime yet.")
        return speak(f"Your laptop has been running for {uptime}.")

    # Built-in help
    if intent_name == "AMAZON.HelpIntent":
        return speak("You can ask: CPU usage, memory usage, disk space left, uptime, or say full system summary.")

    # Exact intents first
    if intent_name == "CheckCPUIntent":
        return answer_cpu()

    if intent_name == "CheckMemoryIntent":
        return answer_mem()

    if intent_name == "CheckDiskIntent":
        return answer_disk()

    if intent_name == "CheckAllStatusIntent":
        return speak(summary or "Here’s your status, but I couldn’t generate the full summary.")

    if intent_name == "CheckUptimeIntent":
        # SAFETY: If transcript clearly mentions CPU, override misroute.
        if has_any(phrase_from_transcript, ["cpu", "c p u", "processor", "proc"]):
            return answer_cpu()
        return answer_uptime()

    # Catch-all free-form intent
    if intent_name == "MetricQueryIntent":
        phrase_slot = (((intent_obj.get("slots") or {}).get("phrase") or {}).get("value") or "")
        phrase_clean = normalize_phrase(phrase_slot)
        app.logger.info(f"MetricQuery phrase: {phrase_clean}")

        if has_any(phrase_clean, ["cpu", "c p u", "processor", "proc"]):
            return answer_cpu()
        if has_any(phrase_clean, ["memory", "ram"]):
            return answer_mem()
        if has_any(phrase_clean, ["disk", "storage", "space", "drive"]):
            return answer_disk()
        if has_any(phrase_clean, ["uptime", "running time", "how long", "since when"]):
            return answer_uptime()

        # As a last resort, use transcript
        if has_any(phrase_from_transcript, ["cpu", "c p u", "processor", "proc"]):
            return answer_cpu()
        if has_any(phrase_from_transcript, ["memory", "ram"]):
            return answer_mem()
        if has_any(phrase_from_transcript, ["disk", "storage", "space", "drive"]):
            return answer_disk()
        if has_any(phrase_from_transcript, ["uptime", "running time", "how long", "since when"]):
            return answer_uptime()

        return speak("I heard you, but I couldn't tell which metric you want. Try CPU, memory, disk, or uptime.")

    # Fallback intent or anything else: try transcript rescue
    if intent_name in ("AMAZON.FallbackIntent", ""):
        if has_any(phrase_from_transcript, ["cpu", "c p u", "processor", "proc"]):
            return answer_cpu()
        if has_any(phrase_from_transcript, ["memory", "ram"]):
            return answer_mem()
        if has_any(phrase_from_transcript, ["disk", "storage", "space", "drive"]):
            return answer_disk()
        if has_any(phrase_from_transcript, ["uptime", "running time", "how long", "since when"]):
            return answer_uptime()

    # Default
    return speak("I'm not sure which detail you want. Try CPU usage, memory, storage, uptime, or laptop status.")

@app.route("/update-system-info", methods=["POST"])
def update_system_info():
    global latest_data
    payload = request.get_json(silent=True) or {}
    latest_data = payload
    app.logger.info("System info updated.")
    return jsonify({"status": "success", "message": "System info received."}), 200

@app.route("/latest-system-info", methods=["GET"])
def get_latest_data():
    return jsonify(latest_data if latest_data else {"message": "No data received yet."})

@app.route("/ping", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "alexa-monitoring"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
