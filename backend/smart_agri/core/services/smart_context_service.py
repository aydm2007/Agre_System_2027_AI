
import logging
from datetime import timedelta
from typing import List, Dict, Any
from django.db.models import Count
from django.utils import timezone
from smart_agri.core.models.log import DailyLog
from smart_agri.core.models.activity import Activity

logger = logging.getLogger(__name__)

class SmartContextService:
    """
    Agri-Guardian 'Oracle' Service.
    Analyzes historical patterns to predict today's tasks.
    """
    
    @staticmethod
    def get_suggestions(user, date_str: str) -> List[Dict[str, Any]]:
        """
        Returns a list of suggested activities based on:
        1. Same day last year (+/- 7 days window).
        2. Recent repetitive tasks (last 30 days).
        """
        try:
            target_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
            suggestions = []
            
            # Strategy 1: The "Cycle of Life" (Last Year)
            last_year_start = target_date - timedelta(days=365 + 7)
            last_year_end = target_date - timedelta(days=365 - 7)
            
            historical_activities = Activity.objects.filter(
                log__log_date__range=(last_year_start, last_year_end),
                log__farm__in=user.farm_set.all() # Ensure permission scope
            ).values(
                'activity_type', 
                'crop__id', 'crop__name', 
                'location__id', 'location__name',
                'log__farm__id'
            ).annotate(count=Count('id')).order_by('-count')
            
            for item in historical_activities:
                suggestions.append({
                    'type': 'historical',
                    'label': f"Repeat Last Year: {item['activity_type']} on {item['location__name']}",
                    'data': {
                        'farm': item['log__farm__id'],
                        'location': item['location__id'],
                        'crop': item['crop__id'],
                        'task': None, # Task is tricky if it's not generic, we might need task_id from activity
                        'activity_type': item['activity_type']
                    },
                    'confidence': 'high'
                })
                
            return suggestions
            
        except (ValidationError, OperationalError, AttributeError) as e:
            logger.error(f"Smart Context Failure: {e}")
            return []
