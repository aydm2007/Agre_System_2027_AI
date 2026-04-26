from django.apps import apps
from django.db.models import Sum, Avg, Count, Q
from smart_agri.core.models.dynamic_report import ReportTemplate, SavedReport

class ReportBuilderService:
    def __init__(self, farm):
        self.farm = farm
    
    def execute_template(self, template: ReportTemplate, params: dict = None):
        """تنفيذ قالب التقرير وإرجاع البيانات"""
        model = apps.get_model(template.model_name)
        # فرض تصفية المزرعة لضمان أمان البيانات (RLS)
        queryset = model.objects.filter(farm=self.farm)
        
        # تطبيق الفلاتر
        if template.filters:
            filter_q = Q()
            for field, condition in template.filters.items():
                if isinstance(condition, dict) and 'op' in condition:
                    op = condition['op']
                    val = condition['value']
                    filter_q &= Q(**{f"{field}__{op}": val})
                else:
                    filter_q &= Q(**{field: condition})
            queryset = queryset.filter(filter_q)
        
        # تحديد الحقول
        fields = template.fields or ['id']
        
        # التجميع (Aggregation)
        if template.group_by:
            agg_dict = {}
            for agg in template.aggregation:
                func_map = {'sum': Sum, 'avg': Avg, 'count': Count}
                if agg['func'] in func_map:
                    agg_dict[f"{agg['func']}_{agg['field']}"] = func_map[agg['func']](agg['field'])
            
            queryset = queryset.values(*template.group_by).annotate(**agg_dict)
            data = list(queryset)
        else:
            data = list(queryset.values(*fields))
        
        # حفظ النتيجة للرجوع إليها لاحقاً
        saved = SavedReport.objects.create(
            template=template,
            parameters=params or {},
            result_data={'data': data}
        )
        return saved
