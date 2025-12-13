import cv2
import torch
import tensorflow as tf

print("OpenCV CUDA:", cv2.cuda.getCudaEnabledDeviceCount())
print("PyTorch CUDA:", torch.cuda.is_available())
print("TensorFlow GPU:", len(tf.config.list_physical_devices('GPU')))