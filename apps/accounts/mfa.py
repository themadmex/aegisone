import base64
import secrets

import segno
from django_otp import login as otp_login
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

RECOVERY_CODE_COUNT = 10


def confirmed_totp(user):
    return TOTPDevice.objects.filter(user=user, confirmed=True).first()


def pending_totp(user):
    device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    if device is None:
        device = TOTPDevice.objects.create(user=user, name="Authenticator app", confirmed=False)
    return device


def setup_material(device):
    """Return the manual setup key and an inline SVG QR code for the device."""
    key = base64.b32encode(bytes.fromhex(device.key)).decode().rstrip("=")
    uri = device.config_url  # otpauth:// URI carrying the issuer and account label
    svg = segno.make(uri, error="m").svg_inline(scale=5, dark="#17253A", light="#FFFFFF", border=2)
    grouped = " ".join(key[i : i + 4] for i in range(0, len(key), 4))
    return grouped, svg


def issue_recovery_codes(user):
    """Replace all recovery codes and return the new ones (shown exactly once)."""
    static, _ = StaticDevice.objects.get_or_create(user=user, name="Recovery codes", defaults={"confirmed": True})
    static.token_set.all().delete()
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        code = "-".join(secrets.token_hex(2) for _ in range(3))
        StaticToken.objects.create(device=static, token=code)
        codes.append(code)
    return codes


def verify(request, user, code):
    """Check a TOTP code, then a single-use recovery code. Logs the device in on success."""
    totp = confirmed_totp(user)
    if totp is not None and totp.verify_token(code):
        otp_login(request, totp)
        return "totp"
    static = StaticDevice.objects.filter(user=user, confirmed=True).first()
    if static is not None and static.verify_token(code.lower()):
        otp_login(request, static)
        return "recovery"
    return None
