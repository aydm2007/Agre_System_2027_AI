"""
Frictionless DailyLog API — بوابة التسجيل المُبسَّط.

A simplified endpoint for field staff to submit daily logs with
ONLY technical inputs. Financial calculations happen server-side.

@idempotent
"""

from decimal import Decimal, InvalidOperation
from rest_framework import viewsets, status, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from smart_agri.core.models import DailyLog
from smart_agri.core.models.farm import Farm, Asset
from smart_agri.core.models.planning import CropPlan
from smart_agri.core.models.settings import Supervisor
from smart_agri.core.services.daily_log_execution import FrictionlessDailyLogService
from smart_agri.core.api.permissions import user_farm_ids
from smart_agri.core.api.viewsets.base import IdempotentCreateMixin


class FrictionlessDailyLogViewSet(IdempotentCreateMixin, viewsets.ViewSet):
    """
    [YECO Hybrid ERP] بوابة التسجيل اليومي المبسط.

    يقبل فقط المدخلات الفنية (عدد العمال، ساعات، قراءات الديبستيك)
    ويحسب التكاليف المالية تلقائياً من الخادم.

    POST /api/v1/frictionless-daily-logs/

    Required body:
    {
        "farm_id": 1,
        "log_date": "2026-02-24",
        "activity_name": "حرث القطعة الشمالية",
        "workers_count": 5,
        "shift_hours": "8.0000",
        "machine_asset_id": 3,          // optional
        "machine_hours": "6.0000",      // optional
        "dipstick_start_liters": "100.0000",  // optional
        "dipstick_end_liters": "82.0000",     // optional
        "supervisor_id": 1,             // optional
        "notes": ""                     // optional
    }

    @idempotent
    """
    permission_classes = [permissions.IsAuthenticated]
    enforce_idempotency = True
    model_name = "DailyLog"

    def get_queryset(self):
        return DailyLog.objects.all()

    def create(self, request):
        return self._handle_idempotent_mutation(request, self._create_impl)

    def _create_impl(self, request):
        """Process a frictionless daily log entry."""
        try:
            data = request.data

            # Required fields
            farm_id = data.get('farm_id')
            if not farm_id:
                raise ValidationError({"farm_id": "farm_id مطلوب (عزل المزرعة إلزامي)."})

            farm = Farm.objects.get(id=farm_id)
            if not request.user.is_superuser and farm.id not in set(user_farm_ids(request.user)):
                raise PermissionDenied("ليس لديك صلاحية على هذه المزرعة.")
            log_date = data.get('log_date')
            activity_name = data.get('activity_name', '')

            if not log_date or not activity_name:
                raise ValidationError({"detail": "log_date و activity_name مطلوبان."})

            # Optional fields with Decimal parsing
            workers_count = int(data.get('workers_count', 0))
            shift_hours = Decimal(str(data.get('shift_hours', '0')))
            machine_hours = Decimal(str(data.get('machine_hours', '0')))
            dipstick_start = Decimal(str(data.get('dipstick_start_liters', '0')))
            dipstick_end = Decimal(str(data.get('dipstick_end_liters', '0')))

            # Optional FK lookups
            machine_asset = None
            machine_asset_id = data.get('machine_asset_id')
            if machine_asset_id:
                machine_asset = Asset.objects.get(id=machine_asset_id)
                if machine_asset.farm_id != farm.id:
                    raise ValidationError({"machine_asset_id": "الأصل المحدد لا يتبع للمزرعة المحددة."})

            # YECO/GEMS: dipstick is mandatory when machine activity is logged.
            if machine_asset and machine_hours > Decimal("0"):
                if dipstick_start <= Decimal("0") or dipstick_end < Decimal("0"):
                    raise ValidationError({"dipstick": "قراءات الديبستك إلزامية عند تشغيل الآلة."})

            supervisor = None
            supervisor_id = data.get('supervisor_id')
            if supervisor_id:
                supervisor = Supervisor.objects.filter(id=supervisor_id, farm_id=farm.id).first()
                if not supervisor:
                    raise ValidationError({"supervisor_id": "المشرف المحدد خارج نطاق المزرعة."})

            crop_plan = None
            crop_plan_id = data.get('crop_plan_id')
            if crop_plan_id:
                crop_plan = CropPlan.objects.filter(id=crop_plan_id, farm_id=farm.id).first()
                if not crop_plan:
                    raise ValidationError({"crop_plan_id": "الخطة المحددة خارج نطاق المزرعة."})

            notes = data.get('notes', '')

            # Delegate to service
            result = FrictionlessDailyLogService.process_technical_log(
                farm=farm,
                log_date=log_date,
                activity_name=activity_name,
                workers_count=workers_count,
                shift_hours=shift_hours,
                machine_asset=machine_asset,
                machine_hours=machine_hours,
                dipstick_start_liters=dipstick_start,
                dipstick_end_liters=dipstick_end,
                supervisor=supervisor,
                notes=notes,
                crop_plan=crop_plan,
                created_by=request.user,
            )

            return Response({
                "message": "تم تسجيل اليومية المبسطة بنجاح.",
                **result,
            }, status=status.HTTP_201_CREATED)

        except Farm.DoesNotExist:
            return Response(
                {"error": "المزرعة المحددة غير موجودة."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except (Asset.DoesNotExist, Supervisor.DoesNotExist, CropPlan.DoesNotExist):
            return Response(
                {"error": "مرجع غير صالح في الطلب (أصل/مشرف/خطة)."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDenied as exc:
            return Response(
                getattr(exc, "detail", {"detail": str(exc)}),
                status=status.HTTP_403_FORBIDDEN,
            )
        except ValidationError as exc:
            return Response(
                getattr(exc, "detail", {"detail": str(exc)}),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (ValueError, TypeError, InvalidOperation) as e:
            return Response(
                {"error": f"قيمة رقمية غير صالحة: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
