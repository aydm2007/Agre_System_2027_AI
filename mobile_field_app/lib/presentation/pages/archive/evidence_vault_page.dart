import 'dart:io';
import 'package:flutter/material.dart';
import 'package:agriasset_field_app/presentation/widgets/shared/glass_card.dart';
import 'package:agriasset_field_app/core/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:agriasset_field_app/data/sources/local/offline_storage.dart';

class EvidenceVaultPage extends StatelessWidget {
  const EvidenceVaultPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.obsidianBlack,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          "خزنة الأدلة الميدانية",
          style: GoogleFonts.notoKufiArabic(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.cleaning_services, color: Colors.orangeAccent),
            tooltip: "تنظيف الأرشيف",
            onPressed: () {
              // Trigger 7-day purge logic
            },
          ),
        ],
      ),
      body: ValueListenableBuilder(
        valueListenable: Hive.box(OfflineStorage.transfersBox).listenable(), // Use a proxy for now or specific box
        builder: (context, Box box, _) {
          // In real impl, we'd fetch from evidence_vault box
          final evidenceList = box.values.toList(); 

          if (evidenceList.isEmpty) {
            return _buildEmptyState();
          }

          return GridView.builder(
            padding: const EdgeInsets.all(16),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: 0.8,
            ),
            itemCount: 10, // Mock for demo
            itemBuilder: (context, index) {
              return _buildEvidenceCard(context, index);
            },
          );
        },
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.photo_library_outlined, size: 64, color: Colors.white24),
          const SizedBox(height: 16),
          Text(
            "لا توجد أدلة محفوظة حالياً",
            style: GoogleFonts.notoKufiArabic(color: Colors.white38),
          ),
        ],
      ),
    );
  }

  Widget _buildEvidenceCard(BuildContext context, int index) {
    return GlassCard(
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.05),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
                image: const DecorationImage(
                  image: NetworkImage("https://via.placeholder.com/300x200"), // Mock
                  fit: BoxFit.cover,
                ),
              ),
              child: Stack(
                children: [
                   Positioned(
                    top: 8,
                    right: 8,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.black54,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        "S-SAFE",
                        style: GoogleFonts.orbitron(color: Colors.greenAccent, fontSize: 8),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "سجل إنجاز يومي",
                  style: GoogleFonts.notoKufiArabic(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                ),
                Text(
                  "2026/04/18 10:45",
                  style: GoogleFonts.notoKufiArabic(color: Colors.white38, fontSize: 8),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    const Icon(Icons.check_circle, color: Colors.greenAccent, size: 10),
                    const SizedBox(width: 4),
                    Text(
                      "تمت المزامنة",
                      style: GoogleFonts.notoKufiArabic(color: Colors.greenAccent, fontSize: 8),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    ).animate().fadeIn(delay: (index * 50).ms).scale();
  }
}
