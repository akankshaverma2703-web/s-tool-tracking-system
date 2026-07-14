from backend.yolo.model_loader import get_model
from backend.yolo.classes import normalize_class_name

CONFIDENCE_THRESHOLD = 0.5  # ignore detections below 50% confidence


def detect_tool(frame, confidence_threshold=CONFIDENCE_THRESHOLD):
    """
    Runs YOLO on a single frame and returns the highest-confidence detection.

    Args:
        frame: a BGR image (numpy array), e.g. from cv2.VideoCapture or a
               decoded base64 frame sent from the browser.
        confidence_threshold: minimum confidence to accept a detection.

    Returns:
        dict {"class_name": str, "confidence": float} for the best detection,
        or None if nothing was detected above the threshold.
    """
    model = get_model()
    results = model.predict(frame, conf=confidence_threshold, verbose=False)

    if not results or len(results[0].boxes) == 0:
        return None

    best_box = max(results[0].boxes, key=lambda b: float(b.conf[0]))

    raw_class_name = model.names[int(best_box.cls[0])]
    confidence = float(best_box.conf[0])

    return {
        "class_name": normalize_class_name(raw_class_name),
        "confidence": round(confidence, 3),
    }


def decode_base64_frame(image_data):
    """Helper: converts a base64 data-URL (from browser camera capture)
    into a cv2-compatible BGR frame."""
    import base64
    import numpy as np
    import cv2

    header, encoded = image_data.split(',', 1) if ',' in image_data else (None, image_data)
    img_bytes = base64.b64decode(encoded)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return frame