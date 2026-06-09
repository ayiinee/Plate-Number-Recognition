from fast_alpr import ALPR


def create_alpr_engine():
    return ALPR(
        detector_model="yolo-v9-t-384-license-plate-end2end",
        ocr_model="cct-xs-v2-global-model",
    )


def predict_and_annotate(alpr, frame):
    """
    Mengembalikan frame yang sudah diberi anotasi dan hasil deteksi.
    """
    drawn = alpr.draw_predictions(frame)

    if hasattr(drawn, "image"):
        annotated_frame = drawn.image
        results = drawn.results
    else:
        annotated_frame = drawn
        results = alpr.predict(frame)

    return annotated_frame, results