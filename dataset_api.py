# -*- coding: utf-8 -*-
"""Dataset_API.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/11wU6DH26x6XyMh-7mgk4rEPJPU9g1QtS
"""

#Import necessary modules and packages
import tensorflow as tf
import cv2 as cv
import glob
import sys
import numpy as np
from tensorflow.keras.datasets.cifar10 import load_data
import os

#Load image and label data to train and test splits
(train_x, train_y), (test_x, test_y) = load_data()

#Define wrapper function for Feature to be used later for 'Example' protocol message
def _int64_feature(value):
  return tf.train.Feature(int64_list = tf.train.Int64List(value = [value]))

def _bytes_feature(value):
  return tf.train.Feature(bytes_list = tf.train.BytesList(value = [value]))


#Function to create tfrecords files
def create_tfrecord(filename, data, labels):
  
  #Call the TFRecordWriter function class to write records to a TFRecords file and assign a writer function
  writer = tf.python_io.TFRecordWriter(filename)
  
  for i in range(len(data)):
      
    if not i % 1000:
      print('Train data: {}/{}'.format(i, len(data)))
      sys.stdout.flush()
      
    image = data[i]
    label = labels[i]
    image = image.tostring()
    
    #Create the feature dictionary with image_raw and label as keys and 
    #their bytes and int64 lists features as respective values
    feature = {
                'image_raw': _bytes_feature(image),
                'label': _int64_feature(label)}
    
    #Instantiate an Example protocol message
    example = tf.train.Example(features = tf.train.Features(feature = feature))
    
    #Write the serialized string Example proto 
    writer.write(example.SerializeToString())
  
  #Close the writer after finishing writing TFRecords
  writer.close()
  sys.stdout.flush()
  
#Create the TFRecords file for both train and test data
create_tfrecord('train.tfrecords', train_x, train_y)

create_tfrecord('test.tfrecords', test_x, test_y)

#Start the session
sess = tf.Session()
#Initialize the variables
sess.run(tf.global_variables_initializer())

#Define a parser function to extract from the TFRecord files
def parser(record):
    
    #Create a dictionary to extract the raw image and label from the TFRecord files
  keys_to_features = {
                        'image_raw': tf.FixedLenFeature([], tf.string),
                        'label': tf.FixedLenFeature([], tf.int64)}
    #Parse the TFRecord files with the above created dictionary                   
  parsed = tf.parse_single_example(record, keys_to_features)
  #Decode the raw image  from the parser dictionary
  image = tf.decode_raw(parsed['image_raw'], tf.uint8)
  #Convert the image to float32 type
  image = tf.cast(image, tf.float32)
  #Reshape the extracted image to 32x32x3 shape as their original shape 
  image = tf.reshape(image, shape = [32, 32, 3])
  #Convert the lables to int32 type
  labels = tf.cast(parsed['label'], tf.int32)
  return image, labels

#Define the input function for the dataset pipeline
def inp_fn(filename, train, batch_size=16, buffer_size=1000):
  
  #Read the dataset from the TFRecord file
  dataset = tf.data.TFRecordDataset(filenames=filename)
  #Map the parser function to the read dataset to get the image and labels
  dataset = dataset.map(parser)
  
  #If training, shuffle the dataset, else not
  if train:
    dataset = dataset.shuffle(buffer_size=buffer_size)
    num_repeat = None
  
  else:
    num_repeat = 1
  #Repeat the dataset indefinitely for training and once for testing,
  #Number of repeats can be passed by argument if not to repeat indefinitely
  dataset = dataset.repeat(num_repeat)
  #Combines consecutive elements of this dataset into batches.
  dataset = dataset.batch(batch_size=batch_size)
  #Initialize the one shot iterator to creates an Iterator for enumerating the elements of this dataset.  
  iterator = dataset.make_one_shot_iterator()
  #Get the next batch of data
  images_batch, labels_batch = iterator.get_next()
    
  x = {'image': images_batch}
  y = labels_batch
    
  return x, y

#Input function for training and testing
def train_input_fn():
  return inp_fn(filename='train.tfrecords' , train=True)

def test_input_fn():
   return inp_fn(filename='test.tfrecords', train=False)

#Create the feature column as numeric colum to pass to the estimator class
feature_columns = [tf.feature_column.numeric_column('image', shape=[32,32,3])]
num_hidden_units = [512, 256,128, 64]
num_classes = 10

#Create an pre-made dnn classifier with necessary elements
model = tf.estimator.DNNClassifier(feature_columns=feature_columns,
                                   hidden_units=num_hidden_units,
                                   activation_fn=tf.nn.relu,
                                   n_classes=num_classes,
                                   model_dir='./checkpoints_3/')
#Train the model
model.train(input_fn=train_input_fn, steps=10000)
#Evaluate the model
result = model.evaluate(input_fn=test_input_fn)

print('Result:', result)
print('Classification Accuracy: {:.4f}'.format(result['accuracy']*100))
print('Classification Loss: {:.4f}'.format(result['loss']))

#Create custom model function  
def model_fn(features, labels, mode, params):
  
  num_classes = 10
  net = features['image']
  net = tf.identity(net, name="input_tensor")
    
  net = tf.reshape(net, [-1, 32, 32, 3])    

  net = tf.identity(net, name="input_tensor_after")
  #Convolve with 32 filters  
  net = tf.layers.conv2d(inputs=net, name='layer_conv1',
                           filters=32, kernel_size=3,
                           padding='same', activation=tf.nn.relu)
  #Max pool with pool size 2 
  net = tf.layers.max_pooling2d(inputs=net, pool_size=2, strides=2)

  net = tf.layers.conv2d(inputs=net, name='layer_conv2',
                           filters=64, kernel_size=3,
                           padding='same', activation=tf.nn.relu)
  net = tf.layers.max_pooling2d(inputs=net, pool_size=2, strides=2)  

  net = tf.layers.conv2d(inputs=net, name='layer_conv3',
                           filters=64, kernel_size=3,
                           padding='same', activation=tf.nn.relu)
  net = tf.layers.max_pooling2d(inputs=net, pool_size=2, strides=2)    

  #Flatten the network
  net = tf.contrib.layers.flatten(net)
  #Create the dense layers
  net = tf.layers.dense(inputs=net, name='layer_fc1',
                        units=128, activation=tf.nn.relu)  
  #Drop some neurons  
  net = tf.layers.dropout(net, rate=0.5, noise_shape=None, 
                        seed=None, training=(mode == tf.estimator.ModeKeys.TRAIN))
  #Create the output layer  
  net = tf.layers.dense(inputs=net, name='layer_fc_2',
                        units=num_classes)
  
  logits = net
  #Generate the predictions
  y_pred = tf.nn.softmax(logits=logits)
  y_pred_cls = tf.argmax(y_pred, 1)
  
  #Create the cost function
  cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=labels, logits=logits)
  loss = tf.reduce_mean(cross_entropy)
  #Create the optimizer method
  optimizer = tf.train.AdamOptimizer(learning_rate=params['learning_rate'])
  #Minimize the loss
  train_op = optimizer.minimize(loss=loss, global_step=tf.train.get_global_step())
  #Calculate the accuracy metrics
  metrics = {'accuracy': tf.metrics.accuracy(labels, y_pred_cls)}
  #Define the model to be run by the estimator  
  spec = tf.estimator.EstimatorSpec(mode=mode, loss=loss,
                                      train_op=train_op,
                                      eval_metric_ops=metrics)
  return spec

#Define the Estimator class by the custom model
model = tf.estimator.Estimator(model_fn=model_fn,
                                   params={'learning_rate': 0.001},
                                   model_dir='./checkpoints_2/')
#Train and evaluate the model
model.train(input_fn=train_input_fn, steps=10000)
result = model.evaluate(input_fn=test_input_fn)
print('Result:', result)
print('Classification Accuracy : {:4f}'.format(result['accuracy']*100)) 
print('Classification loss: {:.4f}'.format(result['loss']))
sys.stdout.flush()