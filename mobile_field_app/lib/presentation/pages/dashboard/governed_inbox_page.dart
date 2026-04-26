import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:agriasset_field_app/presentation/blocs/auth_bloc.dart';
import 'package:agriasset_field_app/presentation/widgets/shared/glass_card.dart';
import 'package:agriasset_field_app/core/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:agriasset_field_app/presentation/pages/daily_log/daily_log_create_page.dart';
import 'package:agriasset_field_app/presentation/pages/inventory/stock_reconciliation_page.dart';
import 'package:agriasset_field_app/presentation/pages/archive/evidence_vault_page.dart';
import 'package:agriasset_field_app/presentation/pages/inventory/storekeeper_stock_page.dart';

class GovernedInboxPage extends StatefulWidget {
  const GovernedInboxPage({super.key});

  @override
  State<GovernedInboxPage> createState() => _GovernedInboxPageState();
}

class _GovernedInboxPageState extends State<GovernedInboxPage> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  Widget build(BuildContext context) {
    final authState = context.read<AuthBloc>().state;
    final user = (authState is AuthAuthenticated) ? authState.user : null;

    return Scaffold(
      backgroundColor: AppTheme.obsidianBlack,
      drawer: Drawer(
        backgroundColor: AppTheme.obsidianBlack,
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: BoxDecoration(color: Colors.white.withOpacity(0.05)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.admin_panel_settings, color: Colors.greenAccent, size: 40),
                  const SizedBox(height: 12),
                  Text("AgriAsset OS", style: GoogleFonts.orbitron(color: Colors.white, fontWeight: FontWeight.bold)),
                  Text("أدوات الحوكمة السيادية", style: GoogleFonts.notoKufiArabic(color: Colors.white60, fontSize: 10)),
                ],
              ),
            ),
            ListTile(
              leading: const Icon(Icons.inventory_2_outlined, color: Colors.blueAccent),
              title: Text("رصيد المخزن (أمين المخزن)", style: GoogleFonts.notoKufiArabic(color: Colors.white70, fontSize: 12)),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(context, MaterialPageRoute(builder: (context) => const StorekeeperStockPage()));
              },
            ),
             ListTile(
              leading: const Icon(Icons.photo_library_outlined, color: Colors.orangeAccent),
              title: Text("خزنة الأدلة والجرد", style: GoogleFonts.notoKufiArabic(color: Colors.white70, fontSize: 12)),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(context, MaterialPageRoute(builder: (context) => const EvidenceVaultPage()));
              },
            ),
          ],
        ),
      ),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          "صندوق المهام السيادي",
          style: GoogleFonts.notoKufiArabic(
            color: Colors.white,
            fontWeight: FontWeight.bold,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.location_on, color: Colors.blueAccent),
            tooltip: "مطابقة الأرصدة",
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const StockReconciliationPage()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.photo_library_outlined, color: Colors.orangeAccent),
            tooltip: "خزنة الأدلة",
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const EvidenceVaultPage()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.redAccent),
            onPressed: () => context.read<AuthBloc>().add(AuthLoggedOut()),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.greenAccent,
          labelStyle: GoogleFonts.notoKufiArabic(fontSize: 12),
          tabs: const [
            Tab(text: "بانتظار الاعتماد", icon: Icon(Icons.pending_actions)),
            Tab(text: "تحتاج مراجعة", icon: Icon(Icons.assignment_return)),
            Tab(text: "مسودات ميدانية", icon: Icon(Icons.edit_document)),
          ],
        ),
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              AppTheme.obsidianBlack,
              AppTheme.forestGreen.withOpacity(0.1),
            ],
          ),
        ),
        child: TabBarView(
          controller: _tabController,
          children: [
            _buildInboxLane("قائمة السجلات بانتظار توقيعك", Icons.security, Colors.orangeAccent),
            _buildInboxLane("سجلات تمت إعادتها من المحاسبة", Icons.warning_amber, Colors.redAccent),
            _buildInboxLane("سجلات محفوظة محلياً (Offline)", Icons.cloud_off, Colors.blueAccent),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: Colors.greenAccent,
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => const DailyLogCreatePage()),
          );
        },
        label: Text(
          "سجل جديد",
          style: GoogleFonts.notoKufiArabic(color: Colors.black, fontWeight: FontWeight.bold),
        ),
        icon: const Icon(Icons.add, color: Colors.black),
      ),
    );
  }

  Widget _buildManagerKpiCard() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: GlassCard(
        color: Colors.white.withOpacity(0.05),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildKpiItem("معدل الإنجاز", "85%", Icons.trending_up, Colors.greenAccent),
                _buildKpiItem("تكلفة الوحدة", "1.2k", Icons.payments_outlined, Colors.orangeAccent),
                _buildKpiItem("العمال النشطين", "12", Icons.groups_outlined, Colors.blueAccent),
              ],
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(2),
              child: LinearProgressIndicator(
                value: 0.85,
                backgroundColor: Colors.white10,
                color: Colors.greenAccent,
                minHeight: 4,
              ),
            ),
          ],
        ),
      ),
    ).animate().fadeIn().slideY();
  }

  Widget _buildKpiItem(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 20),
        const SizedBox(height: 4),
        Text(value, style: GoogleFonts.orbitron(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
        Text(label, style: GoogleFonts.notoKufiArabic(color: Colors.white38, fontSize: 8)),
      ],
    );
  }

  Widget _buildInboxLane(String title, IconData icon, Color accentColor) {
    return Column(
      children: [
        if (title.contains("قائمة السجلات")) _buildManagerKpiCard(), // Integrated KPIs
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            itemCount: 5,
            itemBuilder: (context, index) {
              return GlassCard(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: accentColor.withOpacity(0.2),
                    child: Icon(icon, color: accentColor, size: 20),
                  ),
                  title: Text(
                    "سجل يومية - مزرعة البركة",
                    style: GoogleFonts.notoKufiArabic(color: Colors.white, fontSize: 14),
                  ),
                  subtitle: Text(
                    "بتاريخ: 2026/04/18 - مشرف: عبده",
                    style: GoogleFonts.notoKufiArabic(color: Colors.white60, fontSize: 11),
                  ),
                  trailing: const Icon(Icons.chevron_right, color: Colors.white24),
                  onTap: () {
                    // Open record details with ApprovalTimelineWidget
                  },
                ),
              ).animate().fadeIn(delay: (index * 100).ms).slideX();
            },
          ),
        ),
      ],
    );
  }
}
