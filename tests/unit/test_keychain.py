# tests/unit/test_keychain.py
import keyring.errors
from unittest.mock import patch
from app.utils.keychain import save_client_key, load_client_key, delete_client_key, SERVICE


def test_save_key():
    with patch("app.utils.keychain.keyring") as mock_kr:
        save_client_key("192.168.1.101", "abc123")
        mock_kr.set_password.assert_called_once_with(SERVICE, "192.168.1.101", "abc123")


def test_load_existing_key():
    with patch("app.utils.keychain.keyring") as mock_kr:
        mock_kr.get_password.return_value = "abc123"
        key = load_client_key("192.168.1.101")
        mock_kr.get_password.assert_called_once_with(SERVICE, "192.168.1.101")
        assert key == "abc123"


def test_load_missing_key_returns_none():
    with patch("app.utils.keychain.keyring") as mock_kr:
        mock_kr.get_password.return_value = None
        assert load_client_key("192.168.1.102") is None


def test_delete_existing_key_returns_true():
    with patch("app.utils.keychain.keyring") as mock_kr:
        result = delete_client_key("192.168.1.101")
        mock_kr.delete_password.assert_called_once_with(SERVICE, "192.168.1.101")
        assert result is True


def test_delete_missing_key_returns_false():
    with patch("app.utils.keychain.keyring") as mock_kr:
        mock_kr.errors.PasswordDeleteError = keyring.errors.PasswordDeleteError
        mock_kr.delete_password.side_effect = keyring.errors.PasswordDeleteError("not found")
        result = delete_client_key("192.168.1.199")
        assert result is False
