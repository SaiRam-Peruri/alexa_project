import os, json, re, logging
from flask import Flask, jsonify, request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import openai
except ImportError:
    logger.warning("OpenAI module not found. AI responses will use fallback.")
    OpenAI = None

# Set OpenAI API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY environment variable is not set.")
    client = None
elif OpenAI is None:
    openai.api_key = None
else:
    openai.api_key = api_key

app = Flask(__name__)
latest_data = {}

def speak(intent_name: str, context: str, fallback_text: str):
    try:
        # Call OpenAI API to generate a response
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides brief responses for an Alexa skill about laptop system monitoring."},
                {"role": "user", "content": f"Generate a response for the intent '{intent_name}' with context: {context}"}
            ],
            max_tokens=100
        )
        ai_text = response.choices[0].message.content.strip()

        # Log the interaction
        logger.info(f"AI Response | Intent: {intent_name} | Context: {context} | Response: {ai_text}")

        # Ensure the response is within Alexa's character limits
        if len(ai_text) > 8000:
            ai_text = ai_text[:8000]

        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {"type": "PlainText", "text": ai_text},
                "shouldEndSession": True
            }
        })
    except Exception as e:
        # Log the error and fallback to static response
        logger.error(f"Error generating AI response: {e}")
        return jsonify({
            "version": "1.0",
            "response": {
                "outputSpeech": {"type": "PlainText", "text": fallback_text},
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
        return speak(
            intent_name="LaunchRequest",
            context="User launched the skill.",
            fallback_text="Hi! You can ask about CPU, memory, storage, uptime, or say laptop status."
        )

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
        return speak(
            intent_name="NoDataIntent",
            context="No fresh laptop data available.",
            fallback_text="I don't have fresh laptop data yet. Please make sure the laptop monitor is running."
        )

    # Helper to answer by metric
    def answer_cpu():
        if cpu is None:
            return speak(
                intent_name="CheckCPUIntent",
                context="CPU data is unavailable.",
                fallback_text="I couldn't read CPU usage yet."
            )
        return speak(
            intent_name="CheckCPUIntent",
            context=f"CPU usage is {fnum(cpu)} percent.",
            fallback_text=f"Your CPU usage is {fnum(cpu)} percent."
        )

    def answer_mem():
        if mem is None:
            return speak(
                intent_name="CheckMemoryIntent",
                context="Memory data is unavailable.",
                fallback_text="I couldn't read memory usage yet."
            )
        return speak(
            intent_name="CheckMemoryIntent",
            context=f"Memory usage is {fnum(mem)} percent.",
            fallback_text=f"Your memory usage is {fnum(mem)} percent."
        )

    def answer_disk():
        if disk_free is None:
            return speak(
                intent_name="CheckDiskIntent",
                context="Disk data is unavailable.",
                fallback_text="I couldn't read disk information yet."
            )
        return speak(
            intent_name="CheckDiskIntent",
            context=f"Disk C has {fnum(disk_free, 2)} gigabytes free.",
            fallback_text=f"You have {fnum(disk_free, 2)} gigabytes free on disk C."
        )

    def answer_uptime():
        if uptime is None:
            return speak(
                intent_name="CheckUptimeIntent",
                context="Uptime data is unavailable.",
                fallback_text="I couldn't read uptime yet."
            )
        return speak(
            intent_name="CheckUptimeIntent",
            context=f"Laptop has been running for {uptime}.",
            fallback_text=f"Your laptop has been running for {uptime}."
        )

    # Built-in help
    if intent_name == "AMAZON.HelpIntent":
        return speak(
            intent_name="AMAZON.HelpIntent",
            context="User asked for help.",
            fallback_text="You can ask: CPU usage, memory usage, disk space left, uptime, or say full system summary."
        )

    # Exact intents first
    if intent_name == "CheckCPUIntent":
        return answer_cpu()

    if intent_name == "CheckMemoryIntent":
        return answer_mem()

    if intent_name == "CheckDiskIntent":
        return answer_disk()

    if intent_name == "CheckAllStatusIntent":
        return speak(
            intent_name="CheckAllStatusIntent",
            context="User requested full system status.",
            fallback_text=summary or "Here’s your status, but I couldn’t generate the full summary."
        )

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

        return speak(
            intent_name="MetricQueryIntent",
            context="User query did not match any known metrics.",
            fallback_text="I heard you, but I couldn't tell which metric you want. Try CPU, memory, disk, or uptime."
        )

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
    return speak(
        intent_name="FallbackIntent",
        context="User request did not match any known intents.",
        fallback_text="I'm not sure which detail you want. Try CPU usage, memory, storage, uptime, or laptop status."
    )

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
