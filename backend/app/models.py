from datetime import datetime, timezone
import json
from pathlib import Path
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

def now(): return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__="users"
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(120),nullable=False); email=db.Column(db.String(255),unique=True,index=True,nullable=False)
    password_hash=db.Column(db.String(255),nullable=False); role=db.Column(db.String(20),nullable=False,default="user"); status=db.Column(db.String(20),default="active")
    created_at=db.Column(db.DateTime(timezone=True),default=now); updated_at=db.Column(db.DateTime(timezone=True),default=now,onupdate=now)
    predictions=db.relationship("Prediction",backref="user",lazy=True,cascade="all, delete-orphan")
    def set_password(self,p): self.password_hash=generate_password_hash(p)
    def check_password(self,p): return check_password_hash(self.password_hash,p)
    def json(self): return {"id":self.id,"name":self.name,"email":self.email,"role":self.role,"status":self.status,"created_at":self.created_at.isoformat()}

class ModelVersion(db.Model):
    __tablename__="model_versions"
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(100),nullable=False); version=db.Column(db.String(50),nullable=False)
    architecture=db.Column(db.String(255)); input_width=db.Column(db.Integer,default=224); input_height=db.Column(db.Integer,default=224); status=db.Column(db.String(30),default="mock")
    accuracy=db.Column(db.Float); precision_score=db.Column(db.Float); recall_score=db.Column(db.Float); f1_score=db.Column(db.Float); test_sample_size=db.Column(db.Integer)
    model_path=db.Column(db.String(500)); created_at=db.Column(db.DateTime(timezone=True),default=now)

class Prediction(db.Model):
    __tablename__="predictions"
    id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False,index=True)
    predicted_label=db.Column(db.String(50),nullable=False,index=True); confidence=db.Column(db.Float,nullable=False); class_a_probability=db.Column(db.Float,nullable=False); class_b_probability=db.Column(db.Float,nullable=False)
    processing_time_ms=db.Column(db.Integer,nullable=False); model_version_id=db.Column(db.Integer,db.ForeignKey("model_versions.id")); model_mode=db.Column(db.String(30),default="mock")
    image_path=db.Column(db.String(500)); created_at=db.Column(db.DateTime(timezone=True),default=now,index=True)
    model=db.relationship("ModelVersion")
    def json(self): return {"id":self.id,"predicted_label":self.predicted_label,"confidence":round(self.confidence,2),"class_a_probability":round(self.class_a_probability,2),"class_b_probability":round(self.class_b_probability,2),"processing_time_ms":self.processing_time_ms,"model_version":self.model.version if self.model else "Unknown","model_mode":self.model_mode,"created_at":self.created_at.isoformat(),"image_url":None}

class ActivityLog(db.Model):
    __tablename__="activity_logs"
    id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey("users.id"),index=True); action=db.Column(db.String(100),nullable=False); ip_address=db.Column(db.String(64)); metadata_json=db.Column(db.Text); created_at=db.Column(db.DateTime(timezone=True),default=now)

class Setting(db.Model):
    __tablename__="settings"
    id=db.Column(db.Integer,primary_key=True); key=db.Column(db.String(100),unique=True,nullable=False); value=db.Column(db.Text); updated_at=db.Column(db.DateTime(timezone=True),default=now,onupdate=now)

def ensure_model_record():
    if current_app.config.get("INFERENCE_BACKEND")=="opencv_caffe" and not current_app.config["MOCK_MODE"]:
        if not ModelVersion.query.filter_by(version="OpenCV Caffe GenderNet v1",status="production").first():
            db.session.add(ModelVersion(name="GenderNet",version="OpenCV Caffe GenderNet v1",architecture="Caffe CNN facial gender classifier",input_width=227,input_height=227,status="production",model_path=current_app.config["GENDER_MODEL_PATH"])); db.session.commit()
        return
    metadata_path=Path(current_app.config["MODEL_METADATA_PATH"])
    model_path=Path(current_app.config["MODEL_PATH"])
    if model_path.is_file() and metadata_path.is_file():
        try:
            data=json.loads(metadata_path.read_text(encoding="utf-8")); metrics=data.get("metrics",{})
            version=str(data.get("version","1.0.0"))
            if not ModelVersion.query.filter_by(version=version,status="production").first():
                db.session.add(ModelVersion(name=data.get("name","GenderCNN"),version=version,architecture=data.get("architecture","MobileNetV2 + custom classification head"),status="production",accuracy=metrics.get("accuracy"),precision_score=metrics.get("precision"),recall_score=metrics.get("recall"),f1_score=metrics.get("f1"),test_sample_size=data.get("test_sample_size"),model_path=str(model_path)))
                db.session.commit()
            return
        except (OSError,ValueError,TypeError):
            pass
    if current_app.config["MOCK_MODE"] and not ModelVersion.query.first():
        db.session.add(ModelVersion(name="GenderCNN",version="Development Mock",architecture="MobileNetV2 + custom classification head",status="mock")); db.session.commit()

# Public demo accounts shown on the login page. Passwords are reset on every start so the demo always works.
DEMO_ACCOUNTS=[
    {"name":"Demo User","email":"demo@example.com","password":"DemoUser2026!","role":"user"},
    {"name":"Demo Admin","email":"admin@example.com","password":"DemoAdmin2026!","role":"admin"},
]
DEMO_EMAILS={a["email"] for a in DEMO_ACCOUNTS}

def ensure_demo_users():
    for account in DEMO_ACCOUNTS:
        user=User.query.filter_by(email=account["email"]).first()
        if not user:
            user=User(name=account["name"],email=account["email"],role=account["role"]); db.session.add(user)
        user.role=account["role"]; user.status="active"
        if not user.password_hash or not user.check_password(account["password"]): user.set_password(account["password"])
    db.session.commit()
