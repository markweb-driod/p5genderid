"""Train and export the FaceClass MobileNetV2 model.

Expected dataset layout:
datasets/raw/Male/*.jpg
datasets/raw/Female/*.jpg
"""
import argparse, json
from pathlib import Path
import tensorflow as tf

def build_model(size=224):
    base=tf.keras.applications.MobileNetV2(input_shape=(size,size,3),include_top=False,weights="imagenet")
    base.trainable=False
    inputs=tf.keras.Input((size,size,3)); x=tf.keras.applications.mobilenet_v2.preprocess_input(inputs)
    x=base(x,training=False); x=tf.keras.layers.GlobalAveragePooling2D()(x); x=tf.keras.layers.Dropout(.3)(x)
    return tf.keras.Model(inputs,tf.keras.layers.Dense(1,activation="sigmoid")(x))

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",default="datasets/raw"); p.add_argument("--output",default="../backend/ml/models/model.keras"); p.add_argument("--epochs",type=int,default=20); args=p.parse_args()
    data=Path(args.data); out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    train=tf.keras.utils.image_dataset_from_directory(data,validation_split=.3,subset="training",seed=42,image_size=(224,224),batch_size=32,label_mode="binary")
    held=tf.keras.utils.image_dataset_from_directory(data,validation_split=.3,subset="validation",seed=42,image_size=(224,224),batch_size=32,label_mode="binary")
    batches=tf.data.experimental.cardinality(held); validation=held.take(batches//2); test=held.skip(batches//2)
    augmentation=tf.keras.Sequential([tf.keras.layers.RandomFlip("horizontal"),tf.keras.layers.RandomRotation(.05),tf.keras.layers.RandomZoom(.1),tf.keras.layers.RandomContrast(.1)])
    model=build_model(); original=model.input; augmented=augmentation(original); output=model(augmented); training_model=tf.keras.Model(original,output)
    training_model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),loss="binary_crossentropy",metrics=["accuracy",tf.keras.metrics.Precision(),tf.keras.metrics.Recall(),tf.keras.metrics.AUC(name="auc")])
    callbacks=[tf.keras.callbacks.EarlyStopping(patience=4,restore_best_weights=True),tf.keras.callbacks.ReduceLROnPlateau(patience=2),tf.keras.callbacks.ModelCheckpoint(str(out),save_best_only=True)]
    training_model.fit(train,validation_data=validation,epochs=args.epochs,callbacks=callbacks)
    values=training_model.evaluate(test,return_dict=True); precision=values["precision"]; recall=values["recall"]; values["f1"]=2*precision*recall/(precision+recall) if precision+recall else 0
    test_sample_size=sum(int(labels.shape[0]) for _,labels in test)
    metadata={"name":"GenderCNN","version":"1.0.0","architecture":"MobileNetV2 + custom classification head","input":"224 × 224 RGB","class_names":train.class_names,"test_sample_size":test_sample_size,"metrics":{k:float(v) for k,v in values.items()}}
    out.with_name("metadata.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    print(json.dumps(metadata,indent=2))
if __name__=="__main__": main()
