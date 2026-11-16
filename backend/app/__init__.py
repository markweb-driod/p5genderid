import os
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from dotenv import load_dotenv

db = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["300 per hour"])
migrate = Migrate()

def create_app(test_config=None):
    base = Path(__file__).resolve().parents[1]
    default_database = "sqlite:///" + (base / "instance" / "faceclass.db").as_posix()
    load_dotenv(base / ".env")

    def resolve_path(val, default_rel):
        if not val or not str(val).strip():
            return str(base / default_rel)
        p = Path(str(val).strip())
        if not p.is_absolute():
            return str(base / p)
        if not p.exists() and (base / default_rel).exists():
            return str(base / default_rel)
        return str(p)

    raw_db = os.getenv("DATABASE_URL")
    if not raw_db or not raw_db.strip():
        db_uri = default_database
    elif raw_db.startswith("sqlite:///"):
        sqlite_file = raw_db[10:].strip()
        sqlite_path = Path(sqlite_file)
        if not sqlite_path.is_absolute():
            db_uri = "sqlite:///" + (base / sqlite_file).as_posix()
        elif not sqlite_path.exists() and not sqlite_path.parent.exists():
            db_uri = default_database
        else:
            db_uri = raw_db
    else:
        db_uri = raw_db.strip()
        # Hosted Postgres (Neon, Vercel) hands out postgres:// URLs; SQLAlchemy needs the psycopg driver named.
        for prefix in ("postgres://", "postgresql://"):
            if db_uri.startswith(prefix):
                db_uri = "postgresql+psycopg://" + db_uri[len(prefix):]
                break

    # Serverless hosts (Vercel) only allow writes under /tmp.
    instance_path = "/tmp/faceclass-instance" if os.getenv("VERCEL") else None
    app = Flask(__name__, instance_relative_config=True, instance_path=instance_path)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "development-only-change-me-32-bytes"),
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "development-jwt-change-me-32-bytes"),
        SQLALCHEMY_DATABASE_URI=db_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 280},
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024,
        JWT_ACCESS_TOKEN_EXPIRES=int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "30")) * 60,
        RATELIMIT_STORAGE_URI=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
        MOCK_MODE=os.getenv("MOCK_MODE", "false").lower() == "true",
        RETAIN_IMAGES=os.getenv("RETAIN_IMAGES", "false").lower() == "true",
        MODEL_PATH=resolve_path(os.getenv("MODEL_PATH"), Path("ml") / "models" / "model.keras"),
        MODEL_METADATA_PATH=resolve_path(os.getenv("MODEL_METADATA_PATH"), Path("ml") / "models" / "metadata.json"),
        INFERENCE_BACKEND=os.getenv("INFERENCE_BACKEND", "opencv_caffe"),
        GENDER_MODEL_PATH=resolve_path(os.getenv("GENDER_MODEL_PATH"), Path("ml") / "models" / "gender_net.caffemodel"),
        GENDER_PROTO_PATH=resolve_path(os.getenv("GENDER_PROTO_PATH"), Path("ml") / "models" / "gender_deploy.prototxt"),
        FACE_DETECTOR_PATH=resolve_path(os.getenv("FACE_DETECTOR_PATH"), Path("ml") / "models" / "face_detection_yunet_2023mar.onnx"),
        FACE_MARGIN=float(os.getenv("FACE_MARGIN", "0.15")),
        MALE_THRESHOLD=float(os.getenv("MALE_THRESHOLD", "0.8")),
        AUTO_CREATE_SCHEMA=os.getenv("AUTO_CREATE_SCHEMA", "true").lower() == "true",
        DEMO_ACCOUNTS=os.getenv("DEMO_ACCOUNTS", "true").lower() == "true",
    )
    if test_config: app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app); jwt.init_app(app); limiter.init_app(app); migrate.init_app(app, db)
    allowed_origins=[origin.strip() for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
    CORS(app, origins=allowed_origins)
    from .routes import api
    app.register_blueprint(api, url_prefix="/api")
    @app.get("/")
    @app.get("/api")
    def index():
        return jsonify(name="FaceClass API", status="ok", health="/api/health", ready="/api/ready", model="/api/model",
                       message="This is the backend API. Open the web app to use FaceClass.")
    @app.errorhandler(404)
    def not_found(_): return jsonify(code="NOT_FOUND", message="This API route does not exist. All endpoints are under /api/."), 404
    @app.errorhandler(413)
    def too_large(_): return jsonify(code="IMAGE_TOO_LARGE", message="The image exceeds the configured upload limit."), 413
    @app.errorhandler(429)
    def rate_limited(_): return jsonify(code="RATE_LIMITED", message="Too many requests. Please wait and try again."), 429
    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if not app.debug: response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
    with app.app_context():
        from . import models
        if app.config["AUTO_CREATE_SCHEMA"]:
            db.create_all()
            models.ensure_model_record()
        if app.config["DEMO_ACCOUNTS"]:
            models.ensure_demo_users()
    return app
