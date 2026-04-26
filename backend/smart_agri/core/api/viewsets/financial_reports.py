from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from smart_agri.core.services.financial_reports import FinancialReportService
from smart_agri.core.utils import get_current_farm

class FinancialReportViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_farm(self):
        farm = get_current_farm(self.request)
        if not farm:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("لم يتم تحديد المزرعة النشطة.")
        return farm
    
    @action(detail=False, methods=['get'])
    def trial_balance(self, request):
        """ميزان المراجعة"""
        farm = self.get_farm()
        service = FinancialReportService(farm)
        data = service.get_trial_balance()
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def profit_and_loss(self, request):
        """الأرباح والخسائر"""
        farm = self.get_farm()
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        service = FinancialReportService(farm)
        data = service.get_profit_and_loss(from_date, to_date)
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def balance_sheet(self, request):
        """الميزانية العمومية"""
        farm = self.get_farm()
        service = FinancialReportService(farm)
        data = service.get_balance_sheet()
        return Response(data)
