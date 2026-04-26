from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0084_farmsettings_governance_policy_fields"),
        ("finance", "0040_alter_financialledger_account_code"),
        ("inventory", "0023_item_requires_batch_tracking"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SupplierSettlement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(db_index=True, null=True)),
                ("updated_at", models.DateTimeField(null=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                (
                    "invoice_reference",
                    models.CharField(blank=True, default="", max_length=120),
                ),
                ("due_date", models.DateField(blank=True, null=True)),
                (
                    "payment_method",
                    models.CharField(
                        choices=[("CASH_BOX", "Cash Box"), ("BANK", "Bank")],
                        default="CASH_BOX",
                        max_length=20,
                    ),
                ),
                ("payable_amount", models.DecimalField(decimal_places=4, max_digits=19)),
                (
                    "paid_amount",
                    models.DecimalField(decimal_places=4, default=Decimal("0.0000"), max_digits=19),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("UNDER_REVIEW", "Under Review"),
                            ("APPROVED", "Approved"),
                            ("PARTIALLY_PAID", "Partially Paid"),
                            ("PAID", "Paid"),
                            ("REJECTED", "Rejected"),
                            ("REOPENED", "Reopened"),
                        ],
                        db_index=True,
                        default="DRAFT",
                        max_length=20,
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_reason", models.TextField(blank=True, default="")),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="supplier_settlements_approved",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "cost_center",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_settlements",
                        to="finance.costcenter",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_settlements_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "crop_plan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_settlements",
                        to="core.cropplan",
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "farm",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="supplier_settlements",
                        to="core.farm",
                    ),
                ),
                (
                    "latest_treasury_transaction",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="latest_for_supplier_settlements",
                        to="finance.treasurytransaction",
                    ),
                ),
                (
                    "purchase_order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_settlement",
                        to="inventory.purchaseorder",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="supplier_settlements_reviewed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "finance_suppliersettlement", "ordering": ["-created_at"], "managed": True},
        ),
        migrations.CreateModel(
            name="SupplierSettlementPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(db_index=True, null=True)),
                ("updated_at", models.DateTimeField(null=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("amount", models.DecimalField(decimal_places=4, max_digits=19)),
                ("note", models.CharField(blank=True, default="", max_length=255)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_settlement_payments_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "settlement",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="finance.suppliersettlement",
                    ),
                ),
                (
                    "treasury_transaction",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_settlement_payment",
                        to="finance.treasurytransaction",
                    ),
                ),
            ],
            options={"db_table": "finance_suppliersettlementpayment", "ordering": ["created_at"], "managed": True},
        ),
        migrations.AddConstraint(
            model_name="suppliersettlement",
            constraint=models.CheckConstraint(
                check=models.Q(("payable_amount__gt", 0)),
                name="supplier_settlement_payable_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="suppliersettlement",
            constraint=models.CheckConstraint(
                check=models.Q(("paid_amount__gte", 0)),
                name="supplier_settlement_paid_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="suppliersettlementpayment",
            constraint=models.CheckConstraint(
                check=models.Q(("amount__gt", 0)),
                name="supplier_settlement_payment_positive",
            ),
        ),
    ]
