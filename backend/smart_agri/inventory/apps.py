from django.apps import AppConfig


class InventoryConfig(AppConfig):
    """
    [AGRI-GUARDIAN] Django AppConfig for the Inventory module.
    Manages Items, Stock, Fuel Logs, and Tank Calibrations.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'smart_agri.inventory'
    verbose_name = 'المخزون والمواد'
