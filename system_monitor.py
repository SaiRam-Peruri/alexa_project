import os
import psutil
import platform
import datetime
import threading
import time
import requests
from flask import Flask, jsonify

# Cloud Run URL (update if needed)
CLOUD_RUN_ENDPOINT = os.getenv(
    "CLOUD_RUN_URL", 
    "https://alexa-monitoring-151299060564.us-central1.run.app/update-system-info"
)

app = Flask(__name__)

def get_system_info():
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.datetime.now() - boot_time
    uptime_str = str(uptime).split('.')[0]

    battery = psutil.sensors_battery()
    battery_info = None
    battery_text = "No battery detected."
    if battery:
        battery_info = {
            "Charging": battery.power_plugged,
            "Percentage": battery.percent
        }
        battery_text = f"Battery is at {battery.percent}% and {'charging' if battery.power_plugged else 'not charging'}."

    net_io = psutil.net_io_counters()
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('C:\\')

    summary = (
        f"Your laptop is running {platform.system()} {platform.version()} "
        f"with {psutil.cpu_count(logical=True)} CPU cores. "
        f"CPU is at {cpu_percent}% usage, and memory is {memory.percent}% used. "
        f"Disk C has {round(disk_usage.free / (1024 ** 3), 2)} GB free. "
        f"{battery_text} The system has been running for {uptime_str}."
    )

    detailed = {
        "CPU": {
            "Usage (%)": cpu_percent,
            "Cores": psutil.cpu_count(logical=True),
            "Frequency (MHz)": round(psutil.cpu_freq().current, 1) if psutil.cpu_freq() else None
        },
        "Memory": {
            "Total (GB)": round(memory.total / (1024 ** 3), 2),
            "Available (GB)": round(memory.available / (1024 ** 3), 2),
            "Used (%)": memory.percent
        },
        "Disk (C:)": {
            "Total (GB)": round(disk_usage.total / (1024 ** 3), 2),
            "Used (GB)": round(disk_usage.used / (1024 ** 3), 2),
            "Free (GB)": round(disk_usage.free / (1024 ** 3), 2),
            "Used (%)": disk_usage.percent
        },
        "Battery": battery_info,
        "Network": {
            "Data Sent (MB)": round(net_io.bytes_sent / (1024 ** 2), 2),
            "Data Received (MB)": round(net_io.bytes_recv / (1024 ** 2), 2)
        },
        "System Info": {
            "OS": platform.system(),
            "OS Version": platform.version(),
            "Architecture": platform.machine(),
            "Uptime": uptime_str
        }
    }

    return {"summary": summary, "stats": detailed}

# Background thread to push data to Cloud Run
def background_sender():
    while True:
        try:
            data = get_system_info()
            response = requests.post(CLOUD_RUN_ENDPOINT, json=data, timeout=5)
            if response.status_code == 200:
                print("✅ Data sent to Cloud Run.")
            else:
                print(f"❌ Cloud Run error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error sending to Cloud Run: {e}")
        time.sleep(5)

@app.route("/system-info", methods=["GET"])
def system_info():
    return jsonify(get_system_info())

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "running", "message": "Merged system monitor is live"})

if __name__ == "__main__":
    print("[•] Starting system monitor with Cloud Run sync...")
    threading.Thread(target=background_sender, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Local info available at http://127.0.0.1:{port}/system-info")
    app.run(host="0.0.0.0", port=port)
