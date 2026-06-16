def is_authorized(email: str | None, allowed_users: list[str]) -> bool:
    """allowlist が空なら True（platform 制限に委ねる）。設定時は大小無視で照合。"""
    if not allowed_users:
        return True
    if not email:
        return False
    allowed = {a.strip().lower() for a in allowed_users if a and a.strip()}
    return email.strip().lower() in allowed
