"""
[AGRI-GUARDIAN] HR/Employee API with Farm Tenant Isolation
"""
from rest_framework import serializers, viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, api_view, permission_classes as perm_dec
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from django_filters import rest_framework as filters

from smart_agri.core.models.hr import Employee, EmploymentContract, Timesheet
from smart_agri.core.api.permissions import user_farm_ids
from smart_agri.core.api.permissions import _ensure_user_has_farm_access
from smart_agri.core.api.viewsets.base import AuditedModelViewSet


# ─────────────────────────────────────────────────────────────────────────────
# SERIALIZERS
# ─────────────────────────────────────────────────────────────────────────────

class EmployeeSerializer(serializers.ModelSerializer):
    """Employee serializer with computed name field for frontend compatibility."""
    name = serializers.SerializerMethodField()
    job_title = serializers.CharField(source='role', read_only=True)
    daily_rate = serializers.SerializerMethodField()
    phone = serializers.CharField(default='', allow_blank=True)
    email = serializers.EmailField(default='', allow_blank=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'farm', 'name', 'first_name', 'last_name', 'employee_id',
            'id_number', 'role', 'job_title', 'category', 'payment_mode',
            'base_salary', 'shift_rate', 'guarantor_name', 'joined_date', 'is_active',
            'phone', 'email', 'daily_rate'
        ]
        extra_kwargs = {
            'first_name': {'write_only': True, 'required': False, 'allow_blank': True},
            'last_name': {'write_only': True, 'required': False, 'allow_blank': True},
            'employee_id': {'required': False, 'allow_blank': True},
            'joined_date': {'required': False},
        }
    
    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def get_daily_rate(self, obj):
        """Get daily rate from active contract."""
        from decimal import Decimal

        if obj.payment_mode in ['SURRA', 'PIECE']:
            return obj.shift_rate

        contract = obj.contracts.filter(is_active=True).first()
        if contract and contract.basic_salary:
            # Calculate daily from monthly (approx 22 working days)
            return (contract.basic_salary / Decimal('22'))
        return Decimal('0.0000')

    def create(self, validated_data):
        # Frontend compatibility fields that do not exist on Employee model.
        validated_data.pop('phone', None)
        validated_data.pop('email', None)

        # Handle 'name' field from frontend
        name = self.initial_data.get('name', '')
        if name and not validated_data.get('first_name'):
            parts = name.strip().split(' ', 1)
            validated_data['first_name'] = parts[0]
            validated_data['last_name'] = parts[1] if len(parts) > 1 else ''

        # Accept daily_rate from form and map it to Surra shift_rate when provided.
        daily_rate = self.initial_data.get('daily_rate')
        if daily_rate not in (None, '') and not validated_data.get('shift_rate'):
            validated_data['shift_rate'] = daily_rate
            
        job_title = self.initial_data.get('job_title')
        if job_title and not validated_data.get('role'):
            validated_data['role'] = job_title
        
        # Generate employee_id if not provided
        if not validated_data.get('employee_id'):
            from django.utils import timezone
            import uuid
            validated_data['employee_id'] = f"EMP-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        
        # Set joined_date if not provided
        if not validated_data.get('joined_date'):
            from django.utils import timezone
            validated_data['joined_date'] = timezone.now().date()
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Frontend sends these fields, but Employee model has no direct columns for them.
        validated_data.pop('phone', None)
        validated_data.pop('email', None)

        daily_rate = self.initial_data.get('daily_rate')
        if daily_rate not in (None, ''):
            validated_data['shift_rate'] = daily_rate

        name = self.initial_data.get('name')
        if name is not None:
            parts = name.strip().split(' ', 1)
            if parts:
                validated_data['first_name'] = parts[0]
                validated_data['last_name'] = parts[1] if len(parts) > 1 else ''

        job_title = self.initial_data.get('job_title')
        if job_title is not None:
            validated_data['role'] = job_title

        return super().update(instance, validated_data)


class EmploymentContractSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.__str__', read_only=True)
    total_package = serializers.DecimalField(
        source='total_monthly_package',
        max_digits=10, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = EmploymentContract
        fields = [
            'id', 'employee', 'employee_name', 'start_date', 'end_date',
            'basic_salary', 'housing_allowance', 'transport_allowance',
            'other_allowance', 'overtime_shift_value', 'is_active', 'total_package'
        ]


class TimesheetSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.__str__', read_only=True)
    activity_name = serializers.CharField(source='activity.name', read_only=True, allow_null=True)
    farm_name = serializers.CharField(source='farm.name', read_only=True)

    class Meta:
        model = Timesheet
        fields = [
            'id', 'employee', 'employee_name', 'farm', 'farm_name', 'date',
            'activity', 'activity_name',
            'surrah_count', 'surrah_overtime', 'is_approved', 'approved_by'
        ]


# ─────────────────────────────────────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────────────────────────────────────

class EmployeeFilter(filters.FilterSet):
    farm = filters.NumberFilter(field_name='farm_id')
    is_active = filters.BooleanFilter(field_name='is_active')
    role = filters.CharFilter(field_name='role')
    category = filters.CharFilter(field_name='category')

    class Meta:
        model = Employee
        fields = ['farm', 'is_active', 'role', 'category']


# ─────────────────────────────────────────────────────────────────────────────
# VIEWSETS
# ─────────────────────────────────────────────────────────────────────────────

class EmployeeViewSet(AuditedModelViewSet):
    """
    [AGRI-GUARDIAN] Employee API with Farm Tenant Isolation
    """
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = EmployeeFilter

    def get_queryset(self):
        qs = Employee.objects.filter(deleted_at__isnull=True).select_related('farm')
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(farm_id__in=user_farm_ids(user))

        # [AGRI-GUARDIAN] Farm tenant isolation
        farm_id = self.request.query_params.get('farm')
        if farm_id:
            qs = qs.filter(farm_id=farm_id)

        return qs.order_by('-is_active', 'first_name')

    def perform_create(self, serializer):
        farm = serializer.validated_data.get('farm')
        if farm and not self.request.user.is_superuser:
            _ensure_user_has_farm_access(self.request.user, farm.id)
        serializer.save()

    def perform_update(self, serializer):
        farm = serializer.validated_data.get('farm') or serializer.instance.farm
        if farm and not self.request.user.is_superuser:
            _ensure_user_has_farm_access(self.request.user, farm.id)
        serializer.save()


class EmploymentContractViewSet(AuditedModelViewSet):
    serializer_class = EmploymentContractSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = EmploymentContract.objects.filter(deleted_at__isnull=True).select_related('employee')
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(employee__farm_id__in=user_farm_ids(user))

        employee_id = self.request.query_params.get('employee')
        if employee_id:
            qs = qs.filter(employee_id=employee_id)

        return qs.order_by('-is_active', '-start_date')

    def perform_create(self, serializer):
        employee = serializer.validated_data.get('employee')
        if employee and not self.request.user.is_superuser:
            _ensure_user_has_farm_access(self.request.user, employee.farm_id)
        serializer.save()

    def perform_update(self, serializer):
        employee = serializer.validated_data.get('employee') or serializer.instance.employee
        if employee and not self.request.user.is_superuser:
            _ensure_user_has_farm_access(self.request.user, employee.farm_id)
        serializer.save()


class TimesheetViewSet(AuditedModelViewSet):
    """
    [AGRI-GUARDIAN] Timesheet API with Surra-based attendance tracking.
    [Axis 6] Farm-scoped queries mandatory.
    [Axis 5] Surra is the financial labor unit.
    """
    serializer_class = TimesheetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Timesheet.objects.filter(
            deleted_at__isnull=True,
        ).select_related('employee', 'activity', 'farm')
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(farm_id__in=user_farm_ids(user))

        # [Axis 6] Farm filter — mandatory tenant isolation
        farm_id = self.request.query_params.get('farm')
        if farm_id:
            qs = qs.filter(farm_id=farm_id)

        employee_id = self.request.query_params.get('employee')
        if employee_id:
            qs = qs.filter(employee_id=employee_id)

        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        return qs.order_by('-date')

    def perform_create(self, serializer):
        from smart_agri.core.services.timesheet_service import TimesheetService
        data = serializer.validated_data
        employee = data.get('employee')
        farm = data.get('farm') or (employee.farm if employee else None)
        if farm and not self.request.user.is_superuser:
            _ensure_user_has_farm_access(self.request.user, farm.id)
        serializer.save()

    def perform_update(self, serializer):
        employee = serializer.validated_data.get('employee') or serializer.instance.employee
        if employee and not self.request.user.is_superuser:
            _ensure_user_has_farm_access(self.request.user, employee.farm_id)
        serializer.save()

    @action(detail=False, methods=['get'], url_path='monthly-summary')
    def monthly_summary(self, request):
        """
        GET /api/v1/timesheets/monthly-summary/?farm=X&year=Y&month=M
        [Axis 6] Farm-scoped monthly attendance summary.
        [§139] OFFICIAL employees = attendance only (cost=0).
        """
        from smart_agri.core.services.timesheet_service import TimesheetService
        farm_id = request.query_params.get('farm')
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not all([farm_id, year, month]):
            return Response(
                {'detail': 'المعاملات farm, year, month مطلوبة.'},
                status=400,
            )
        if not request.user.is_superuser:
            _ensure_user_has_farm_access(request.user, int(farm_id))

        summary = TimesheetService.get_monthly_summary(
            farm_id=int(farm_id),
            year=int(year),
            month=int(month),
        )
        return Response(summary)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_entry(self, request, pk=None):
        """
        POST /api/v1/timesheets/{id}/approve/
        [Axis 7] Maker-Checker approval with audit trail.
        @idempotent
        """
        from smart_agri.core.services.timesheet_service import TimesheetService

        ts_preview = self.get_object()
        farm_id = ts_preview.farm_id

        key, error_response = self._enforce_action_idempotency(request, farm_id=farm_id)
        if error_response:
            return error_response

        ts = TimesheetService.approve_timesheet(
            timesheet_id=pk,
            approver=request.user,
        )
        final_response = Response(TimesheetSerializer(ts).data, status=status.HTTP_200_OK)
        self._commit_action_idempotency(request, key, object_id=str(ts.pk), response=final_response)
        return final_response


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER REGISTRATION
# ─────────────────────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employees')
router.register(r'employment-contracts', EmploymentContractViewSet, basename='employment-contracts')
router.register(r'timesheets', TimesheetViewSet, basename='timesheets')


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE VIEWS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@perm_dec([IsAuthenticated])
def worker_kpi(request):
    """
    GET /api/v1/worker-kpi/?farm=X&date_from=Y&date_to=Z
    [AGENTS.md §298] Daily labor KPI per farm.
    [Axis 6] Farm-scoped.
    """
    from smart_agri.core.services.worker_productivity_service import WorkerProductivityService
    farm_id = request.query_params.get('farm')
    if not farm_id:
        return Response({'detail': '[Axis 6] معامل farm مطلوب.'}, status=400)

    if not request.user.is_superuser:
        _ensure_user_has_farm_access(request.user, int(farm_id))

    data = WorkerProductivityService.get_labor_kpi(
        farm_id=int(farm_id),
        date_from=request.query_params.get('date_from'),
        date_to=request.query_params.get('date_to'),
    )
    return Response(data)


@api_view(['GET'])
@perm_dec([IsAuthenticated])
def attendance_calendar(request):
    """
    GET /api/v1/attendance-calendar/?farm=X&year=Y&month=M
    [Axis 6] Farm-scoped monthly attendance grid.
    """
    from smart_agri.core.services.attendance_report_service import AttendanceReportService
    farm_id = request.query_params.get('farm')
    year = request.query_params.get('year')
    month = request.query_params.get('month')
    if not all([farm_id, year, month]):
        return Response({'detail': 'المعاملات farm, year, month مطلوبة.'}, status=400)
    if not request.user.is_superuser:
        _ensure_user_has_farm_access(request.user, int(farm_id))
    data = AttendanceReportService.get_monthly_calendar(
        farm_id=int(farm_id), year=int(year), month=int(month),
    )
    return Response(data)


@api_view(['GET', 'POST'])
@perm_dec([IsAuthenticated])
def advances_list(request):
    """
    GET  /api/v1/advances/?farm=X — list advances
    POST /api/v1/advances/ — create advance
    [Axis 6] Farm-scoped.
    """
    from smart_agri.core.services.advances_service import AdvancesService
    if request.method == 'GET':
        farm_id = request.query_params.get('farm')
        if not farm_id:
            return Response({'detail': '[Axis 6] معامل farm مطلوب.'}, status=400)
        if not request.user.is_superuser:
            _ensure_user_has_farm_access(request.user, int(farm_id))
        data = AdvancesService.get_employee_advances(
            farm_id=int(farm_id),
            employee_id=request.query_params.get('employee'),
            status=request.query_params.get('status'),
        )
        return Response(data)

    # POST
    from django.core.exceptions import ValidationError as DjangoValidationError
    try:
        advance = AdvancesService.create_advance(
            employee_id=request.data.get('employee_id'),
            farm_id=request.data.get('farm_id'),
            amount=request.data.get('amount', 0),
            date=request.data.get('date'),
            reason=request.data.get('reason', ''),
            actor=request.user,
            idempotency_key=request.data.get('idempotency_key'),
        )
        return Response({
            'id': advance.id,
            'status': advance.status,
            'amount': str(advance.amount),
        }, status=201)
    except DjangoValidationError as e:
        return Response({'detail': str(e.message_dict if hasattr(e, 'message_dict') else e.message)}, status=400)


@api_view(['POST'])
@perm_dec([IsAuthenticated])
def approve_advance(request, advance_id):
    """
    POST /api/v1/advances/{id}/approve/
    [Axis 7] Maker-Checker.
    """
    from smart_agri.core.services.advances_service import AdvancesService
    from django.core.exceptions import ValidationError as DjangoValidationError
    try:
        advance = AdvancesService.approve_advance(
            advance_id=advance_id, approver=request.user,
        )
        return Response({
            'id': advance.id,
            'status': advance.status,
            'status_display': advance.get_status_display(),
        })
    except DjangoValidationError as e:
        return Response({'detail': str(e.message_dict if hasattr(e, 'message_dict') else e.message)}, status=400)
