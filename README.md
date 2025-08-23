# Voice-Driven Laptop Monitoring (Alexa + Cloud Run) — V1

Ask your Echo Dot for live laptop stats:

> “Alexa, ask acer processor load / memory used /disk space / uptime.”

A tiny Windows agent posts metrics every 5 seconds to a Google Cloud Run API. A custom Alexa skill hits the API and speaks back real-time values. The backend includes a fallback router so even phrases like “c. p. u. usage” map correctly.

---

## ✨ Features

- **Live metrics:** CPU %, Memory %, Disk C: free (GB), Uptime
- **Voice interface:** Alexa custom skill (invocation: acer)
- **Robust NLU:** AMAZON.SearchQuery + transcript normalization for variants like “c. p. u.”
- **Lightweight agent:** Windows + Python (Flask, psutil) pushes every 5s
- **Serverless backend:** Flask on Cloud Run, HTTPS with public invoke
- **Debug endpoints:** `/latest-system-info`, `/ping`
- **Tested on Echo Dot:** works via voice (V1)

---

## 🗺️ Architecture

```
+-------------------+       HTTPS POST (5s)        +---------------------------+
|  Windows Laptop   | ---------------------------> |  Cloud Run (Flask API)    |
|  Agent (Flask)    |                               |  /update-system-info      |
|  psutil metrics   |  Local debug:                 |  /latest-system-info      |
|  /system-info     |  http://127.0.0.1:5000       |  /ping  /                 |
+-------------------+                               +--------------+------------+
                                                                 |
                                                     Alexa HTTPS | (request/response)
                                                                 v
                                                     +---------------------------+
                                                     |  Alexa Custom Skill       |
                                                     |  Invocation: "acer"       |
                                                     |  Intents: CPU/Mem/Disk/...|
                                                     +---------------------------+
```

---

## 📁 Repo Structure

```
.
├── agent/
│   ├── system_monitor.py        # Flask code for Windows agent
│   ├── start.bat
│   └── startup.vbs              # optional (auto-start on login)
├── cloudrun/
│   ├── main.py                  # Flask code for Cloud Run backend
│   ├── requirements.txt         # Python dependencies for backend
│   └── Dockerfile               # optional; for custom Cloud Run builds
└── alexa/
    └── interactionModel.json    # Amazon Alexa intents & utterances
```

- **agent/**: Contains the Windows agent code (`system_monitor.py`) that collects and posts system stats.
- **cloudrun/**: Contains the backend code (`main.py`, `requirements.txt`) deployed to Google Cloud Run.
- **alexa/**: Contains the Alexa skill interaction model (intents, utterances).

---

## ⚙️ Prerequisites

- Python 3.10+ on the laptop
- Google Cloud project with Cloud Run enabled (gcloud CLI configured)
- Alexa Developer Console account
- Echo Dot signed into the same Amazon account you use in the Developer Console

---

## 🚀 Deploy the Cloud Run Backend

1. **Install dependencies**  
   In `cloudrun/requirements.txt`:
   ```
   Flask==3.0.0
   gunicorn==21.2.0
   ```

2. **Dockerfile (optional)**  
   In `cloudrun/Dockerfile`:
   ```
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY main.py .
   CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "main:app"]
   ```

3. **Build & deploy**
   ```powershell
   PROJECT_ID=<your-gcp-project>
   REGION=us-central1
   SERVICE_NAME=alexa-monitoring

   gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME ./cloudrun
   gcloud run deploy $SERVICE_NAME `
     --image gcr.io/$PROJECT_ID/$SERVICE_NAME `
     --region $REGION `
     --allow-unauthenticated
   ```

4. **Verify**
   - GET `https://<your-cloud-run-url>/ping` → `{ "status": "healthy", ... }`
   - Note the root URL (e.g., `https://...run.app/`) for Alexa.

---

## 🖥️ Run the Laptop Agent (Windows)

- `agent/system_monitor.py`: Collects CPU/Memory/Disk/Uptime via psutil, serves GET `/system-info` locally, and POSTs JSON to Cloud Run `/update-system-info` every 5s.

**Install dependencies:**
```powershell
py -m venv venv
venv\Scripts\pip install flask psutil requests
```

**Start agent:**
```powershell
venv\Scripts\python agent\system_monitor.py
```

**Optional: start.bat**
```bat
@echo off
set CLOUD_RUN_URL=https://<your-cloud-run-root>/update-system-info
cd /d C:\path\to\repo\agent
..\venv\Scripts\python system_monitor.py
```

**Verify locally:**
- Open `http://127.0.0.1:5000/system-info` (JSON with stats)
- Check console: “✅ Data sent to Cloud Run.”
- Cloud URL `/latest-system-info` should show fresh stats

**Auto-start (optional):**
- Place a shortcut to your `startup.vbs` (or the BAT) in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`

---

## 🗣️ Create & Wire the Alexa Skill

1. **Create skill**  
   Alexa Developer Console → Create Custom skill  
   Name: e.g., acer  
   Invocation name: acer (or “acer monitor”)

2. **Import interaction model**  
   Build → Interaction Model → JSON Editor  
   Paste your `alexa/interactionModel.json` (includes intents + MetricQueryIntent)  
   Save Model → Build Model

3. **Endpoint**  
   Build → Endpoint → HTTPS  
   Default Region URL: `https://<your-cloud-run-root>/` (root path, not `/latest-system-info`)  
   Certificate: My development endpoint has a certificate from a trusted CA  
   Save

4. **Enable testing**  
   Test tab → Skill testing in Development = ON  
   Ensure your Echo Dot is on the same Amazon account  
   Device language should match your skill locale (e.g., English (US))

---

## 🚀 Exact Setup Steps

1. **Windows Agent Setup**
   - Create `system_monitor.py` in the `agent/` folder with Flask and psutil code to expose `/system-info`.
   - Install dependencies:
     ```powershell
     py -m venv venv
     venv\Scripts\pip install flask psutil requests
     ```
   - Run the agent:
     ```powershell
     venv\Scripts\python agent\system_monitor.py
     ```

2. **Cloud Run Backend Setup**
   - Create `main.py` and `requirements.txt` in the `cloudrun/` folder with Flask code and dependencies:
     ```
     Flask==3.0.0
     gunicorn==21.2.0
     ```
   - Deploy to Cloud Run:
     ```powershell
     PROJECT_ID=<your-gcp-project>
     REGION=us-central1
     SERVICE_NAME=alexa-monitoring

     gcloud builds submit --tag gcr.io/%PROJECT_ID%/%SERVICE_NAME% ./cloudrun
     gcloud run deploy %SERVICE_NAME% --image gcr.io/%PROJECT_ID%/%SERVICE_NAME% --region %REGION% --allow-unauthenticated
     ```

3. **Alexa Skill Setup**
   - Create a custom skill in the Alexa Developer Console.
   - Set invocation name (e.g., "acer").
   - Import your `alexa/interactionModel.json` for intents and utterances.
   - Set the Cloud Run backend URL as the HTTPS endpoint.
   - Enable skill testing in development.

4. **Connect Everything**
   - The agent posts system stats to Cloud Run every 5 seconds.
   - Alexa skill fetches and announces stats via voice commands.

5. **Test**
   - Open `http://127.0.0.1:5000/system-info` to verify local agent.
   - Use Alexa voice queries to confirm end-to-end functionality.

---

## 🔎 Endpoints (Backend)

- GET `/ping` – health check
- POST `/update-system-info` – agent pushes JSON payload
- GET `/latest-system-info` – debug: returns last payload
- POST `/` – Alexa skill entry (handles intents)
- GET `/` – simple “live” JSON for sanity check

---

## 🧪 Try It (Echo Dot)

- “Alexa, open acer”
- “Alexa, ask acer processor load”
- “Alexa, ask acer how much memory is used”
- “Alexa, ask acer how much disk space is left”
- “Alexa, ask acer how long has my system been running”
- Also works: “c. p. u. usage” (thanks to fallback routing)

---

## 🛠️ Troubleshooting

- Alexa says “not sure how to help” → Use exact invocation (“acer”), enable testing, and ensure the same Amazon account.
- No data yet → Laptop agent not posting. Check CLOUD_RUN_URL and console logs for “✅ Data sent…”.

- Skill reaches backend? → Open Cloud Run logs. You should see an incoming POST to `/` and lines like Intent: ... | Transcript: ....
- Wrong answers for CPU vs Uptime → Rebuild the model with MetricQueryIntent; backend normalization handles “c. p. u.” variants.
- 401/403 → Make Cloud Run public:
  ```powershell
  gcloud run services add-iam-policy-binding <SERVICE_NAME> `
    --member=allUsers --role=roles/run.invoker
  ```
- Locale mismatch → Device language must be one of your skill locales (e.g., en-US).

---

## 🔐 Security Notes

- The backend is public (to let Alexa call it). Do not expose secrets.
- Payload contains device stats; if sensitive, consider adding a shared token or IP filtering in V2.
- Use Cloud Run logs responsibly; avoid storing PII.

---

## 🧭 Roadmap (V2+)

- Persistence: Firestore “latest” + history
- Watchdog: Cloud Scheduler to detect missed heartbeats
- Alerts: Pub/Sub → SendGrid/Slack/Twilio
- Snapshots: Render a PNG “status card” to Cloud Storage
- Alexa cards: Show answers in Alexa app; keep session open for multi-turn

---

## 📜 License

MIT (or your choice)

---

## 🙌 Credits

Python, Flask, psutil  
Alexa Skills Kit  
Google Cloud Run
