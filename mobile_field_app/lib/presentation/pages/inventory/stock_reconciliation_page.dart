import 'package:flutter/material.dart';
import 'package:agriasset_field_app/presentation/widgets/shared/glass_card.dart';
import 'package:agriasset_field_app/core/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';

class StockReconciliationPage extends StatefulWidget {
  const StockReconciliationPage({super.key});

  @override
  State<StockReconciliationPage> createState() => _StockReconciliationPageState();
}

class _StockReconciliationPageState extends State<StockReconciliationPage> {
  final _formKey = GlobalKey<FormState>();
  int? _selectedLocationId;
  int? _selectedVarietyId;
  int _actualCount = 0;
  String? _notes;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.obsidianBlack,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          "مطابقة أرصدة الأشجار",
          style: GoogleFonts.notoKufiArabic(color: Colors.white),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildInstructionCard(),
              const SizedBox(height: 24),
              _buildSelectionSection(),
              const SizedBox(height: 24),
              _buildCountingSection(),
              const SizedBox(height: 32),
              _buildSubmitButton(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInstructionCard() {
    return GlassCard(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            const Icon(Icons.info_outline, color: Colors.blueAccent, size: 28),
            const SizedBox(width: 16),
            Expanded(
              child: Text(
                "استخدم هذه الواجهة لمطابقة رصيد الأشجار الفعلي في الموقع مع السجل النظامي (Axis 26).",
                style: GoogleFonts.notoKufiArabic(color: Colors.white70, fontSize: 13),
              ),
            ),
          ],
        ),
      ),
    ).animate().fadeIn().slideY();
  }

  Widget _buildSelectionSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          "تحديد الموقع والصنف",
          style: GoogleFonts.notoKufiArabic(color: Colors.greenAccent, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 16),
        // Simplified dropdowns for this example, would use MasterDataRepository in real impl
        _buildDropdown(label: "الموقع", value: _selectedLocationId, items: [
          const DropdownMenuItem(value: 1, child: Text("مربع أ - حقل 1")),
          const DropdownMenuItem(value: 2, child: Text("مربع ب - حقل 2")),
        ], onChanged: (v) => setState(() => _selectedLocationId = v)),
        const SizedBox(height: 16),
        _buildDropdown(label: "الصنف", value: _selectedVarietyId, items: [
          const DropdownMenuItem(value: 1, child: Text("نخيل خلاص")),
          const DropdownMenuItem(value: 2, child: Text("مانجو خارجي")),
        ], onChanged: (v) => setState(() => _selectedVarietyId = v)),
      ],
    );
  }

  Widget _buildCountingSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          "الجرد الفعلي",
          style: GoogleFonts.notoKufiArabic(color: Colors.greenAccent, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 16),
        GlassCard(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  "العدد الفعلي المقطوع:",
                  style: GoogleFonts.notoKufiArabic(color: Colors.white, fontSize: 16),
                ),
                Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.remove_circle, color: Colors.redAccent),
                      onPressed: () => setState(() => _actualCount = (_actualCount > 0) ? _actualCount - 1 : 0),
                    ),
                    SizedBox(
                      width: 60,
                      child: Text(
                        "$_actualCount",
                        textAlign: TextAlign.center,
                        style: GoogleFonts.orbitron(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.add_circle, color: Colors.greenAccent),
                      onPressed: () => setState(() => _actualCount++),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDropdown({required String label, required dynamic value, required List<DropdownMenuItem> items, required void Function(dynamic) onChanged}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: GoogleFonts.notoKufiArabic(color: Colors.white60, fontSize: 12)),
        DropdownButtonFormField(
          value: value,
          dropdownColor: AppTheme.obsidianBlack,
          items: items,
          onChanged: onChanged,
          style: GoogleFonts.notoKufiArabic(color: Colors.white),
          decoration: const InputDecoration(
            enabledBorder: UnderlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
          ),
        ),
      ],
    );
  }

  Widget _buildSubmitButton() {
    return SizedBox(
      width: double.infinity,
      height: 55,
      child: ElevatedButton(
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.greenAccent,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
        onPressed: () {
          // Submit Stock Adjustment Event (Axis 26)
        },
        child: Text(
          "اعتماد المطابقة والجرد",
          style: GoogleFonts.notoKufiArabic(color: Colors.black, fontWeight: FontWeight.bold),
        ),
      ),
    );
  }
}
