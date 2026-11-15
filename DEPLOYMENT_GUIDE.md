# FaceClass Deployment Guide for Another Local Machine

This guide explains how to transfer and deploy **FaceClass** on any target local machine (Windows, macOS, or Linux) with zero hassle.

---

## 1. Quick Start (1-Click Automated Startup)

Everything has been automated into unified startup scripts that check dependencies, create virtual environments, install packages, initialize databases, and launch both Backend and Frontend.

### On Windows:
Double-click or run:
```bat
start_all.bat
```
*(or run `powershell -ExecutionPolicy Bypass -File .\start_all.ps1` in PowerShell)*

### On Linux / macOS / WSL:
```bash
chmod +x start_all.sh stop_all.sh
./start_all.sh
```

### To Stop All Running Services:
* **Windows**: Run `stop_all.bat` (or `.\stop_all.ps1`)
* **Linux/macOS**: Run `./stop_all.sh`

---

## 2. Prerequisites on Target Machine

| Component | Minimum Version | Purpose |
|---|---|---|
| **Python** | 3.10+ (recommended 3.11 or 3.12) | Backend Flask API & Machine Learning |
| **Node.js & npm** | Node 18+ (Node 20+ LTS recommended) | Frontend React & Vite Dev Server |
| **Git** *(Optional)* | Any | Repository management |
| **Docker** *(Optional)* | Docker Desktop | If you prefer containerized deployment |

---

## 3. How to Transfer the Project to the New Machine

When copying the `p5genderid` folder to the target computer (via USB drive, ZIP archive, or Git clone):

### You CAN omit these folders to save space & transfer speed:
- `node_modules/` *(auto-installed on startup)*
- `backend/.venv/` *(auto-created on startup)*
- `dist/` *(generated build artifacts)*

### MUST KEEP:
- `backend/ml/models/` *(contains the Caffe model weights `gender_net.caffemodel` and `gender_deploy.prototxt`)*
- `src/` and `backend/app/` *(application source code)*
- Configuration files, `package.json`, `package-lock.json`, `requirements.txt`
- `start_all.bat`, `start_all.ps1`, `start_all.sh`, `stop_all.*`

---

## 4. What the Startup Script Does Automatically

1. **Environment Verification**: Verifies Python and Node.js/npm exist in system PATH.
2. **Configuration Setup**: Automatically creates `backend/.env` from `backend/.env.example` if not already present, using relative paths so it works in any directory.
3. **Python Virtual Environment**: Automatically sets up `backend/.venv` and installs all dependencies from `backend/requirements.txt`.
4. **Database Initialization**: Prepares `backend/instance/faceclass.db` and generates the database schema.
5. **Frontend Setup**: Runs `npm install` automatically if `node_modules` is not yet present.
6. **Concurrent Startup**: Launches the Flask API on `http://localhost:5000` and the React frontend on `http://localhost:5173`.
7. **Browser Launch**: Opens `http://localhost:5173` automatically once ready.

---

## 5. First Time Account Setup

* Open `http://localhost:5173`.
* Navigate to the **Register** tab.
* Register the first user account.
* **Important**: The **very first user account registered** automatically receives the **Administrator** role. All subsequent registrations receive standard user permissions.

---

## 6. Docker Deployment (Alternative Option)

If the target machine has Docker Desktop installed, you can also run the entire containerized stack (Frontend, API, MySQL, Redis):

```bat
start_docker.bat
```
or manually:
```bash
cp .env.production.example .env.production
docker compose up --build -d
```
The Docker container exposes the web application on **`http://localhost:8080`**.
