import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const Color primaryColor = Color(0xFF1B5E20); // Deep Forest Green
  static const Color accentColor = Color(0xFFFFD700); // Golden Soil
  static const Color backgroundColor = Color(0xFF060906); // Ultra Deep Green-Black
  static const Color surfaceColor = Color(0xFF121712); // Deep Slate Green
  static const Color obsidianBlack = Color(0xFF0A0E0A); // Total Black for GRP
  static const Color forestGreen = Color(0xFF1B5E20); // Canonical Agri Green
  
  static List<BoxShadow> get luminousShadow => [
    BoxShadow(
      color: accentColor.withOpacity(0.15),
      blurRadius: 20,
      spreadRadius: 2,
      offset: const Offset(0, 10),
    ),
  ];

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      primaryColor: primaryColor,
      scaffoldBackgroundColor: backgroundColor,
      colorScheme: const ColorScheme.dark(
        primary: primaryColor,
        secondary: accentColor,
        surface: surfaceColor,
      ),
      textTheme: GoogleFonts.outfitTextTheme(ThemeData.dark().textTheme).copyWith(
        displayLarge: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: -1),
        titleLarge: const TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: Colors.white, letterSpacing: -0.5),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
      ),
      cardTheme: CardTheme(
        color: surfaceColor,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24), side: BorderSide(color: Colors.white.withOpacity(0.05))),
      ),
      // ... input decoration theme etc.
    );
  }
}
