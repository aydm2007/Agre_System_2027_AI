from rest_framework import serializers, viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, Prefetch
from django.db import OperationalError, transaction
from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError, PermissionDenied as DjangoPermissionDenied
from .models import SalesInvoice, SalesInvoiceItem, Customer
from smart_agri.core.api.viewsets.base import AuditedModelViewSet
from smart_agri.core.api.permissions import IsFarmManager
from smart_agri.core.throttles import FinancialMutationThrottle
import logging

logger = logging.getLogger(__name__)

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class SalesInvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='item.name', read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, source='total')

    class Meta:
        model = SalesInvoiceItem
        fields = ['id', 'item', 'product_name', 'qty', 'unit_price', 'total_price']

class SalesInvoiceSerializer(serializers.ModelSerializer):
    items = SalesInvoiceItemSerializer(many=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    invoice_number = serializers.SerializerMethodField()
    # [Agri-Guardian] Farm is derived from Location (Zombie Column fix).
    farm = serializers.PrimaryKeyRelatedField(read_only=True) 

    class Meta:
        model = SalesInvoice
        fields = [
            'id', 'invoice_number', 'farm', 'farm_name', 'customer', 'customer_name', 
            'location', 'invoice_date', 'status', 'total_amount', 'notes', 
            'items', 'created_by', 'approved_by', 'approved_at'
        ]
        read_only_fields = ['status', 'total_amount', 'created_by', 'approved_by', 'approved_at', 'farm']

    def get_invoice_number(self, obj):
        # Canonical display number until a dedicated DB sequence field is introduced.
        return str(obj.id)

    def create(self, validated_data):
        """
        [AGRI-GUARDIAN] Delegates to SaleService.create_invoice()
        """
        items_data = validated_data.pop('items')
        
        request = self.context.get('request')
        user = request.user if request else None
        
        from smart_agri.sales.services import SaleService
        invoice = SaleService.create_invoice(
            customer=validated_data.get('customer'),
            location=validated_data.get('location'),
            invoice_date=validated_data.get('invoice_date'),
            items_data=items_data,
            user=user,
            notes=validated_data.get('notes', '')
        )
        return invoice

    def update(self, instance, validated_data):
        """
        [AGRI-GUARDIAN] Delegates to SaleService.update_invoice()
        """
        items_data = validated_data.pop('items', None)
        
        request = self.context.get('request')
        user = request.user if request else None
        
        from smart_agri.sales.services import SaleService
        invoice = SaleService.update_invoice(
            invoice=instance,
            items_data=items_data,
            user=user,
            **validated_data
        )
        return invoice

from smart_agri.core.api.permissions import user_farm_ids

class CustomerViewSet(AuditedModelViewSet):
    """
    @idempotent
    """
    serializer_class = CustomerSerializer
    model_name = "Customer"
    enforce_idempotency = True

    def get_queryset(self):
        # [Agri-Guardian] Global Resource Note: 
        # Customers are shared across the system (no farm_id on model).
        # We return all non-deleted customers to authenticated users.
        return Customer.objects.filter(deleted_at__isnull=True)

class SalesInvoiceViewSet(AuditedModelViewSet):
    """
    @idempotent
    """
    serializer_class = SalesInvoiceSerializer
    model_name = "SalesInvoice"
    enforce_idempotency = True
    throttle_classes = [FinancialMutationThrottle]

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except DjangoPermissionDenied as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except DjangoValidationError as exc:
            detail = exc.messages if hasattr(exc, "messages") else [str(exc)]
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        try:
            return super().partial_update(request, *args, **kwargs)
        except DjangoPermissionDenied as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except DjangoValidationError as exc:
            detail = exc.messages if hasattr(exc, "messages") else [str(exc)]
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        # [Agri-Guardian] Fixed: Removed 'farm' from select_related (Zombie Column)
        # Added 'location__farm' to optimize farm property access
        qs = SalesInvoice.objects.filter(deleted_at__isnull=True).select_related('customer', 'location', 'location__farm').prefetch_related('items').order_by('-invoice_date', '-id')
        
        # [Agri-Guardian] Tenant Isolation (via Location)
        user = self.request.user
        if not user.is_superuser:
             farm_ids = user_farm_ids(user)
             qs = qs.filter(location__farm_id__in=farm_ids)
             
        # [Agri-Guardian] Optional specific farm filter
        farm_id_param = self.request.query_params.get('farm_id') or self.request.query_params.get('farm')
        if farm_id_param:
            try:
                fid = int(farm_id_param)
                qs = qs.filter(location__farm_id=fid)
            except ValueError:
                pass

        # [Agri-Guardian] Optional crop and period filter
        crop_param = self.request.query_params.get('crop')
        if crop_param:
            qs = qs.filter(items__harvest_lot__crop_plan__crop_id=crop_param).distinct()

        period_param = self.request.query_params.get('period')
        if period_param:
            try:
                from smart_agri.finance.models import FiscalPeriod
                period = FiscalPeriod.objects.get(id=period_param)
                qs = qs.filter(invoice_date__gte=period.start_date, invoice_date__lte=period.end_date)
            except (ValidationError, OperationalError, ObjectDoesNotExist) as exc:
                logger.warning("Invalid period filter '%s': %s", period_param, exc)
                
        return qs

    from rest_framework.decorators import action

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        [Agri-Guardian] Server-Side Aggregation for Accurate Financial Reporting.
        Calculates total revenue, count, and average for the filtered queryset.
        Respects all active filters (tenancy, date, customer, etc.)
        """
        qs = self.filter_queryset(self.get_queryset())
        
        # Aggregate in DB
        stats = qs.aggregate(
            total_revenue=Sum('total_amount'),
            invoice_count=Count('id'),
            average_invoice=Avg('total_amount')
        )
        
        return Response({
            'total_revenue': stats['total_revenue'] or 0,
            'invoice_count': stats['invoice_count'] or 0,
            'average_invoice': stats['average_invoice'] or 0
        })

    from rest_framework.decorators import action

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        from smart_agri.sales.services import SaleService
        try:
            with transaction.atomic():
                invoice = self.get_object()
                SaleService.confirm_sale(invoice, user=request.user)
                response = Response({'status': 'confirmed'})
                self._commit_action_idempotency(request, key, object_id=str(invoice.id), response=response)
        except DjangoPermissionDenied as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except DjangoValidationError as exc:
            detail = exc.messages if hasattr(exc, "messages") else [str(exc)]
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return response

    @action(detail=True, methods=['get'], url_path='confirm-check')
    def confirm_check(self, request, pk=None):
        from smart_agri.sales.services import SaleService
        try:
            invoice = self.get_object()
            SaleService.check_confirmability(invoice, user=request.user)
            return Response({'ok': True, 'message': ''})
        except DjangoPermissionDenied as exc:
            return Response({'ok': False, 'message': str(exc)}, status=status.HTTP_200_OK)
        except DjangoValidationError as exc:
            detail = exc.messages if hasattr(exc, "messages") else [str(exc)]
            message = " - ".join(detail) if isinstance(detail, (list, tuple)) else str(detail)
            return Response({'ok': False, 'message': message}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        from smart_agri.sales.services import SaleService
        try:
            with transaction.atomic():
                invoice = self.get_object()
                SaleService.cancel_sale(invoice, user=request.user)
                response = Response({'status': 'cancelled'})
                self._commit_action_idempotency(request, key, object_id=str(invoice.id), response=response)
        except DjangoValidationError as exc:
            detail = exc.messages if hasattr(exc, "messages") else [str(exc)]
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        return response

    @action(detail=True, methods=['get'])
    def invoice(self, request, pk=None):
        """Generate a PDF invoice ready for download/archival."""
        from django.http import HttpResponse
        from smart_agri.core.utils.pdf_generator import FinancialReportPDF

        invoice = (
            SalesInvoice.objects.select_related('customer', 'location', 'location__farm')
            .prefetch_related('items__item')
            .get(pk=self.get_object().pk)
        )

        farm_name = '-'
        if invoice.location_id and getattr(invoice.location, 'farm', None):
            farm_name = invoice.location.farm.name
        elif getattr(invoice, 'farm_id', None) and getattr(invoice, 'farm', None):
            farm_name = invoice.farm.name

        report = FinancialReportPDF(
            title=f"فاتورة مبيعات #{invoice.invoice_number}",
            subtitle=f"{farm_name} • {invoice.invoice_date}",
        )
        report.add_table(
            headers=['البيان', 'القيمة'],
            data_rows=[
                ['العميل', invoice.customer.name],
                ['المزرعة', farm_name],
                ['الحالة', invoice.get_status_display()],
                ['الإجمالي', invoice.total_amount],
            ],
        )
        report.add_table(
            headers=['الصنف', 'الكمية', 'الإجمالي'],
            data_rows=[
                [item.item.name, item.qty, item.total]
                for item in invoice.items.all().order_by('id')
            ] or [['لا توجد أصناف', '0', '0']],
        )
        pdf_bytes = report.generate()
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.id}.pdf"'
        return response

from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'sales-invoices', SalesInvoiceViewSet, basename='sales-invoices')
router.register(r'customers', CustomerViewSet, basename='customers')
