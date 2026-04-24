from unittest.mock import patch
from app.utils.keychain import save_client_key, load_client_key, delete_client_key

SERVICE = "lg-oled-cal"

def test_save_and_load_key():
    with patch("app.utils.keychain.keyring") as mock_kr:
        mock_kr.get_password.return_value = "abc123"
        save_client_key("192.168.1.101", "abc123")
        mock_kr.set_password.assert_called_once_with(SERVICE, "192.168.1.101", "abc123")
        key = load_client_key("192.168.1.101")
        mock_kr.get_password.assert_called_once_with(SERVICE, "192.168.1.101")
        assert key == "abc123"

def test_load_missing_key_returns_none():
    with patch("app.utils.keychain.keyring") as mock_kr:
        mock_kr.get_password.return_value = None
        assert load_client_key("192.168.1.102") is None

def test_delete_key():
    with patch("app.utils.keychain.keyring") as mock_kr:
        delete_client_key("192.168.1.101")
        mock_kr.delete_password.assert_called_once_with(SERVICE, "192.168.1.101")
