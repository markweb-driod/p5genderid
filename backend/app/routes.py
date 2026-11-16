from datetime import datetime, timedelta, timezone
from pathlib import Path
from functools import wraps
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import func
from . import db, limiter
from .models import User, Prediction, ModelVersion, ActivityLog, DEMO_EMAILS
from .services import decode_image, detect_face, inference, ImageError
import time

api=Blueprint("api",__name__)
def current_user(): return db.session.get(User,int(get_jwt_identity()))
def log(user,action): db.session.add(ActivityLog(user_id=user.id,action=action,ip_address=request.remote_addr)); db.session.commit()
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def inner(*a,**kw):
        if current_user().role!="admin": return jsonify(message="Administrator access required."),403
        return fn(*a,**kw)
    return inner

@api.get("/health")
def health(): return jsonify(status="ok")

@api.get("/ready")
def ready():
    from flask import current_app
    try:
        db.session.execute(db.text("SELECT 1"))
        model_ready=inference.load_model() if not current_app.config["MOCK_MODE"] else False
        if not model_ready and not current_app.config["MOCK_MODE"]:
            return jsonify(status="not_ready",database=True,model=False,message="Production model is missing."),503
        return jsonify(status="ready",database=True,model=model_ready,mode="mock" if current_app.config["MOCK_MODE"] else "production")
    except Exception:
        return jsonify(status="not_ready",database=False,model=False,message="Database connectivity failed."),503

@api.post("/auth/register")
@limiter.limit("10 per hour")
def register():
    data=request.get_json(silent=True) or {}; name=str(data.get("name","")).strip(); email=str(data.get("email","")).strip().lower(); password=str(data.get("password",""))
    if len(name)<2 or "@" not in email or len(password)<8: return jsonify(message="Provide a valid name, email and password of at least 8 characters."),400
    if User.query.filter_by(email=email).first(): return jsonify(message="An account with this email already exists."),409
    user=User(name=name,email=email,role="admin" if User.query.count()==0 else "user"); user.set_password(password); db.session.add(user); db.session.commit(); log(user,"ACCOUNT_REGISTERED")
    return jsonify(user=user.json(),access_token=create_access_token(identity=str(user.id))),201

@api.post("/auth/login")
@limiter.limit("20 per hour")
def login():
    data=request.get_json(silent=True) or {}; user=User.query.filter_by(email=str(data.get("email","")).lower()).first()
    if not user or not user.check_password(str(data.get("password",""))): return jsonify(message="Email or password is incorrect."),401
    if user.status!="active": return jsonify(message="This account is inactive."),403
    log(user,"SIGNED_IN"); return jsonify(user=user.json(),access_token=create_access_token(identity=str(user.id)))

@api.get("/user/profile")
@jwt_required()
def profile(): return jsonify(user=current_user().json())

@api.put("/user/profile")
@jwt_required()
def update_profile():
    user=current_user(); data=request.get_json(silent=True) or {}; name=str(data.get("name","")).strip(); email=str(data.get("email","")).strip().lower()
    if len(name)<2 or "@" not in email: return jsonify(message="Provide a valid name and email."),400
    if user.email in DEMO_EMAILS and email!=user.email: return jsonify(message="The email of a demo account cannot be changed."),403
    conflict=User.query.filter(User.email==email,User.id!=user.id).first()
    if conflict: return jsonify(message="That email is already in use."),409
    user.name=name; user.email=email; db.session.commit(); return jsonify(user=user.json())

@api.post("/predictions")
@jwt_required()
@limiter.limit("30 per hour")
def create_prediction():
    if "image" not in request.files: return jsonify(code="INVALID_IMAGE",message="Select an image to analyze."),400
    started=time.perf_counter()
    try:
        image,raw=decode_image(request.files["image"]); face=detect_face(image); label,confidence,male,female,mode=inference.predict(face,raw)
        model=ModelVersion.query.order_by(ModelVersion.id.desc()).first(); elapsed=round((time.perf_counter()-started)*1000)
        item=Prediction(user_id=current_user().id,predicted_label=label,confidence=confidence,class_a_probability=male,class_b_probability=female,processing_time_ms=elapsed,model_version_id=model.id,model_mode=mode)
        db.session.add(item); db.session.commit(); log(current_user(),"PREDICTION_CREATED"); return jsonify(prediction=item.json()),201
    except ImageError as exc: return jsonify(code=exc.code,message=exc.message),422

@api.get("/predictions")
@jwt_required()
def predictions():
    page=max(request.args.get("page",1,type=int),1); query=Prediction.query.filter_by(user_id=current_user().id).order_by(Prediction.created_at.desc()); result=query.paginate(page=page,per_page=20,error_out=False)
    return jsonify(items=[x.json() for x in result.items],page=page,pages=result.pages,total=result.total)

@api.get("/predictions/<int:item_id>")
@jwt_required()
def prediction(item_id):
    item=Prediction.query.filter_by(id=item_id,user_id=current_user().id).first_or_404(); return jsonify(prediction=item.json())

@api.delete("/predictions/<int:item_id>")
@jwt_required()
def delete_prediction(item_id):
    item=Prediction.query.filter_by(id=item_id,user_id=current_user().id).first_or_404(); db.session.delete(item); db.session.commit(); log(current_user(),"PREDICTION_DELETED"); return jsonify(message="Prediction deleted.")

@api.get("/analytics/overview")
@jwt_required()
def analytics():
    uid=current_user().id; rows=Prediction.query.filter_by(user_id=uid).order_by(Prediction.created_at.desc()).all(); now=datetime.now(timezone.utc)
    dist={"Male":0,"Female":0}; bands={"<70":0,"70–84":0,"85–94":0,"95+":0}
    for x in rows:
        dist[x.predicted_label]=dist.get(x.predicted_label,0)+1; bands["<70" if x.confidence<70 else "70–84" if x.confidence<85 else "85–94" if x.confidence<95 else "95+"]+=1
    days=[]
    for n in range(6,-1,-1):
        day=(now-timedelta(days=n)).date(); days.append({"day":day.strftime("%a"),"count":sum(1 for x in rows if x.created_at.date()==day)})
    model=ModelVersion.query.order_by(ModelVersion.id.desc()).first()
    return jsonify(total=len(rows),week=sum(x.created_at.replace(tzinfo=timezone.utc)>=now-timedelta(days=7) for x in rows),average_ms=round(sum(x.processing_time_ms for x in rows)/len(rows)) if rows else 0,average_confidence=round(sum(x.confidence for x in rows)/len(rows),1) if rows else 0,distribution=[{"name":k,"value":v} for k,v in dist.items()],confidence=[{"band":k,"count":v} for k,v in bands.items()],timeline=days,recent=[x.json() for x in rows[:5]],model={"version":model.version,"status":model.status})

@api.get("/model")
def model_info():
    m=ModelVersion.query.order_by(ModelVersion.id.desc()).first(); return jsonify(name=m.name,version=m.version,architecture=m.architecture,input=f"{m.input_width} × {m.input_height} RGB",framework="OpenCV DNN (Caffe)" if "Caffe" in (m.version or "") else "TensorFlow / Keras",status=m.status,metrics={"accuracy":m.accuracy,"precision":m.precision_score,"recall":m.recall_score,"f1":m.f1_score,"test_sample_size":m.test_sample_size})

@api.get("/admin/overview")
@admin_required
def admin_overview():
    avg=db.session.query(func.avg(Prediction.processing_time_ms)).scalar() or 0
    return jsonify(users=User.query.count(),predictions=Prediction.query.count(),average_ms=round(avg),models=ModelVersion.query.count())
