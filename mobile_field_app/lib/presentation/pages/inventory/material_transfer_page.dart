import 'package:flutter/material.dart';
import 'package:agriasset_field_app/core/theme/app_theme.dart';
import 'package:agriasset_field_app/presentation/widgets/shared/glass_card.dart';
import 'package:agriasset_field_app/presentation/widgets/shared/signature_pad.dart';
import 'package:agriasset_field_app/data/sources/local/offline_storage.dart';
import 'package:agriasset_field_app/data/models/material_transfer_model.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:google_fonts/google_fonts.dart';

class MaterialTransferPage extends StatefulWidget {
  const MaterialTransferPage({super.key});

  @override
  State<MaterialTransferPage> createState() => _MaterialTransferPageState();
}

class _MaterialTransferPageState extends State<MaterialTransferPage> {
  final _formKey = GlobalKey<FormState>();
  
  int? _selectedItemId;
  double _quantity = 0;
  int? _selectedReceiverId;
  bool _showSignaturePad = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: Text("صرف مواد (أمين المخزن)", style: GoogleFonts.notoKufiArabic(fontWeight: FontWeight.bold, fontSize: 18)),
      ),
      body: Directionality(
        textDirection: TextDirection.rtl,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (!_showSignaturePad) ...[
                _buildTransferForm(),
              ] else ...[
                _buildSignatureSection(),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTransferForm() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text("تفاصيل صرف العهدة", style: GoogleFonts.notoKufiArabic(fontWeight: FontWeight.bold, color: AppTheme.accentColor)),
          const SizedBox(height: 24),
          
          // Material Selector
          ValueListenableBuilder(
            valueListenable: Hive.box(OfflineStorage.cropsBox).listenable(), // Should be itemsBox in prod
            builder: (context, Box box, _) {
              return _buildDropdown(
                label: "المادة / الصنف",
                value: _selectedItemId,
                items: const [
                  DropdownMenuItem(value: 1, child: Text("يوريا (Urea)")),
                  DropdownMenuItem(value: 2, child: Text("سماد عضوي")),
                  DropdownMenuItem(value: 3, child: Text("مبيد حشري")),
                ],
                onChanged: (val) => setState(() => _selectedItemId = val as int?),
              );
            },
          ),
          
          const SizedBox(height: 20),

          TextFormField(
            keyboardType: TextInputType.number,
            style: const TextStyle(color: Colors.white),
            decoration: InputDecoration(
              labelText: "الكمية المصروفة",
              labelStyle: GoogleFonts.notoKufiArabic(fontSize: 12, color: Colors.white54),
              enabledBorder: const UnderlineInputBorder(borderSide: BorderSide(color: Colors.white24)),
            ),
            onChanged: (val) => _quantity = double.tryParse(val) ?? 0,
          ),

          const SizedBox(height: 20),

          _buildDropdown(
            label: "المستلم (المشرف الميداني)",
            value: _selectedReceiverId,
            items: const [
              DropdownMenuItem(value: 101, child: Text("المشرف / أحمد علي")),
              DropdownMenuItem(value: 102, child: Text("المشرف / محمد حسن")),
            ],
            onChanged: (val) => setState(() => _selectedReceiverId = val as int?),
          ),

          const SizedBox(height: 40),

          ElevatedButton(
            onPressed: () => setState(() => _showSignaturePad = true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.accentColor,
              foregroundColor: Colors.black,
              minimumSize: const Size(double.infinity, 56),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            child: Text("الانتقال للتوقيع والاعتماد", style: GoogleFonts.notoKufiArabic(fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _buildSignatureSection() {
    return Column(
      children: [
        SignaturePad(
          title: "توقيع المستلم (المشرف)",
          onSave: (signatureData) async {
            if (signatureData != null) {
              await _completeTransfer(signatureData);
            }
          },
        ),
        TextButton(
          onPressed: () => setState(() => _showSignaturePad = false),
          child: Text("العودة لتعديل البيانات", style: GoogleFonts.notoKufiArabic(color: Colors.white54)),
        ),
      ],
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

  Future<void> _completeTransfer(dynamic signatureData) async {
    // Save Transfer Record (Axis 21)
    final transfer = MaterialTransferModel(
      mobileRequestId: "MTR-${DateTime.now().millisecondsSinceEpoch}",
      farmId: 1, // Dynamic from User
      storekeeperId: 10, // Dynamic from User
      receiverId: _selectedReceiverId!,
      items: [
        TransferItem(itemId: _selectedItemId!, itemName: "Material", quantity: _quantity, uom: "KG"),
      ],
      // signature: signatureData, // Save blob to local storage or Hive
    );

    final box = Hive.box(OfflineStorage.transfersBox);
    await box.add(transfer.toJson());

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("تم اعتماد الصرف وتوقيع المستلم بنجاح"), backgroundColor: Colors.green),
      );
      Navigator.pop(context);
    }
  }
}
