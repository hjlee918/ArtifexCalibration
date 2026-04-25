# app/utils/keychain.py
import keyring
import keyring.errors

SERVICE = "lg-oled-cal"


def save_client_key(tv_ip: str, client_key: str) -> None:
    """Store the TV client key in the system keychain keyed by IP address."""
    keyring.set_password(SERVICE, tv_ip, client_key)


def load_client_key(tv_ip: str) -> str | None:
    """Return the stored client key for the given TV IP, or None if not found."""
    return keyring.get_password(SERVICE, tv_ip)


def delete_client_key(tv_ip: str) -> bool:
    """Delete the stored client key. Returns True if deleted, False if not present."""
    try:
        keyring.delete_password(SERVICE, tv_ip)
        return True
    except keyring.errors.PasswordDeleteError:
        return False
