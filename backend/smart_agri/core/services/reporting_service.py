from django.conf import settings
from decimal import Decimal
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    arabic_reshaper = None
    get_display = None

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import logging

from smart_agri.core.models.report import AsyncReportRequest

logger = logging.getLogger(__name__)

class ArabicReportService:
    """
    [AGRI-GUARDIAN] AgriAsset Yemen: RTL PDF Support.
    Fixes broken/disjointed Arabic characters in PDF exports.
    Protocol XXVIII: The Readable Report Standard.
    """
    
    def __init__(self):
        # Register Arabic Font (Must be present in static files)
        # Deployed from: public/fonts/Amiri-Regular.ttf -> backend/smart_agri/static/fonts/
        font_path = os.path.join(settings.BASE_DIR, 'smart_agri', 'static', 'fonts', 'Amiri-Regular.ttf')
        try:
             # Check if file exists to avoid crash, though ReportLab might need absolute path
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('Amiri', font_path))
            else:
                logger.warning(f"Arabic Font not found at {font_path}. Reports may be garbled.")
        except (ValidationError, OperationalError, ObjectDoesNotExist) as e:
            logger.warning(f"Failed to register Arabic font: {e}")

    def _process_text(self, text):
        """
        Reshapes Arabic text to be rendered correctly in PDF.
        """
        if not text: return ""
        
        if arabic_reshaper and get_display:
            try:
                reshaped_text = arabic_reshaper.reshape(str(text))
                bidi_text = get_display(reshaped_text)
                return bidi_text
            except (ValidationError, OperationalError, ObjectDoesNotExist) as e:
                logger.error(f"Text shaping failed: {e}")
                return text
        return text

    def _format_money(self, amount):
        if amount is None:
            return "0.00"
        return f"{Decimal(amount):,.2f}"

    def generate_profitability_pdf(self, params: dict) -> bytes:
        """
        Generates the Advanced Financial Report (Profitability/Income Statement)
        Filtered by Farm, Cost Center, and Crop Plan.
        Returns the PDF as bytes.
        """
        from smart_agri.finance.models import FinancialLedger
        from django.db.models import Sum
        from decimal import Decimal
        from smart_agri.core.utils.pdf_generator import FinancialReportPDF
        
        # 1. Extract Filters
        farm_id = params.get('farm_id') or params.get('farm')
        cost_center_id = params.get('cost_center_id')
        crop_plan_id = params.get('crop_plan_id')
        start_date = params.get('start') or params.get('start_date')
        end_date = params.get('end') or params.get('end_date')
        
        # 2. Build Query
        qs = FinancialLedger.objects.filter(deleted_at__isnull=True)
        if farm_id:
            raw_farm_id = str(farm_id).split(",")[0].strip()
            qs = qs.filter(farm_id=raw_farm_id)
        if cost_center_id:
            qs = qs.filter(cost_center_id=cost_center_id)
        if crop_plan_id:
            qs = qs.filter(crop_plan_id=crop_plan_id)
        if start_date:
            qs = qs.filter(transaction_date__gte=start_date)
        if end_date:
            qs = qs.filter(transaction_date__lte=end_date)
            
        # 3. Aggregate Data
        # Group by account_code
        rows = qs.values('account_code').annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        ).order_by('account_code')
        
        # 4. Prepare PDF
        title = "التقرير المالي التحليلي المتقدم"
        subtitle = "ميزان المراجعة وقائمة الدخل المصغرة"
        if start_date and end_date:
            subtitle += f" ({start_date} إلى {end_date})"
            
        pdf_gen = FinancialReportPDF(title=title, subtitle=subtitle)
        headers = ["الرصيد الدائن", "الرصيد المدين", "رقم الحساب"]
        
        table_data = []
        grand_debit = Decimal("0.0000")
        grand_credit = Decimal("0.0000")
        
        for row in rows:
            dr = row['total_debit'] or Decimal("0.0000")
            cr = row['total_credit'] or Decimal("0.0000")
            code = row['account_code'] or "غير محدد"
            
            grand_debit += dr
            grand_credit += cr
            
            # Note: Columns ordered Right to Left for Arabic reading (Credit, Debit, Account)
            table_data.append([
                self._format_money(cr),
                self._format_money(dr),
                code
            ])
            
        # Add Totals Row
        table_data.append([
            self._format_money(grand_credit),
            self._format_money(grand_debit),
            "الإجمالي"
        ])
        
        pdf_gen.add_table(headers=headers, data_rows=table_data)
        
        # Net Income Calculation
        # Assuming Revenue = Accounts starting with 4, Expense = Accounts starting with 7
        # simplified for demonstration:
        revenue = sum(r['total_credit'] or 0 for r in rows if str(r['account_code']).startswith('4'))
        expense = sum(r['total_debit'] or 0 for r in rows if str(r['account_code']).startswith('7'))
        net_income = revenue - expense
        
        summary_headers = ["القيمة", "البيان"]
        summary_data = [
            [self._format_money(revenue), "إجمالي الإيرادات (صنف 4)"],
            [self._format_money(expense), "إجمالي المصروفات (صنف 7)"],
            [self._format_money(net_income), "صافي الربح / (الخسارة) التشغيلية"]
        ]
        pdf_gen.add_table(headers=summary_headers, data_rows=summary_data)
        
        return pdf_gen.generate()

    def generate_commercial_pdf(self, params: dict) -> bytes:
        from smart_agri.core.services.commercial_reporting_service import CommercialReportingService

        return CommercialReportingService.generate_commercial_pdf(params)

    @staticmethod
    def request_async_profitability_report(user, params=None):
        params = params or {}
        request = AsyncReportRequest.objects.create(
            created_by=user,
            report_type=AsyncReportRequest.REPORT_PROFITABILITY,
            params=params,
        )
        # Lazy import avoids circular dependency with report_tasks importing this service.
        from smart_agri.core.tasks.report_tasks import generate_profitability_report
        generate_profitability_report.delay(request.id)
        return request
