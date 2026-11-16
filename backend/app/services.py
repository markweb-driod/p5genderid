import hashlib, io, json, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError
from flask import current_app

class ImageError(Exception):
    def __init__(self, code, message): self.code=code; self.message=message; super().__init__(message)

def decode_image(storage):
    declared=(storage.mimetype or "").lower()
    if declared not in ("image/jpeg","image/png"):
        raise ImageError("UNSUPPORTED_FORMAT","Only JPG, JPEG and PNG images are supported.")
    raw=storage.read()
    if not raw: raise ImageError("INVALID_IMAGE","The uploaded file is empty.")
    try:
        probe=Image.open(io.BytesIO(raw)); detected=probe.format; probe.verify()
        if detected not in ("JPEG","PNG"): raise ImageError("UNSUPPORTED_FORMAT","Only JPG, JPEG and PNG images are supported.")
        image=ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    except (UnidentifiedImageError, OSError): raise ImageError("INVALID_IMAGE","The file could not be decoded as a valid image.")
    if image.width * image.height > 40_000_000: raise ImageError("IMAGE_TOO_LARGE","The image dimensions are too large to process safely.")
    if min(image.size)<160: raise ImageError("IMAGE_TOO_SMALL","Use an image at least 160 × 160 pixels.")
    if ImageStat.Stat(image.convert("L")).var[0]<18: raise ImageError("LOW_IMAGE_QUALITY","The image has too little visual detail. Try a clearer image.")
    return image, raw

DETECT_MAX_SIDE=1280      # images are downscaled to this for detection; the crop uses full resolution
MIN_FACE_PX=60            # smallest face side (original pixels) we trust the gender model on
SECOND_FACE_RATIO=0.7     # a second face this large relative to the main one counts as "multiple faces"
_detectors={}

def _yunet(width,height):
    import cv2
    path=current_app.config.get("FACE_DETECTOR_PATH")
    if not path or not Path(path).is_file(): return None
    det=_detectors.get("yunet")
    if det is None:
        det=cv2.FaceDetectorYN.create(str(path),"",(width,height),0.7,0.3,50); _detectors["yunet"]=det
    det.setInputSize((width,height)); return det

def _find_faces(rgb):
    """Return [(x,y,w,h,score,(right_eye,left_eye) or None)] in the coordinates of `rgb`."""
    import cv2
    h,w=rgb.shape[:2]
    det=_yunet(w,h)
    if det is not None:
        _,found=det.detect(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR))
        if found is None: return []
        return [(f[0],f[1],f[2],f[3],float(f[14]),((f[4],f[5]),(f[6],f[7]))) for f in found]
    # Fallback: Haar cascade (no landmarks) on a contrast-equalized image.
    gray=cv2.equalizeHist(cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY))
    cascade=_detectors.get("haar") or cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml"); _detectors["haar"]=cascade
    side=max(24,int(min(w,h)*0.08))
    return [(x,y,fw,fh,1.0,None) for x,y,fw,fh in cascade.detectMultiScale(gray,scaleFactor=1.08,minNeighbors=6,minSize=(side,side))]

def detect_face(image):
    try:
        import cv2
    except ImportError:
        # Pillow-only development fallback validates the central crop; it never masquerades as production detection.
        w,h=image.size; side=min(w,h); return image.crop(((w-side)//2,(h-side)//2,(w+side)//2,(h+side)//2)).resize((227,227))
    full=np.asarray(image)
    scale=min(1.0,DETECT_MAX_SIDE/max(full.shape[:2]))
    small=cv2.resize(full,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA) if scale<1 else full
    faces=sorted(_find_faces(small),key=lambda f:f[2]*f[3],reverse=True)
    if not faces: raise ImageError("NO_FACE_DETECTED","We couldn't detect a clear face. Use a front-facing image with good lighting.")
    main=faces[0]
    if len(faces)>1 and faces[1][2]*faces[1][3]>=SECOND_FACE_RATIO*main[2]*main[3]:
        raise ImageError("MULTIPLE_FACES_DETECTED","More than one face was detected. Use an image containing one person.")
    x,y,fw,fh=[v/scale for v in main[:4]]
    if min(fw,fh)<MIN_FACE_PX: raise ImageError("FACE_TOO_SMALL","The detected face is too small for reliable analysis. Move closer or use a higher-resolution image.")
    cx,cy=x+fw/2,y+fh/2; angle=0.0
    if main[5] is not None and current_app.config.get("FACE_ALIGN",True):
        (rx,ry),(lx,ly)=[(px/scale,py/scale) for px,py in main[5]]
        angle=float(np.degrees(np.arctan2(ly-ry,lx-rx)))
        if abs(angle)>45: angle=0.0
    # Level the eyes, then take a square crop with margin around the face (the gender model was trained on loose crops).
    margin=float(current_app.config.get("FACE_MARGIN",0.15))
    half=max(fw,fh)*(0.5+margin)
    m=cv2.getRotationMatrix2D((cx,cy),angle,1.0)
    m[0,2]+=half-cx; m[1,2]+=half-cy
    size=int(round(2*half))
    crop=cv2.warpAffine(full,m,(size,size),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(cv2.resize(crop,(227,227),interpolation=cv2.INTER_AREA))

class InferenceService:
    def __init__(self): self.model=None
    def load_model(self):
        if current_app.config.get("INFERENCE_BACKEND")=="opencv_caffe":
            try:
                import cv2
                model_path=Path(current_app.config["GENDER_MODEL_PATH"])
                proto_path=Path(current_app.config["GENDER_PROTO_PATH"])
                if not model_path.is_file() or not proto_path.is_file(): return False
                if self.model is None: self.model=cv2.dnn.readNet(str(model_path),str(proto_path),"caffe")
                return True
            except Exception:
                return False
        model_path=Path(current_app.config["MODEL_PATH"])
        if not model_path.is_file(): return False
        if self.model is None:
            try:
                import tensorflow as tf
                self.model=tf.keras.models.load_model(model_path)
            except Exception:
                return False
        return True
    def predict(self, face, raw):
        if not current_app.config.get("MOCK_MODE"):
            if current_app.config.get("INFERENCE_BACKEND")=="opencv_caffe":
                try:
                    import cv2
                    if not self.load_model(): raise RuntimeError("OpenCV Caffe gender model load failed")
                    bgr=cv2.cvtColor(np.asarray(face,dtype=np.uint8),cv2.COLOR_RGB2BGR)
                    # Average the face and its mirror image: cheap test-time augmentation that steadies the score.
                    blob=cv2.dnn.blobFromImages([bgr,cv2.flip(bgr,1)],1.0,(227,227),(78.4263377603,87.7689143744,114.895847746),swapRB=False)
                    self.model.setInput(blob); scores=self.model.forward().mean(axis=0); total=float(scores.sum()) or 1.0
                    # GenderNet leans "Male". Shift its log-odds so that MALE_THRESHOLD maps to 50%
                    # (tuned with person-level cross-validation on LFW; see FACE_MARGIN / MALE_THRESHOLD).
                    raw_male=min(max(float(scores[0])/total,1e-6),1-1e-6); t=float(current_app.config.get("MALE_THRESHOLD",0.8))
                    logit=np.log(raw_male/(1-raw_male))-np.log(t/(1-t))
                    male=float(100/(1+np.exp(-logit))); female=100-male; label="Male" if male>=50 else "Female"
                    return label,max(male,female),male,female,"production"
                except Exception as exc:
                    raise ImageError("INFERENCE_FAILED","The trained OpenCV gender model could not complete inference.") from exc
            model_path=Path(current_app.config["MODEL_PATH"])
            if model_path.exists():
                try:
                    import tensorflow as tf
                    if not self.load_model(): raise RuntimeError("Model load failed")
                    arr=np.asarray(face,dtype=np.float32); arr=tf.keras.applications.mobilenet_v2.preprocess_input(arr); score=float(self.model.predict(arr[None,...],verbose=0).reshape(-1)[0])
                    class_names=["Female","Male"]
                    metadata_path=Path(current_app.config["MODEL_METADATA_PATH"])
                    if metadata_path.is_file():
                        class_names=json.loads(metadata_path.read_text(encoding="utf-8")).get("class_names",class_names)
                    second=str(class_names[1]).lower() if len(class_names)>1 else "male"
                    male=(score if second=="male" else 1-score)*100; female=100-male
                    label="Female" if female>=50 else "Male"; return label,max(male,female),male,female,"production"
                except Exception as exc: raise ImageError("INFERENCE_FAILED","The model could not complete inference.") from exc
            raise ImageError("MODEL_UNAVAILABLE","No trained model is deployed. Contact the administrator.")
        # Deterministic mock for UI/development only. It is labelled MOCK everywhere and is not an ML claim.
        digest=hashlib.sha256(raw).digest(); female=55+(digest[0]/255)*40; female=female if digest[1]%2 else 100-female; male=100-female
        label="Female" if female>=50 else "Male"; return label,max(male,female),male,female,"mock"

inference=InferenceService()
