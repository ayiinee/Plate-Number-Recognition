import re
from statistics import mean


def normalize_plate(text: str) -> str:
    if not text:
        return ""

    text = str(text).upper().strip()
    text = re.sub(r"[^A-Z0-9]", "", text)

    return text


def get_attr_or_key(obj, name, default=None):
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def parse_confidence(value) -> float:
    """
    FastALPR OCR confidence kadang berupa float,
    kadang berupa list confidence per karakter.
    Fungsi ini menormalkan semuanya menjadi satu angka float.
    """
    if value is None:
        return 0.0

    if isinstance(value, list):
        if len(value) == 0:
            return 0.0

        numeric_values = []

        for item in value:
            try:
                numeric_values.append(float(item))
            except Exception:
                continue

        if not numeric_values:
            return 0.0

        return float(mean(numeric_values))

    try:
        return float(value)
    except Exception:
        return 0.0


def extract_plate_results(results):
    """
    Mengambil text plat dan confidence dari output FastALPR.
    Hanya hasil yang punya OCR text yang dimasukkan.
    """
    extracted = []

    if not results:
        return extracted

    for result in results:
        ocr = get_attr_or_key(result, "ocr")

        if ocr is None:
            continue

        plate_text = (
            get_attr_or_key(ocr, "text")
            or get_attr_or_key(result, "text")
            or get_attr_or_key(result, "plate")
            or get_attr_or_key(result, "plate_text")
        )

        confidence_raw = (
            get_attr_or_key(ocr, "confidence")
            or get_attr_or_key(result, "confidence")
            or get_attr_or_key(result, "score")
        )

        plate_text = normalize_plate(plate_text)
        confidence = parse_confidence(confidence_raw)

        if plate_text:
            extracted.append(
                {
                    "plate": plate_text,
                    "confidence": confidence,
                }
            )

    return extracted