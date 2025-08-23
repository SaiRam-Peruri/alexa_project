# Alexa Project

This project is designed to provide system monitoring capabilities that can be accessed via an Alexa-enabled Echo Dot device. The structure and files are organized to support easy deployment and integration with Alexa routines and skills.

## Project Structure

- `main.py` or `system_monitor.py`: Contains the actual Flask application code that exposes system information via HTTP endpoints. This is the core logic that Alexa interacts with.
- `requirements.txt`: Lists all Python dependencies required to run the Flask app and system monitoring features (e.g., Flask, psutil, gunicorn).
- `Procfile`: Used for deployment on platforms like Cloud Run or Heroku, specifying how to start the web server.

## Why This Structure?
- **Separation of Concerns**: Each file serves a specific purpose (app logic, dependencies, deployment config).
- **Resource Organization**: The main code files (`main.py` or `system_monitor.py`) contain all the logic for system monitoring, making it easy to maintain and extend.
- **Alexa Integration**: The endpoints exposed by the Flask app are designed to be consumed by Alexa routines or custom skills, allowing your Echo Dot to fetch and announce system status.

## How Alexa/Echo Dot Works With This
- Alexa can make HTTP requests to the `/system-info` endpoint to retrieve system status.
- You can set up routines or custom skills to trigger these requests and have Alexa announce the results.

## Usage
1. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
2. Run the Flask app:
   ```powershell
   python main.py
   ```
3. Access system info:
   - Open `http://127.0.0.1:5000/system-info` in your browser or configure Alexa to use this endpoint.

---
Feel free to extend the project with more endpoints or integrate additional smart home features!
