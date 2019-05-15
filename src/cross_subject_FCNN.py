#!/usr/bin/env python3
# -*- coding: utf-8
#
# Gibran Fuentes-Pineda <gibranfp@unam.mx>
# IIMAS, UNAM
# 2019
#
"""
Script to evaluate a ResNet50 architecture for single-trial cross_subject P300 detection using cross-validation
"""
import argparse
import sys
import numpy as np
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.utils import to_categorical
from sklearn.model_selection import *
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.utils import resample, class_weight
from FCNNmodel import FCNN
from utils import *

def evaluate_cross_subject_model(data, labels, modelpath):
    """
    Trains and evaluates SimpleConv1D architecture for each subject in the P300 Speller database
    using random cross validation.
    """
    aucs = np.zeros(22)
    accuracies = np.zeros(22)
    precisions =  np.zeros(22)
    recalls =  np.zeros(22)
    aps =  np.zeros(22)
    f1scores =  np.zeros(22)
    data = data.reshape((22 * 2880, 206, data.shape[3]))
    labels = labels.reshape((22 * 2880))
    groups = [i for i in range(22) for j in range(2880)]
    cv = LeaveOneGroupOut()
    for k, (t, v) in enumerate(cv.split(data, labels, groups)):
        X_train, y_train, X_test, y_test = data[t], labels[t], data[v], labels[v]
        X_train, X_valid, y_train, y_valid = train_test_split(X_train, y_train, test_size=0.2, random_state=123)    
        
        print("Partition {0}: train = {1}, valid = {2}, test = {3}".format(k, X_train.shape, X_valid.shape, X_test.shape))
        sample_weights = class_weight.compute_sample_weight('balanced', y_train)

        y_onehot_train = to_categorical(y_train)
        y_onehot_valid = to_categorical(y_valid)
        y_onehot_test = to_categorical(y_test)

        sc = EEGChannelScaler()
        X_train = sc.fit_transform(X_train)
        X_valid = sc.transform(X_valid)
        X_test = sc.transform(X_test)

        X_train = np.swapaxes(sc.fit_transform(X_train)[:, np.newaxis, :], 2, 3)
        X_valid = np.swapaxes(sc.transform(X_valid)[:, np.newaxis, :], 2, 3)
        X_test = np.swapaxes(sc.transform(X_test)[:, np.newaxis, :], 2, 3)
        
        model = FCNN(Chans = 6, Samples = 206, Ns=16)
        print(model.summary())
        model.compile(optimizer = 'adam', loss = 'categorical_crossentropy', metrics = ['accuracy'])

        es = EarlyStopping(monitor='val_loss', mode='min', restore_best_weights=True, patience=50)
        model.fit(X_train,
                  y_onehot_train,
                  batch_size = 32,
                  sample_weight = sample_weights,
                  epochs = 200,
                  validation_data = (X_valid, y_onehot_valid),
                  callbacks = [es])

        model.save(modelpath + '/s' + str(k) + '.h5')
        proba_test = model.predict(X_test)
        aucs[k] = roc_auc_score(y_test, proba_test[:, 1])
        accuracies[k] = accuracy_score(y_test, proba_test[:, 1].round())
        precisions[k] = precision_score(y_test, proba_test[:, 1].round())
        recalls[k] = recall_score(y_test, proba_test[:, 1].round())
        aps[k] = average_precision_score(y_test, proba_test[:, 1])
        f1scores[k] = f1_score(y_test, proba_test[:, 1].round())
        print('AUC: {0} ACC: {1} PRE: {2} REC: {3} AP: {4} F1: {5}'.format(aucs[k],
                                                                           accuracies[k],
                                                                           precisions[k],
                                                                           recalls[k],
                                                                           aps[k],
                                                                           f1scores[k]))
        
    np.savetxt(modelpath + '/aucs.npy', aucs)
    np.savetxt(modelpath + '/accuracies.npy', accuracies)
    np.savetxt(modelpath + '/precisions.npy', precisions)
    np.savetxt(modelpath + '/recalls.npy', recalls)
    np.savetxt(modelpath + '/aps.npy', aps)
    np.savetxt(modelpath + '/f1scores.npy', f1scores)

def main():
    """
    Main function
    """
    try:
        parser = argparse.ArgumentParser()
        parser = argparse.ArgumentParser(
            description="Evaluates single-trial cross_subject P300 detection using cross-validation")
        parser.add_argument("datapath", type=str,
                            help="Path for the data of the P300 Speller Database (NumPy file)")
        parser.add_argument("labelspath", type=str,
                            help="Path for the labels of the P300 Speller Database (NumPy file)")
        parser.add_argument("modelpath", type=str,
                            help="Path of the directory where the models are to be saved")
        args = parser.parse_args()
        
        data, labels = load_db(args.datapath, args.labelspath)
        evaluate_cross_subject_model(data, labels, args.modelpath)
        
    except SystemExit:
        print('for help use --help')
        sys.exit(2)
        
if __name__ == "__main__":
    main()