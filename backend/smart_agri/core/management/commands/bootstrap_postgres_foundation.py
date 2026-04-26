from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from smart_agri.accounts.models import FarmGovernanceProfile, FarmMembership, RaciTemplate
from smart_agri.core.models import Farm, FarmSettings


User = get_user_model()

TIER_POLICY_DEFAULTS = {
    Farm.TIER_SMALL: {
        'mode': FarmSettings.MODE_SIMPLE,
        'approval_profile': FarmSettings.APPROVAL_PROFILE_TIERED,
        'variance_behavior': FarmSettings.VARIANCE_BEHAVIOR_WARN,
        'cost_visibility': FarmSettings.COST_VISIBILITY_RATIOS_ONLY,
        'contract_mode': FarmSettings.CONTRACT_MODE_OPERATIONAL_ONLY,
        'treasury_visibility': FarmSettings.TREASURY_VISIBILITY_FINANCE_ONLY,
        'fixed_asset_mode': FarmSettings.FIXED_ASSET_MODE_TRACKING_ONLY,
        'single_finance_officer_allowed': True,
        'local_finance_threshold': '100000.0000',
        'sector_review_threshold': '250000.0000',
        'procurement_committee_threshold': '500000.0000',
        'mandatory_attachment_for_cash': True,
        'remote_site': False,
        'weekly_remote_review_required': False,
    },
    Farm.TIER_MEDIUM: {
        'mode': FarmSettings.MODE_STRICT,
        'approval_profile': FarmSettings.APPROVAL_PROFILE_TIERED,
        'variance_behavior': FarmSettings.VARIANCE_BEHAVIOR_QUARANTINE,
        'cost_visibility': FarmSettings.COST_VISIBILITY_SUMMARIZED,
        'contract_mode': FarmSettings.CONTRACT_MODE_OPERATIONAL_ONLY,
        'treasury_visibility': FarmSettings.TREASURY_VISIBILITY_FINANCE_ONLY,
        'fixed_asset_mode': FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION,
        'single_finance_officer_allowed': False,
        'local_finance_threshold': '150000.0000',
        'sector_review_threshold': '350000.0000',
        'procurement_committee_threshold': '750000.0000',
        'mandatory_attachment_for_cash': True,
        'remote_site': True,
        'weekly_remote_review_required': True,
    },
    Farm.TIER_LARGE: {
        'mode': FarmSettings.MODE_STRICT,
        'approval_profile': FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE,
        'variance_behavior': FarmSettings.VARIANCE_BEHAVIOR_BLOCK,
        'cost_visibility': FarmSettings.COST_VISIBILITY_SUMMARIZED,
        'contract_mode': FarmSettings.CONTRACT_MODE_FULL_ERP,
        'treasury_visibility': FarmSettings.TREASURY_VISIBILITY_FINANCE_ONLY,
        'fixed_asset_mode': FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION,
        'single_finance_officer_allowed': False,
        'local_finance_threshold': '250000.0000',
        'sector_review_threshold': '500000.0000',
        'procurement_committee_threshold': '1000000.0000',
        'mandatory_attachment_for_cash': True,
        'remote_site': True,
        'weekly_remote_review_required': True,
    },
}

RACI_DEFAULTS = [
    (
        'قالب مزرعة صغيرة (مرجعي V38)',
        FarmGovernanceProfile.TIER_SMALL,
        {
            'daily_operations': {'R': 'مشرف ميداني', 'A': 'مدير المزرعة', 'C': 'فني زراعي', 'I': 'محاسب المزرعة'},
            'finance_close': {'R': 'رئيس الحسابات', 'A': 'رئيس الحسابات', 'C': 'مدير المزرعة', 'I': 'محاسب القطاع'},
            'petty_cash': {'R': 'أمين صندوق', 'A': 'رئيس الحسابات', 'C': 'محاسب المزرعة', 'I': 'مدير المزرعة'},
        },
    ),
    (
        'قالب مزرعة متوسطة (مرجعي V38)',
        FarmGovernanceProfile.TIER_MEDIUM,
        {
            'daily_operations': {'R': 'مشرف ميداني', 'A': 'مدير المزرعة', 'C': 'مهندس زراعي', 'I': 'رئيس الحسابات'},
            'finance_close': {'R': 'رئيس الحسابات', 'A': 'المدير المالي للمزرعة', 'C': 'محاسب المزرعة', 'I': 'محاسب القطاع'},
            'sector_lane': {'R': 'محاسب القطاع', 'A': 'رئيس حسابات القطاع', 'C': 'مراجع القطاع', 'I': 'مدير القطاع'},
        },
    ),
    (
        'قالب مزرعة كبيرة (مرجعي V38)',
        FarmGovernanceProfile.TIER_LARGE,
        {
            'daily_operations': {'R': 'مشرف ميداني', 'A': 'مدير المزرعة', 'C': 'مهندس زراعي', 'I': 'رئيس الحسابات'},
            'finance_close': {'R': 'رئيس الحسابات', 'A': 'المدير المالي للمزرعة', 'C': 'محاسب المزرعة', 'I': 'محاسب القطاع'},
            'sector_lane': {'R': 'محاسب القطاع', 'A': 'المدير المالي لقطاع المزارع', 'C': 'رئيس حسابات القطاع', 'I': 'مدير القطاع'},
        },
    ),
]

FINANCE_LEAD_ROLES = {
    Farm.TIER_MEDIUM: 'المدير المالي للمزرعة',
    Farm.TIER_LARGE: 'المدير المالي للمزرعة',
}


class Command(BaseCommand):
    help = 'Bootstrap a PostgreSQL-backed reference foundation with roles, farms, settings, permissions, and demo data.'

    def add_arguments(self, parser):
        parser.add_argument('--skip-migrate', action='store_true', help='Skip migrate step if already applied.')
        parser.add_argument('--skip-demo-data', action='store_true', help='Seed only roles/settings without full demo dataset.')
        parser.add_argument('--default-password', dest='default_password', help='Password for demo users created by seed_full_system.')
        parser.add_argument('--snapshot-path', dest='snapshot_path', help='Optional path for writing JSON bootstrap snapshot.')
        parser.add_argument('--allow-non-postgres', action='store_true', help='Allow execution on non-PostgreSQL databases for diagnostics only.')

    def handle(self, *args, **options):
        vendor = connection.vendor
        db_name = connection.settings_dict.get('NAME')
        if vendor != 'postgresql' and not options.get('allow_non_postgres'):
            raise CommandError('bootstrap_postgres_foundation requires PostgreSQL as the authoritative database path.')

        if not options.get('skip_migrate'):
            call_command('migrate', interactive=False, verbosity=0)

        call_command('seed_roles', verbosity=0)
        self._seed_reference_catalogs()
        self._ensure_raci_templates()

        if not options.get('skip_demo_data'):
            kwargs = {'verbose': False}
            if options.get('default_password'):
                kwargs['default_password'] = options['default_password']
            call_command('seed_full_system', **kwargs)

        snapshot = self._ensure_governed_foundation(vendor=vendor, db_name=db_name)
        output_path = self._write_snapshot(snapshot=snapshot, explicit_path=options.get('snapshot_path'))
        self.stdout.write(self.style.SUCCESS(f'bootstrap_postgres_foundation_ready: {output_path}'))
        self.stdout.write(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str))

    def _seed_reference_catalogs(self):
        for command in (
            'seed_yemen_units',
            'seed_standard_data',
            'seed_operational_catalog',
            'seed_crop_products',
        ):
            try:
                call_command(command, verbosity=0)
            except Exception as exc:  # explicit operational surface for bootstrap summary
                self.stdout.write(self.style.WARNING(f'{command} skipped: {exc}'))

    def _ensure_raci_templates(self):
        for name, tier, matrix in RACI_DEFAULTS:
            RaciTemplate.objects.update_or_create(
                name=name,
                defaults={
                    'tier': tier,
                    'version': 'v38',
                    'matrix': matrix,
                    'is_active': True,
                },
            )

    @transaction.atomic
    def _ensure_governed_foundation(self, *, vendor: str, db_name: str):
        farms_snapshot = []
        for farm in Farm.objects.order_by('id'):
            tier = (getattr(farm, 'tier', None) or Farm.TIER_SMALL).upper()
            if tier not in TIER_POLICY_DEFAULTS:
                tier = Farm.TIER_SMALL
            governance_profile, _ = FarmGovernanceProfile.objects.get_or_create(
                farm=farm,
                defaults={
                    'tier': tier,
                    'rationale': f'Auto-governed bootstrap aligned to area/tier at {timezone.now():%Y-%m-%d %H:%M}',
                },
            )
            if governance_profile.tier != tier:
                governance_profile.tier = tier
                governance_profile.rationale = f'Normalized to farm tier during bootstrap at {timezone.now():%Y-%m-%d %H:%M}'
                governance_profile.save(update_fields=['tier', 'rationale', 'updated_at'])

            settings_obj, _ = FarmSettings.objects.get_or_create(farm=farm)
            defaults = TIER_POLICY_DEFAULTS[tier]
            changed_fields = []
            for field, value in defaults.items():
                if getattr(settings_obj, field) != value:
                    setattr(settings_obj, field, value)
                    changed_fields.append(field)
            if changed_fields:
                settings_obj.save(update_fields=changed_fields + ['updated_at'])

            required_role = FINANCE_LEAD_ROLES.get(tier)
            finance_lead_present = True
            if required_role:
                finance_lead_present = FarmMembership.objects.filter(farm=farm, role=required_role).exists()
                if not finance_lead_present:
                    candidate = User.objects.filter(username__in=['finance_dir', 'chief_acct', 'ibrahim']).first()
                    if candidate:
                        FarmMembership.objects.update_or_create(
                            user=candidate,
                            farm=farm,
                            defaults={'role': required_role},
                        )
                        finance_lead_present = True

            memberships = list(FarmMembership.objects.filter(farm=farm).values_list('role', flat=True))
            farms_snapshot.append(
                {
                    'id': farm.id,
                    'name': farm.name,
                    'slug': farm.slug,
                    'tier': tier,
                    'mode': settings_obj.mode,
                    'approval_profile': settings_obj.approval_profile,
                    'remote_site': settings_obj.remote_site,
                    'weekly_remote_review_required': settings_obj.weekly_remote_review_required,
                    'single_finance_officer_allowed': settings_obj.single_finance_officer_allowed,
                    'finance_lead_present': finance_lead_present,
                    'membership_roles': sorted(memberships),
                }
            )

        return {
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'database_vendor': vendor,
            'database_name': db_name,
            'farms_total': Farm.objects.count(),
            'users_total': User.objects.count(),
            'groups_total': Group.objects.count(),
            'farm_memberships_total': FarmMembership.objects.count(),
            'governance_profiles_total': FarmGovernanceProfile.objects.count(),
            'farm_settings_total': FarmSettings.objects.count(),
            'raci_templates_total': RaciTemplate.objects.count(),
            'permissions_by_group': [
                {
                    'group': group.name,
                    'permission_count': group.permissions.count(),
                }
                for group in Group.objects.order_by('name')
            ],
            'farms': farms_snapshot,
        }

    def _write_snapshot(self, *, snapshot: dict, explicit_path: str | None):
        if explicit_path:
            output_path = Path(explicit_path)
        else:
            root = Path(settings.BASE_DIR).parent
            out_dir = root / 'docs' / 'evidence' / 'bootstrap'
            out_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            output_path = out_dir / f'postgres_reference_foundation_{stamp}.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        return output_path
