import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:signature/signature.dart';
import 'package:agriasset_field_app/core/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';

class SignaturePad extends StatefulWidget {
  final Function(Uint8List?) onSave;
  final String title;

  const SignaturePad({super.key, required this.onSave, required this.title});

  @override
  State<SignaturePad> createState() => _SignaturePadState();
}

class _SignaturePadState extends State<SignaturePad> {
  final SignatureController _controller = SignatureController(
    penStrokeWidth: 4,
    penColor: AppTheme.accentColor,
    exportBackgroundColor: Colors.transparent,
  );

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 20.0),
          child: Text(
            widget.title,
            style: GoogleFonts.outfit(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
          ),
        ),
        Container(
          margin: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(
            border: Border.all(color: AppTheme.accentColor.withOpacity(0.5), width: 2),
            borderRadius: BorderRadius.circular(24),
            color: AppTheme.surfaceColor.withOpacity(0.8),
            boxShadow: [
              BoxShadow(color: AppTheme.accentColor.withOpacity(0.1), blurRadius: 20, spreadRadius: 5),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: Signature(
              controller: _controller,
              height: 250,
              backgroundColor: Colors.transparent,
            ),
          ),
        ),
        const SizedBox(height: 20),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            TextButton.icon(
              onPressed: () => _controller.clear(),
              icon: const Icon(Icons.refresh, color: Colors.white70),
              label: const Text("مسح", style: TextStyle(color: Colors.white70)),
            ),
            ElevatedButton.icon(
              onPressed: () async {
                if (_controller.isNotEmpty) {
                  final Uint8List? data = await _controller.toPngBytes();
                  widget.onSave(data);
                }
              },
              icon: const Icon(Icons.verified_user),
              label: const Text("اعتماد التوقيع"),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryColor,
                foregroundColor: Colors.white,
                minimumSize: const Size(200, 56),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
