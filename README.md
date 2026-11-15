# FaceClass

FaceClass is a complete academic facial-image classification system. It combines a responsive React interface, a secured Flask REST API, OpenCV face validation, a TensorFlow MobileNetV2 training/inference path, database-backed history, analytics, administration, and explicit responsible-use guidance.

The labels produced by this project are dataset-defined appearance classifications. They do not determine a person's gender identity. The application makes that limitation visible in the landing page, results and model information view.

## Included features

- Upload and deliberate webcam capture workflows
- MIME-safe image decoding, dimension/quality checks, one-face validation, cropping and normalization
- Production TensorFlow inference when a trained model is available
- Deterministic development mock mode, visibly labelled and never presented as model output
- JWT authentication, password hashing, role-protected administration, rate limits and audit logs
- Per-user prediction history, deletion, filtering, responsive mobile cards and usage analytics
- Model transparency page with architecture, methodology, limitations and ethical interpretation
- Separate training/evaluation scripts with held-out test evaluation
- SQLite development database and MySQL-ready SQLAlchemy configuration

## Quick Start (1-Click Automated Startup)

To run the entire system on any local machine (handles dependencies, virtual environment, database, and launches both frontend & backend):

* **Windows**: Double-click `start_all.bat` (or run `.\start_all.ps1` in PowerShell).
* **Linux / macOS**: Run `./start_all.sh`.
* **To Stop**: Run `stop_all.bat` (or `./stop_all.sh`).

For transfer instructions and step-by-step guidance, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

## Run the frontend manually

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`. Set `VITE_API_URL` if the API does not run at `http://localhost:5000/api`.

## Run the API

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
```

The first registered account becomes the administrator. Later accounts receive the user role. The default database is created in `backend/instance/faceclass.db`.

For MySQL, create a database and user, install the requirements, then set:

```env
DATABASE_URL=mysql+pymysql://faceclass:strong-password@localhost/faceclass
```

## Model setup

Development starts with `MOCK_MODE=true`. Mock results are deterministic for a given image and marked `mock` in both API records and the UI. They are useful only to demonstrate the connected product while a real model is being trained.

Arrange training images by dataset label:

```text
training/datasets/raw/
  Female/
  Male/
```

Use a carefully reviewed and appropriately licensed dataset. Then run:

```powershell
cd training
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python train.py --data datasets/raw
```

The trainer reserves 30% before training, divides that held-out portion into validation and test data, applies augmentation only to the training path, checkpoints the best model, and writes model metadata. For a formal study, prepare a fixed subject-disjoint `datasets/test` directory and run:

```powershell
python evaluate.py --model ../backend/ml/models/model.keras --test datasets/test
```

After reviewing subgroup performance and evaluation artifacts, set `MODEL_PATH` to the exported model and `MOCK_MODE=false`. Restart the API. If the model cannot load or inference fails, the API returns an error and does not create a prediction.

## Privacy and production notes

Source images are not retained by default. Prediction metadata remains until the user deletes it. Production deployments should use HTTPS, strong secrets, a restricted database account, server-side malware scanning, an external rate-limit store, encrypted backups and a documented model release process. Arbitrary model upload is intentionally absent from the browser.

## Container production deployment

The repository includes a non-root Gunicorn API container, an Nginx frontend/reverse proxy, MySQL and Redis. After placing the verified model artifacts in `backend/ml/models`, copy `.env.production.example` to `.env.production`, replace every placeholder, and run:

```powershell
docker compose config
docker compose up --build -d
```

The application will be available on port `8080`. Put a TLS-enabled reverse proxy or managed edge in front of it. MySQL and Redis have no public port mappings. Complete [the production checklist](deploy/PRODUCTION_CHECKLIST.md) before launch.

## API summary

`POST /api/auth/register`, `POST /api/auth/login`, `GET/PUT /api/user/profile`, `POST/GET /api/predictions`, `GET/DELETE /api/predictions/{id}`, `GET /api/analytics/overview`, `GET /api/model`, and `GET /api/admin/overview`.
