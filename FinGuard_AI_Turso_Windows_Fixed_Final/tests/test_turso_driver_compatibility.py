from pathlib import Path


def test_windows_compatible_turso_driver_is_declared():
    root = Path(__file__).resolve().parents[1]
    requirements = (root / "requirements.txt").read_text(encoding="utf-8")
    database_source = (root / "backend" / "database.py").read_text(encoding="utf-8")

    assert "libsql==0.1.11" in requirements
    assert "pyturso" not in requirements
    assert "sqlalchemy-libsql" not in requirements
    assert "libsql.connect" in database_source
    assert 'create_engine(\n            "sqlite://"' in database_source
    assert "sqlite+turso_sync" not in database_source
    assert "sqlite+libsql" not in database_source
