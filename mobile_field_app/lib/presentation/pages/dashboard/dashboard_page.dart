import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:agriasset_field_app/core/theme/app_theme.dart';
import 'package:agriasset_field_app/presentation/widgets/shared/glass_card.dart';
import 'package:agriasset_field_app/presentation/blocs/auth_bloc.dart';
import 'package:agriasset_field_app/data/models/user_model.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:fl_chart/fl_chart.dart';

import 'package:hive_flutter/hive_flutter.dart';
import 'package:agriasset_field_app/data/sources/local/offline_storage.dart';
import 'package:agriasset_field_app/presentation/pages/daily_log/daily_log_create_page.dart';
import 'package:agriasset_field_app/presentation/pages/inventory/material_transfer_page.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final isDesktop = size.width > 900;

    return BlocBuilder<AuthBloc, AuthState>(
      builder: (context, state) {
        final user = (state is AuthAuthenticated) ? state.user : null;
        
        return Scaffold(
          extendBodyBehindAppBar: true,
          appBar: AppBar(
            title: Text("AgriAsset OS", 
              style: GoogleFonts.outfit(fontWeight: FontWeight.w800, letterSpacing: -1, fontSize: 24)),
            actions: [
              _buildPulseSyncButton(),
              IconButton(
                onPressed: () => context.read<AuthBloc>().add(AuthLoggedOut()),
                icon: const Icon(Icons.logout_rounded, color: Colors.white70),
              ),
            ],
          ),
          body: Stack(
            children: [
              _buildAtmosphericBackground(),
              Directionality(
                textDirection: TextDirection.rtl,
                child: SafeArea(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildUnifiedHeader(user),
                        const SizedBox(height: 32),
                        if (isDesktop) _buildDesktopLayout(user) else _buildMobileLayout(user),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildAtmosphericBackground() {
    return Container(
      decoration: const BoxDecoration(
        gradient: RadialGradient(
          center: Alignment(-0.8, -0.6),
          radius: 1.5,
          colors: [
            Color(0xFF133213),
            AppTheme.backgroundColor,
          ],
        ),
      ),
    );
  }

  Widget _buildPulseSyncButton() {
    return Container(
      margin: const EdgeInsets.only(left: 8),
      child: IconButton(
        onPressed: () {},
        icon: const Icon(Icons.sync_rounded, color: AppTheme.accentColor),
      ),
    ).animate(onPlay: (controller) => controller.repeat())
     .shimmer(duration: 2.seconds, color: Colors.white24);
  }

  Widget _buildUnifiedHeader(UserModel? user) {
    return ValueListenableBuilder<Box>(
      valueListenable: Hive.box(OfflineStorage.dailyLogsBox).listenable(),
      builder: (context, box, _) {
        final pendingCount = box.length;
        final isHealthy = pendingCount == 0;
        
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("مرحباً بك، ${user?.fullName ?? '...'} 👋", 
              style: GoogleFonts.notoKufiArabic(fontSize: 24, fontWeight: FontWeight.w900, color: Colors.white)),
            const SizedBox(height: 4),
            Row(
              children: [
                Container(
                  width: 8, height: 8,
                  decoration: BoxDecoration(
                    color: isHealthy ? Colors.greenAccent : Colors.orangeAccent, 
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: (isHealthy ? Colors.greenAccent : Colors.orangeAccent).withOpacity(0.5),
                        blurRadius: 8,
                        spreadRadius: 2,
                      )
                    ]
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  _getRoleDisplay(user?.role) + (isHealthy ? " • متصل" : " • جاري المزامنة ($pendingCount)"), 
                  style: GoogleFonts.notoKufiArabic(fontSize: 13, color: Colors.white54, fontWeight: FontWeight.normal),
                ),
              ],
            ),
          ],
        );
      },
    ).animate().fadeIn(duration: 600.ms).slideY(begin: 0.2);
  }

  String _getRoleDisplay(String? role) {
    switch (role) {
      case 'MANAGER': return 'مدير المزرعة';
      case 'FINANCE': return 'المدير المالي';
      case 'SUPERVISOR': return 'مشرف ميداني';
      case 'STOREKEEPER': return 'أمين المخزن';
      default: return 'مستخدم';
    }
  }

  Widget _buildMobileLayout(UserModel? user) {
    return Column(
      children: [
        _buildAnalyticsPanel(user),
        const SizedBox(height: 24),
        _buildStatGrid(user, crossAxisCount: 2),
        const SizedBox(height: 32),
        _buildActionHub(user),
      ],
    );
  }

  Widget _buildDesktopLayout(UserModel? user) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(flex: 2, child: _buildAnalyticsPanel(user)),
        const SizedBox(width: 32),
        Expanded(
          flex: 1,
          child: Column(
            children: [
              _buildStatGrid(user, crossAxisCount: 1),
              const SizedBox(height: 32),
              _buildActionHub(user),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildAnalyticsPanel(UserModel? user) {
    final showChart = user?.role != 'STOREKEEPER';
    if (!showChart) return const SizedBox.shrink();

    return GlassCard(
      height: 300,
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("معدلات الإنتاج الميداني", style: GoogleFonts.notoKufiArabic(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 24),
          Expanded(child: _buildSimpleLineChart()),
        ],
      ),
    ).animate().fadeIn(delay: 200.ms);
  }

  Widget _buildSimpleLineChart() {
    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: const [FlSpot(0, 3), FlSpot(1, 1), FlSpot(2, 4), FlSpot(3, 3), FlSpot(4, 5)],
            isCurved: true,
            color: AppTheme.accentColor,
            barWidth: 4,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: AppTheme.accentColor.withOpacity(0.1),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatGrid(UserModel? user, {required int crossAxisCount}) {
    return GridView.count(
      crossAxisCount: crossAxisCount,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 16,
      crossAxisSpacing: 16,
      childAspectRatio: 1.3,
      children: [
        _buildSyncHealthCard(),
        if (user?.role == 'MANAGER' || user?.role == 'FINANCE')
          _buildGlassStat("الحرق", "١٢٪ أسبوعي", Icons.local_fire_department_outlined, Colors.orange),
        if (user?.role != 'STOREKEEPER')
          _buildGlassStat("المحصول", "٩٢٪ صحي", Icons.eco_outlined, Colors.greenAccent),
        if (user?.role == 'STOREKEEPER')
          _buildGlassStat("المخزون", "٤٥ صنف", Icons.inventory_2_outlined, Colors.cyan),
        _buildGlassStat("الري", "٨ ساعات", Icons.water_drop_outlined, Colors.blueAccent),
      ],
    ).animate().fadeIn(delay: 400.ms).slideY(begin: 0.1);
  }

  Widget _buildSyncHealthCard() {
    return ListenableBuilder(
      listenable: Listenable.merge([
        Hive.box(OfflineStorage.dailyLogsBox).listenable(),
        Hive.box(OfflineStorage.transfersBox).listenable(),
      ]),
      builder: (context, _) {
        final logsCount = Hive.box(OfflineStorage.dailyLogsBox).length;
        final transfersCount = Hive.box(OfflineStorage.transfersBox).length;
        final pendingCount = logsCount + transfersCount;
        final isHealthy = pendingCount == 0;
        
        return GlassCard(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                isHealthy ? Icons.cloud_done_rounded : Icons.cloud_sync_rounded, 
                color: isHealthy ? Colors.greenAccent : Colors.orangeAccent, 
                size: 28,
              ),
              const SizedBox(height: 8),
              Text(
                isHealthy ? "مؤمن" : "$pendingCount معلق", 
                style: GoogleFonts.outfit(fontSize: 18, fontWeight: FontWeight.w800),
              ),
              Text("صحة المزامنة", style: GoogleFonts.notoKufiArabic(fontSize: 11, color: Colors.white54)),
            ],
          ),
        );
      },
    );
  }

  Widget _buildGlassStat(String title, String value, IconData icon, Color color) {
    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: 8),
          Text(value, style: GoogleFonts.outfit(fontSize: 18, fontWeight: FontWeight.w800)),
          Text(title, style: GoogleFonts.notoKufiArabic(fontSize: 11, color: Colors.white54)),
        ],
      ),
    );
  }

  Widget _buildActionHub(UserModel? user) {
    return Column(
      children: [
        if (user?.role == 'SUPERVISOR' || user?.role == 'MANAGER')
          _buildPremiumAction(
            "إضافة سجل يومي", 
            "توثيق المهام الميدانية والعمالة", 
            Icons.add_circle_outline_rounded,
            AppTheme.accentColor,
            onTap: () => Navigator.push(
              context, 
              MaterialPageRoute(builder: (context) => const DailyLogCreatePage())
            ),
          ),
        if (user?.role == 'STOREKEEPER')
          _buildPremiumAction(
            "صرف مواد", 
            "تسليم بذور/أسمدة للمشرفين", 
            Icons.outbox_rounded,
            Colors.orangeAccent,
            onTap: () => Navigator.push(
              context, 
              MaterialPageRoute(builder: (context) => const MaterialTransferPage())
            ),
          ),
        if (user?.role == 'MANAGER' || user?.role == 'FINANCE')
          _buildPremiumAction(
            "الاعتمادات المالية", 
            "مراجعة السجلات وتوقيع الصرف", 
            Icons.verified_user_rounded,
            Colors.greenAccent,
            onTap: () {},
          ),
        const SizedBox(height: 16),
        _buildPremiumAction(
          "الخرائط والتقارير", 
          "عرض الخرائط التفاعلية GIS", 
          Icons.map_outlined,
          Colors.white70,
          onTap: () {},
        ),
      ],
    ).animate().fadeIn(delay: 600.ms).slideY(begin: 0.1);
  }

  Widget _buildPremiumAction(String title, String subtitle, IconData icon, Color color, {required VoidCallback onTap}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(24),
        child: GlassCard(
          color: AppTheme.primaryColor.withOpacity(0.3),
          child: Row(
            children: [
              Icon(icon, size: 36, color: color),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: GoogleFonts.notoKufiArabic(fontSize: 16, fontWeight: FontWeight.bold)),
                    Text(subtitle, style: GoogleFonts.notoKufiArabic(fontSize: 12, color: Colors.white38)),
                  ],
                ),
              ),
              const Icon(Icons.arrow_back_ios_new_rounded, size: 16, color: Colors.white24),
            ],
          ),
        ),
      ),
    );
  }
}
