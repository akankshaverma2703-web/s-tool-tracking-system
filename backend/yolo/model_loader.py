import os

_model = None
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'runs', 'detect', 'train', 'weights', 'best.pt')


def get_model():
    """Returns the loaded YOLO model, loading it from disk on first call."""
    global _model
    if _model is None:
        from ultralytics import YOLO  # imported lazily so the app doesn't
                                       # crash if ultralytics isn't installed
                                       # yet while training is still running
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"YOLO model not found at {MODEL_PATH}. "
                "Training may still be in progress — copy best.pt here once done."
            )
        _model = YOLO(MODEL_PATH)
    return _model


def is_model_ready():
    """Quick check used by the API layer to know whether YOLO is usable yet,
    without raising an exception."""
    return os.path.exists(MODEL_PATH)