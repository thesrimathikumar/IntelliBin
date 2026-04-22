import cv2
import os

# Check if files exist
print("Prototxt exists:", os.path.exists("MobileNetSSD_deploy.prototxt"))
print("Model exists:", os.path.exists("MobileNetSSD_deploy.caffemodel"))

# Try to load the AI
try:
    net = cv2.dnn.readNetFromCaffe("MobileNetSSD_deploy.prototxt", "MobileNetSSD_deploy.caffemodel")
    print("✅ SUCCESS: AI Brain loaded perfectly!")
except Exception as e:
    print("❌ ERROR:", e)