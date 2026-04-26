import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from smart_agri.core.models.pos import POSOrder, POSOrderLine, POSSession
from smart_agri.core.services.forensic_service import ForensicService
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.inventory.models import Item

logger = logging.getLogger(__name__)


class POSService:
    def __init__(self, farm):
        self.farm = farm

    def open_session(self, device_id, user, opening_balance=0):
        session = POSSession.objects.create(
            farm=self.farm,
            session_id=f"{device_id}-{timezone.now().timestamp()}",
            device_id=device_id,
            opened_by=user,
            opening_balance=opening_balance,
            is_active=True,
        )
        return session

    @transaction.atomic
    def create_order(
        self,
        session,
        items_data,
        payment_method="cash",
        customer=None,
        device_time=None,
        lat=None,
        lon=None,
        accuracy=None,
        idempotency_key=None,
    ):
        is_valid_gps, gps_error = ForensicService.validate_gps_posture(lat, lon, accuracy, mode="STRICT")
        if not is_valid_gps:
            raise ValueError(f"Forensic Block: {gps_error}")

        total = Decimal("0.00")
        order = POSOrder.objects.create(
            session=session,
            order_number=f"POS-{idempotency_key or timezone.now().strftime('%Y%m%d%H%M%S%f')}",
            customer=customer,
            device_timestamp=device_time or timezone.now(),
            payment_method=payment_method,
            is_synced=False,
            latitude=lat,
            longitude=lon,
            accuracy=accuracy,
            idempotency_key=idempotency_key,
        )

        for item_data in items_data:
            item = Item.objects.get(pk=item_data["item_id"])
            qty = Decimal(str(item_data["quantity"]))
            price = Decimal(str(item_data["price"]))
            line_total = qty * price
            POSOrderLine.objects.create(
                order=order,
                item=item,
                quantity=qty,
                unit_price=price,
                line_total=line_total,
            )
            total += line_total

        order.total_amount = total
        order.net_amount = total - order.discount_amount + order.tax_amount

        proof = ForensicService.sign_transaction(
            agent=session.opened_by,
            action="CREATE_POS_ORDER",
            payload={
                "order_number": order.order_number,
                "total": str(total),
                "items_count": len(items_data),
                "gps": {"lat": lat, "lon": lon, "acc": accuracy},
            },
        )
        order.offline_data["forensic_proof"] = proof
        order.save()
        return order

    def sync_offline_orders(self, session):
        orders = POSOrder.objects.filter(session=session, is_synced=False)
        for order in orders:
            try:
                with transaction.atomic():
                    for line in order.lines.all():
                        InventoryService.record_movement(
                            farm=self.farm,
                            item=line.item,
                            qty_delta=-line.quantity,
                            ref_type="POS_SALE",
                            ref_id=order.order_number,
                            note=f"POS Sale: Order {order.order_number}",
                        )
                    order.is_synced = True
                    order.sync_error = ""
                    order.save()
            except (Item.DoesNotExist, ValidationError, ValueError) as exc:
                order.sync_error = str(exc)
                order.save()
                logger.error("POS Sync Failed for Order %s: %s", order.order_number, exc)
