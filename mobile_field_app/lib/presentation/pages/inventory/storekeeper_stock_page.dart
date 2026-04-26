import 'package:flutter/material.dart';
import 'package:agriasset_field_app/presentation/widgets/shared/glass_card.dart';
import 'package:agriasset_field_app/core/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:agriasset_field_app/data/sources/local/offline_storage.dart';

class StorekeeperStockPage extends StatelessWidget {
  const StorekeeperStockPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.obsidianBlack,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          "رصيد عهدة المخزن",
          style: GoogleFonts.notoKufiArabic(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.sync, color: Colors.greenAccent),
            onPressed: () {
              // Trigger Master Data Sync for items
            },
          ),
        ],
      ),
      body: ValueListenableBuilder(
        valueListenable: Hive.box(OfflineStorage.itemsBox).listenable(),
        builder: (context, Box box, _) {
          final items = box.values.toList();

          if (items.isEmpty) {
            return _buildEmptyState();
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];
              return _buildStockItem(context, item);
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
          const Icon(Icons.inventory_2_outlined, size: 64, color: Colors.white24),
          const SizedBox(height: 16),
          Text(
            "لا توجد بيانات أصناف متاحة حالياً",
            style: GoogleFonts.notoKufiArabic(color: Colors.white38),
          ),
        ],
      ),
    );
  }

  Widget _buildStockItem(BuildContext context, dynamic item) {
    // Mock stock level logic (In real impl, we'd have a local_balance field)
    final double stockLevel = (item['id'] % 3 == 0) ? 5.0 : 45.0; 
    final Color levelColor = stockLevel < 10 ? Colors.redAccent : Colors.greenAccent;
    final String statusLabel = stockLevel < 10 ? "مخزون منخفض" : "متوفر";

    return GlassCard(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: levelColor.withOpacity(0.1),
          child: Icon(Icons.category, color: levelColor, size: 20),
        ),
        title: Text(
          item['name'] ?? "صنف غير معروف",
          style: GoogleFonts.notoKufiArabic(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
        ),
        subtitle: Text(
          "الوحدة: ${item['unit_name'] ?? 'كجم'} | الفئة: ${item['category_name'] ?? 'أسمدة'}",
          style: GoogleFonts.notoKufiArabic(color: Colors.white60, fontSize: 11),
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              "$stockLevel",
              style: GoogleFonts.orbitron(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
            ),
            Text(
              statusLabel,
              style: GoogleFonts.notoKufiArabic(color: levelColor, fontSize: 9),
            ),
          ],
        ),
      ),
    ).animate().fadeIn(delay: 100.ms).slideX();
  }
}
