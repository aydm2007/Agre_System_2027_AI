import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:dio/dio.dart';
import 'package:agriasset_field_app/core/theme/app_theme.dart';
import 'package:agriasset_field_app/core/services/secure_storage_service.dart';
import 'package:agriasset_field_app/data/repositories/auth_repository.dart';
import 'package:agriasset_field_app/presentation/blocs/auth_bloc.dart';
import 'package:agriasset_field_app/presentation/pages/dashboard/governed_inbox_page.dart';
import 'package:agriasset_field_app/presentation/pages/auth/login_page.dart';
import 'package:agriasset_field_app/data/sources/local/offline_storage.dart';

import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:window_manager/window_manager.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Sovereign Desktop Orchestration (Axis 21)
  if (!kIsWeb && Platform.isWindows) {
    await windowManager.ensureInitialized();
    WindowOptions windowOptions = const WindowOptions(
      size: Size(1280, 800),
      center: true,
      backgroundColor: Colors.transparent,
      skipTaskbar: false,
      titleBarStyle: TitleBarStyle.normal,
      title: 'AgriAsset Sovereign Field Command',
    );
    windowManager.waitUntilReadyToShow(windowOptions, () async {
      await windowManager.show();
      await windowManager.focus();
    });
  }

  // Initialize Offline Storage (Axis 11/17)
  await OfflineStorage.init();

  final storage = SecureStorageService();
  final dio = Dio();
  final authRepository = AuthRepository(dio, storage);
  
  runApp(
    MultiRepositoryProvider(
      providers: [
        RepositoryProvider.value(value: authRepository),
        RepositoryProvider.value(value: storage),
      ],
      child: BlocProvider(
        create: (context) => AuthBloc(authRepository)..add(AuthAppStarted()),
        child: const AgriAssetFieldApp(),
      ),
    ),
  );
}

class AgriAssetFieldApp extends StatelessWidget {
  const AgriAssetFieldApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AgriAsset Field',
      debugShowCheckedModeBanner: false,
      
      // Premium Design System
      theme: AppTheme.darkTheme,
      
      // RTL & Arabic Support (Northern Yemen Standard)
      locale: const Locale('ar', 'YE'),
      supportedLocales: const [
        Locale('ar', 'YE'),
        Locale('en', 'US'),
      ],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      
      home: BlocBuilder<AuthBloc, AuthState>(
        builder: (context, state) {
          if (state is AuthAuthenticated) {
            return const GovernedInboxPage();
          }
          if (state is AuthLoading) {
            return const Scaffold(
              backgroundColor: AppTheme.backgroundColor,
              body: Center(child: CircularProgressIndicator(color: AppTheme.primaryColor)),
            );
          }
          return const LoginPage();
        },
      ),
    );
  }
}
