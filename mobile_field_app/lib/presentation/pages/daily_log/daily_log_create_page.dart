import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:agriasset_field_app/core/theme/app_theme.dart';
import 'package:agriasset_field_app/presentation/widgets/shared/glass_card.dart';
import 'package:agriasset_field_app/presentation/blocs/auth_bloc.dart';
import 'package:agriasset_field_app/data/sources/local/offline_storage.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:geolocator/geolocator.dart';
import 'package:agriasset_field_app/data/models/daily_log_model.dart';

class DailyLogCreatePage extends StatefulWidget {
  const DailyLogCreatePage({super.key});

  @override
  State<DailyLogCreatePage> createState() => _DailyLogCreatePageState();
}

class _DailyLogCreatePageState extends State<DailyLogCreatePage> {
  final _formKey = GlobalKey<FormState>();
  
  // Governed State
  int? _selectedCropId;
  String? _selectedActivity;
  double _achievementQty = 0;
  int _workerCount = 0;
  bool _isGpsEnabled = false; // [AGR-GUARDIAN] Optional GPS toggle
  Position? _currentPosition;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: Text("إضافة سجل يومي جديد", style: GoogleFonts.notoKufiArabic(fontWeight: FontWeight.bold, fontSize: 18)),
        actions: [
          TextButton(
            onPressed: _submitLog,
            child: Text("حفظ", style: GoogleFonts.notoKufiArabic(color: AppTheme.accentColor, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
      body: Directionality(
        textDirection: TextDirection.rtl,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // 1. Geography & Trust Card
                _buildGpsToggleCard(),
                const SizedBox(height: 24),

                // 2. Core Operational Details
                _buildStockIndicator(), // [AGRI-GUARDIAN] Axis 26 Awareness
                const SizedBox(height: 12),
                _buildOperationCard(),
                const SizedBox(height: 24),

                // 3. Labor & Achievement Card
                _buildLaborCard(),
                const SizedBox(height: 24),
                
                // 4. Materials Card (Placeholder for now)
                _buildMaterialsCard(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildGpsToggleCard() {
    return GlassCard(
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("سجل الموقع الجغرافي", style: GoogleFonts.notoKufiArabic(fontWeight: FontWeight.bold)),
                  Text("اختياري للمناطق ذات التغطية الضعيفة", 
                    style: GoogleFonts.notoKufiArabic(fontSize: 11, color: Colors.white54)),
                ],
              ),
              Switch(
                value: _isGpsEnabled,
                onChanged: (val) async {
                  setState(() => _isGpsEnabled = val);
                  if (val) await _fetchGps();
                },
                activeColor: AppTheme.accentColor,
              ),
            ],
          ),
          if (_isGpsEnabled && _currentPosition != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Row(
                children: [
                  const Icon(Icons.location_on, color: Colors.greenAccent, size: 16),
                  const SizedBox(width: 8),
                  Text(
                    "إحداثيات مؤمنة: ${_currentPosition!.latitude.toStringAsFixed(4)}, ${_currentPosition!.longitude.toStringAsFixed(4)}",
                    style: GoogleFonts.outfit(fontSize: 12, color: Colors.white70),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildOperationCard() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("تفاصيل الدورة الزراعية", style: GoogleFonts.notoKufiArabic(fontWeight: FontWeight.bold, color: AppTheme.accentColor)),
          const SizedBox(height: 20),
          
          // Real Crop Dropdown
          ValueListenableBuilder(
            valueListenable: Hive.box(OfflineStorage.cropsBox).listenable(),
            builder: (context, Box box, _) {
              final crops = box.values.toList();
              return _buildDropdown(
                label: "المحصول / البلوك",
                value: _selectedCropId,
                items: crops.map((c) => DropdownMenuItem(
                  value: c['id'],
                  child: Text(c['name'], style: GoogleFonts.notoKufiArabic(fontSize: 14)),
                )).toList(),
                onChanged: (val) => setState(() => _selectedCropId = val as int?),
              );
            },
          ),
          
          const SizedBox(height: 16),

          _buildDropdown(
            label: "نوع المهمة",
            value: _selectedActivity,
            items: const [
              DropdownMenuItem(value: "تسميد", child: Text("تسميد ورقابة")),
              DropdownMenuItem(value: "ري", child: Text("ري ومناوبة")),
              DropdownMenuItem(value: "مكافحة", child: Text("رش وقائي")),
            ],
            onChanged: (val) => setState(() => _selectedActivity = val as String?),
          ),
        ],
      ),
    );
  }

  Widget _buildLaborCard() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("العمالة والإنجاز", style: GoogleFonts.notoKufiArabic(fontWeight: FontWeight.bold, color: AppTheme.accentColor)),
          const SizedBox(height: 20),
          
          Row(
            children: [
              Expanded(
                child: _buildNumberField(
                  label: "كمية الإنجاز",
                  onChanged: (val) => _achievementQty = val,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildNumberField(
                  label: "عدد العمال",
                  onChanged: (val) => _workerCount = val.toInt(),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMaterialsCard() {
    return GlassCard(
      color: Colors.white.withOpacity(0.02),
      child: Center(
        child: TextButton.icon(
          onPressed: () {},
          icon: const Icon(Icons.add_shopping_cart_rounded, size: 20),
          label: Text("إضافة مواد مستخدمة", style: GoogleFonts.notoKufiArabic()),
        ),
      ),
    );
  }

  Widget _buildDropdown({required String label, required dynamic value, required List<DropdownMenuItem> items, required void Function(dynamic) onChanged}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: GoogleFonts.notoKufiArabic(fontSize: 12, color: Colors.white54)),
        DropdownButton(
          value: value,
          isExpanded: true,
          underline: Container(height: 1, color: Colors.white24),
          dropdownColor: AppTheme.surfaceColor,
          items: items,
          onChanged: onChanged,
        ),
      ],
    );
  }

  Widget _buildNumberField({required String label, required Function(double) onChanged}) {
    return TextFormField(
      keyboardType: TextInputType.number,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: GoogleFonts.notoKufiArabic(fontSize: 12, color: Colors.white54),
        enabledBorder: const UnderlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
      ),
      onChanged: (val) => onChanged(double.tryParse(val) ?? 0),
    );
  }

  Future<void> _fetchGps() async {
    try {
      Position position = await Geolocator.getCurrentPosition();
      setState(() => _currentPosition = position);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("فشل في تحديد الموقع")));
    }
  }

  void _submitLog() async {
    if (_selectedCropId == null || _selectedActivity == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("يرجى إكمال البيانات الأساسية")));
      return;
    }

    // [AGRI-GUARDIAN] Axis 17: Build technical technical technical technically techn-- 
    final log = DailyLogModel(
      mobileRequestId: "M-LOG-${DateTime.now().millisecondsSinceEpoch}",
      farmId: "1", // Dynamic from context in prod
      cropPlanId: _selectedCropId!.toString(),
      activityType: _selectedActivity!,
      quantity: _achievementQty,
      lat: _currentPosition?.latitude ?? 0,
      lng: _currentPosition?.longitude ?? 0,
      accuracy: _currentPosition?.accuracy ?? 0,
      timestamp: DateTime.now(),
    );

    // Save to Hive (Axis 17)
    final box = Hive.box(OfflineStorage.dailyLogsBox);
    await box.add(log.toJson());

    if (mounted) Navigator.pop(context);
  }

  Widget _buildStockIndicator() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4.0),
      child: GlassCard(
        color: AppTheme.primaryColor.withOpacity(0.1),
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Row(
            children: [
              const Icon(Icons.inventory_2_outlined, color: Colors.blueAccent, size: 24),
              const SizedBox(width: 16),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    "رصيد الأصول البيولوجية (Axis 26)",
                    style: GoogleFonts.notoKufiArabic(color: Colors.white60, fontSize: 10),
                  ),
                  Text(
                    "الرصيد المتاح: 450 شجرة",
                    style: GoogleFonts.notoKufiArabic(
                      color: Colors.white, 
                      fontSize: 14, 
                      fontWeight: FontWeight.bold
                    ),
                  ),
                ],
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.blueAccent.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  "دقيق",
                  style: GoogleFonts.notoKufiArabic(color: Colors.blueAccent, fontSize: 9),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
