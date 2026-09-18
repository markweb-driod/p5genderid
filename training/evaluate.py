import argparse, json
from pathlib import Path
import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

def main():
    p=argparse.ArgumentParser(); p.add_argument("--model",default="../backend/ml/models/model.keras"); p.add_argument("--test",default="datasets/test"); args=p.parse_args()
    dataset=tf.keras.utils.image_dataset_from_directory(args.test,shuffle=False,image_size=(224,224),batch_size=32,label_mode="binary")
    model=tf.keras.models.load_model(args.model); y=np.concatenate([labels.numpy().ravel() for _,labels in dataset]); probabilities=model.predict(dataset,verbose=0).ravel(); predicted=(probabilities>=.5).astype(int)
    report=classification_report(y,predicted,target_names=dataset.class_names,output_dict=True); output={"classification_report":report,"confusion_matrix":confusion_matrix(y,predicted).tolist(),"roc_auc":float(roc_auc_score(y,probabilities)),"test_sample_size":int(len(y))}
    Path(args.model).with_name("evaluation.json").write_text(json.dumps(output,indent=2),encoding="utf-8"); print(json.dumps(output,indent=2))
if __name__=="__main__": main()

