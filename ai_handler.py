import cv2
import numpy as np

def predict_waste(image_path):
    # 1. Load the AI Brain files
    proto = "MobileNetSSD_deploy.prototxt"
    model = "MobileNetSSD_deploy.caffemodel"

    # 2. Define the objects this AI knows
    CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
               "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
               "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
               "sofa", "train", "tvmonitor"]

    # 3. Load the Neural Network
    net = cv2.dnn.readNetFromCaffe(proto, model)

    # 4. Prepare the image
    image = cv2.imread(image_path)
    blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 0.007843, (300, 300), 127.5)

    # 5. Run the detection
    net.setInput(blob)
    detections = net.forward()

    # 6. Check the results
    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        
        # Only trust the AI if it is more than 20% sure
        if confidence > 0.2:
            idx = int(detections[0, 0, i, 1])
            label = CLASSES[idx]
            print(f"AI Detected: {label} ({confidence*100:.2f}%)")

            # --- CATEGORY LOGIC ---
            # Vegetables/Organic are often seen as 'pottedplant' or organic textures
            if label in ["pottedplant", "bird", "cat", "dog"]:
                return "Biodegradable (Vegetable/Organic)", "LOW"
            
            # Electronics/Metal are seen as monitors, chairs, or tables
            elif label in ["tvmonitor", "sofa", "diningtable"]:
                return "Hazardous (Electronic/Metal)", "HIGH"
            
            # Plastic/Glass are seen as bottles
            elif label in ["bottle"]:
                return "Recyclable (Plastic/Glass)", "LOW"

    # 7. Fallback: If AI is confused, check the texture (smooth vs. rough)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    texture_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    if texture_score < 150:
        return "Biodegradable (Vegetable)", "LOW"
    else:
        return "Non-Biodegradable", "MEDIUM"