from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class SixDigitPasswordValidator:
    """
    Enforce a simple 6-digit numeric PIN-style password.
    Designed for beginner users while still preventing empty or non-numeric passwords.
    """

    REQUIRED_LENGTH = 6

    def validate(self, password, user=None):
        if password is None:
            raise ValidationError(
                _("كلمة المرور مطلوبة ويجب أن تتكون من 6 أرقام."),
                code="password_missing",
            )
        if len(password) != self.REQUIRED_LENGTH or not password.isdigit():
            raise ValidationError(
                _("كلمة المرور يجب أن تتكون من %(length)d أرقام فقط."),
                code="password_not_six_digits",
                params={"length": self.REQUIRED_LENGTH},
            )

    def get_help_text(self):
        return _("استخدم كلمة مرور مكونة من 6 أرقام (مثال: 123456).")
