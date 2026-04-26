from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from smart_agri.core.models.pos import POSSession, POSOrder
from smart_agri.core.services.pos_service import POSService
from smart_agri.core.utils import get_current_farm

class POSSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = POSSession.objects.all()
    
    def get_queryset(self):
        farm = get_current_farm(self.request)
        return super().get_queryset().filter(farm=farm)
    
    @action(detail=False, methods=['post'])
    def open_session(self, request):
        """فتح جلسة بيع جديدة"""
        farm = get_current_farm(request)
        device_id = request.data.get('device_id')
        opening_balance = request.data.get('opening_balance', 0)
        
        if not device_id:
            return Response({'error': 'device_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        service = POSService(farm)
        session = service.open_session(device_id, request.user.username, opening_balance)
        return Response({
            'session_id': session.session_id,
            'id': session.id
        })
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """مزامنة الطلبات غير المتزامنة للجلسة"""
        session = self.get_object()
        service = POSService(session.farm)
        service.sync_offline_orders(session)
        return Response({'status': 'Sync initiated'})

class POSOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = POSOrder.objects.all()
    
    def get_queryset(self):
        farm = get_current_farm(self.request)
        return super().get_queryset().filter(session__farm=farm)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """إنشاء طلبات متعددة (لمزامنة الـ Offline)"""
        # Logic to be implemented if needed for batch sync
        return Response({'status': 'Bulk creation received'})
