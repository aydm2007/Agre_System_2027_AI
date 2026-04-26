from decimal import Decimal
from smart_agri.core.constants import DailyLogStatus
from smart_agri.core.models.log import DailyLog


class ManualBiophysicalAnalyzer:
    """
    YECO COMPLIANT: Replaces automated monitoring.
    Analyzes manual observations from DailyLogs to detect anomalies.
    No IoT/Sensor data allowed.
    """

    @staticmethod
    def analyze_tree_health(tree_id, observation_period_days=7):
        # Fetch ONLY finalized (Approved) manual logs
        logs = DailyLog.objects.filter(
            observation_data__tree_id=tree_id,
            status=DailyLogStatus.APPROVED,
            observation_data__isnull=False,
        ).order_by('-log_date')[:observation_period_days]

        health_score = Decimal('100.0000')
        risk_flags = []

        for log in logs:
            obs = log.observation_data or {}
            notes = obs.get('notes', '')

            # Look for keywords used by Yemeni supervisors
            if 'اصفرار' in notes:
                health_score -= Decimal('5.0000')
                risk_flags.append(f"Yellowing reported on {log.log_date}")

            # Manual soil check (The 'Sikh' method result)
            if obs.get('soil_moisture_manual') == 'DRY_CRACKED':
                health_score -= Decimal('15.0000')
                risk_flags.append(f"Severe drought signs on {log.log_date}")

            # Manual pest observation
            if obs.get('pest_signs') == 'CONFIRMED' or 'آفات' in notes:
                health_score -= Decimal('10.0000')
                risk_flags.append(f"Pest signs reported on {log.log_date}")

        return {
            'tree_id': tree_id,
            'health_index': max(health_score, Decimal('0.0000')),
            'risk_factors': risk_flags,
            'data_source': 'MANUAL_LOG_ONLY',
        }
