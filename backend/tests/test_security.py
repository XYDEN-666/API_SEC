"""Password hashing utility tests."""

from app.core.security import hash_password, verify_password


def test_hashed_password_verifies_correctly() -> None:
    hashed = hash_password("SuperSecret123!")

    assert hashed != "SuperSecret123!"
    assert hashed.startswith("$2")  # bcrypt hash prefix
    assert verify_password("SuperSecret123!", hashed)


def test_wrong_password_fails_verification() -> None:
    hashed = hash_password("right-password")

    assert not verify_password("wrong-password", hashed)


def test_hashes_are_salted_and_unique() -> None:
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_rejects_malformed_hash() -> None:
    assert not verify_password("anything", "not-a-bcrypt-hash")
