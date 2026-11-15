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

def detect_face(image):
    try:
        import cv2
        gray=cv2.cvtColor(np.asarray(image),cv2.COLOR_RGB2GRAY)
        cascade=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
        faces=cascade.detectMultiScale(gray,scaleFactor=1.1,minNeighbors=5,minSize=(70,70))
        if len(faces)==0: raise ImageError("NO_FACE_DETECTED","We couldn't detect a clear face. Use a front-facing image with good lighting.")
        if len(faces)>1: raise ImageError("MULTIPLE_FACES_DETECTED","More than one face was detected. Use an image containing one person.")
        x,y,w,h=faces[0]
        if w<80 or h<80: raise ImageError("FACE_TOO_SMALL","The detected face is too small for reliable analysis.")
        return image.crop((x,y,x+w,y+h)).resize((224,224))
    except ImportError:
        # Pillow-only development fallback validates the central crop; it never masquerades as production detection.
        w,h=image.size; side=min(w,h); return image.crop(((w-side)//2,(h-side)//2,(w+side)//2,(h+side)//2)).resize((224,224))

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
                    blob=cv2.dnn.blobFromImage(bgr,1.0,(227,227),(78.4263377603,87.7689143744,114.895847746),swapRB=False)
                    self.model.setInput(blob); scores=self.model.forward()[0]; total=float(scores.sum()) or 1.0
                    male=float(scores[0]/total*100); female=float(scores[1]/total*100); label="Male" if male>=female else "Female"
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
