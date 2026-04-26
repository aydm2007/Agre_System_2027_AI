from django.core.exceptions import ValidationError
from django.db import transaction

from smart_agri.core.api.permissions import _ensure_user_has_farm_access, user_farm_ids
from smart_agri.finance.models import WorkerAdvance


class WorkerAdvanceService:
    """Governed service-layer entry point for worker cash advances."""

    @staticmethod
    @transaction.atomic
    def create_advance(*, user, worker, amount, notes="") -> WorkerAdvance:
        if worker is None:
            raise ValidationError({"worker": "العامل مطلوب لإثبات السلفة اليومية."})

        if not getattr(user, "is_superuser", False):
            _ensure_user_has_farm_access(user, worker.farm_id)
            allowed_farms = set(user_farm_ids(user))
            if worker.farm_id not in allowed_farms:
                raise ValidationError({"worker": "ليس لديك صلاحية على مزرعة هذا العامل."})

        advance = WorkerAdvance(
            worker=worker,
            amount=amount,
            supervisor=user,
            notes=(notes or "").strip(),
        )
        advance.full_clean()
        advance.save()
        return advance
