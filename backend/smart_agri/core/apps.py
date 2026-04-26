from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'smart_agri.core'

    def ready(self):
        import smart_agri.core.signals
        import smart_agri.core.services.signal_handlers # Register Listeners
        from django.db import connection
        from django.db.backends import utils as db_utils

        # Test compatibility shim: some legacy tests issue SQLite PRAGMA statements.
        # On PostgreSQL, treat these as no-op instead of raising syntax errors.
        if connection.vendor == "postgresql" and not getattr(db_utils.CursorWrapper, "_pragma_compat_patched", False):
            original_execute = db_utils.CursorWrapper.execute

            def execute_with_pragma_compat(self, sql, params=None):
                if isinstance(sql, str) and sql.strip().upper().startswith("PRAGMA FOREIGN_KEYS"):
                    return None
                return original_execute(self, sql, params)

            db_utils.CursorWrapper.execute = execute_with_pragma_compat
            db_utils.CursorWrapper._pragma_compat_patched = True
        
        # [Architectural Hardening] Register Domain Event Subscribers
        from smart_agri.core.events import AgriEventBus, EventBus, ActivityCreated, ActivityUpdated, ActivityDeleted
        from smart_agri.core.listeners import (
            handle_finance_sync, handle_inventory_sync, 
            handle_finance_reversal, handle_inventory_reversal,
            handle_costing_async  # [Phase 8] Async Costing
        )
        
        # Costing Subscription (Async First)
        EventBus.subscribe(ActivityCreated, handle_costing_async)
        EventBus.subscribe(ActivityUpdated, handle_costing_async)

        # Finance Subscription (Synchronous Check - safety net)
        EventBus.subscribe(ActivityCreated, handle_finance_sync)
        EventBus.subscribe(ActivityUpdated, handle_finance_sync)
        EventBus.subscribe(ActivityDeleted, handle_finance_reversal)
        
        # Inventory Subscription
        EventBus.subscribe(ActivityCreated, handle_inventory_sync)
        EventBus.subscribe(ActivityUpdated, handle_inventory_sync)
        EventBus.subscribe(ActivityDeleted, handle_inventory_reversal)

        # Integration Hub Subscription (transactional persistent outbox)
        from smart_agri.core.listeners_integration import publish_activity_committed_to_outbox
        AgriEventBus.subscribe('activity_committed')(publish_activity_committed_to_outbox)

        # [Dependency Injection] Register Core Services
        from smart_agri.core.di import container
        from smart_agri.core.services.interfaces import IInventoryService, ICostService
        from smart_agri.core.services.inventory.service import TreeInventoryService
        from smart_agri.core.services.costing.service import CostService

        # Registering Classes directly as they utilize @classmethod/@staticmethod patterns
        container.register(IInventoryService, TreeInventoryService)
        container.register(ICostService, CostService)
