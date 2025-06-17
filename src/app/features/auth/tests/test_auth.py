from ....features.auth.security import get_password_hash, verify_password


# test password hashing and verification
def test_password_hashing():
    password = "test_password"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False
    assert hashed != password  # Ensure the hash is not the same as the plain password


# test password hashing consistency
def test_password_hash_consistency():
    password = "test_password"
    hashed1 = get_password_hash(password)
    hashed2 = get_password_hash(password)
    assert hashed1 != hashed2, "Hashing the same password should yield different hash"
    assert hashed1 != password, "Ensure the hash is not the same as the plain password"


# test password hashing uniqueness
def test_password_hash_uniqueness():
    password1 = "test_password1"
    password2 = "test_password2"
    hashed1 = get_password_hash(password1)
    hashed2 = get_password_hash(password2)
    assert hashed1 != hashed2  # Different passwords should yield different hashes
    assert verify_password(password1, hashed1) is True
    assert verify_password(password2, hashed2) is True


# test password hashing with special characters
def test_password_hash_special_characters():
    password = "!@#$%^&*()_+"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


# test password hashing with empty string
def test_password_hash_empty_string():
    password = ""
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("non_empty_password", hashed) is False
    assert hashed != password  # Ensure the hash is not the same as the plain password
