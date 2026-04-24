import keyring

_SERVICE = "lg-oled-cal"


def save_client_key(tv_ip: str, client_key: str) -> None:
    keyring.set_password(_SERVICE, tv_ip, client_key)


def load_client_key(tv_ip: str) -> str | None:
    return keyring.get_password(_SERVICE, tv_ip)


def delete_client_key(tv_ip: str) -> None:
    keyring.delete_password(_SERVICE, tv_ip)
