from pathlib import Path

from backend.config import settings
from backend.security import create_access_token, decode_access_token, decrypt_text, encrypt_text


def test_aes_gcm_roundtrip():
    token = encrypt_text("123456789012")
    assert token and token.startswith("aesgcm:v1:")
    assert decrypt_text(token) == "123456789012"
    assert "123456789012" not in token


def test_jwt_roundtrip():
    token = create_access_token(7, "USER")
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["role"] == "USER"


def test_included_models_exist():
    names = {
        "expense_category_classifier.joblib",
        "monthly_expense_predictor.joblib",
        "savings_predictor.joblib",
        "financial_risk_classifier.joblib",
        "anomaly_detector.joblib",
    }
    assert names.issubset({p.name for p in settings.model_dir.glob("*.joblib")})
