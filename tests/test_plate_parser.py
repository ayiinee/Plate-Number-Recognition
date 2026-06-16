from core.plate_parser import is_valid_indonesian_plate
from core.record_store import PlateRecordStore


def test_valid_indonesian_plate_formats():
    assert is_valid_indonesian_plate("B1234CD")
    assert is_valid_indonesian_plate("D12A")
    assert is_valid_indonesian_plate("AB9999XYZ")


def test_invalid_indonesian_plate_formats():
    assert not is_valid_indonesian_plate("1234ABC")
    assert not is_valid_indonesian_plate("ABC12345")
    assert not is_valid_indonesian_plate("B-123-XYZ")
    assert not is_valid_indonesian_plate("PLAT123")


def test_store_skips_invalid_plate():
    store = PlateRecordStore()

    store.add_detection(
        plate="PLAT123",
        confidence=0.9,
        source_name="Kamera",
        min_confidence=0.5,
        cooldown_seconds=5,
    )

    assert len(store.records) == 0


def test_store_accepts_valid_plate():
    store = PlateRecordStore()

    store.add_detection(
        plate="B1234CD",
        confidence=0.9,
        source_name="Kamera",
        min_confidence=0.5,
        cooldown_seconds=5,
    )

    assert len(store.records) == 1
    assert store.records[0]["plat_nomor"] == "B1234CD"
