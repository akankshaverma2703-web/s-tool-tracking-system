
CLASS_NAME_OVERRIDES = {}


def normalize_class_name(raw_name):
    """Converts a raw YOLO class label into the normalized form used in DB."""
    if raw_name in CLASS_NAME_OVERRIDES:
        return CLASS_NAME_OVERRIDES[raw_name]
    return raw_name.strip().lower().replace(" ", "_")