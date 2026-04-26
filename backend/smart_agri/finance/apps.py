from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "smart_agri.finance"

    def ready(self):
        # Ensure signals are registered (treasury -> ledger posting).
        import smart_agri.finance.signals  # noqa: F401
