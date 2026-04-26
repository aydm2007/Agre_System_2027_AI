from django.apps import AppConfig

class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'smart_agri.sales'
    verbose_name = 'المبيعات'

    def ready(self):
        import smart_agri.sales.signals
