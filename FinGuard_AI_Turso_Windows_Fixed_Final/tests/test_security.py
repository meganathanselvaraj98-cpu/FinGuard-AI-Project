from backend.security import decrypt_text, deterministic_hash, encrypt_text, mask_account_number, password_is_strong


def test_encryption_round_trip():
    original = "123456789012"
    encrypted = encrypt_text(original)
    assert encrypted != original
    assert decrypt_text(encrypted) == original


def test_deterministic_hash():
    assert deterministic_hash("ABC") == deterministic_hash("abc")
    assert deterministic_hash("ABC") != deterministic_hash("ABD")


def test_masking_and_password():
    assert mask_account_number("1234567890").endswith("7890")
    assert password_is_strong("Strong@123")[0] is True
