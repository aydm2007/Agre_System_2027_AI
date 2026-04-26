import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:agriasset_field_app/presentation/blocs/auth_bloc.dart';
import 'package:agriasset_field_app/core/theme/app_theme.dart';
import 'package:agriasset_field_app/presentation/widgets/shared/glass_card.dart';
import 'package:google_fonts/google_fonts.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isPasswordVisible = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: Stack(
        children: [
          // Background Gradient Ornaments
          Positioned(
            top: -100,
            right: -100,
            child: Container(
              width: 300,
              height: 300,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppTheme.primaryColor.withOpacity(0.15),
              ),
            ).animate().scale(duration: 2.seconds, curve: Curves.easeOutBack),
          ),
          
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Sovereign Logo
                    Container(
                      height: 120,
                      width: 120,
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppTheme.surfaceColor,
                        border: Border.all(color: AppTheme.accentColor.withOpacity(0.3)),
                        boxShadow: [
                          BoxShadow(
                            color: AppTheme.accentColor.withOpacity(0.2),
                            blurRadius: 30,
                            spreadRadius: 5,
                          ),
                        ],
                      ),
                      child: Image.asset('assets/branding/logo.png'),
                    ).animate().fadeIn(duration: 800.ms).scale(delay: 200.ms),
                    
                    const SizedBox(height: 32),
                    
                    Text(
                      "AgriAsset OS",
                      style: GoogleFonts.outfit(
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                        letterSpacing: 1.2,
                      ),
                    ).animate().slideY(begin: 0.2, duration: 600.ms),
                    
                    Text(
                      "منصة السيادة الزراعية",
                      style: GoogleFonts.notoKufiArabic(
                        fontSize: 14,
                        color: Colors.white.withOpacity(0.6),
                      ),
                    ).animate().fadeIn(delay: 400.ms),

                    const SizedBox(height: 48),

                    // Login GlassCard
                    BlocConsumer<AuthBloc, AuthState>(
                      listener: (context, state) {
                        if (state is AuthFailure) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(state.message, style: GoogleFonts.notoKufiArabic()),
                              backgroundColor: Colors.redAccent,
                            ),
                          );
                        }
                      },
                      builder: (context, state) {
                        return GlassCard(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Text(
                                "تسجيل الدخول",
                                textAlign: TextAlign.right,
                                style: GoogleFonts.notoKufiArabic(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                              const SizedBox(height: 24),
                              
                              _buildTextField(
                                controller: _usernameController,
                                label: "اسم المستخدم",
                                icon: Icons.person_outline,
                              ),
                              
                              const SizedBox(height: 20),
                              
                              _buildTextField(
                                controller: _passwordController,
                                label: "كلمة المرور",
                                icon: Icons.lock_outline,
                                isPassword: true,
                              ),
                              
                              const SizedBox(height: 32),
                              
                              ElevatedButton(
                                onPressed: state is AuthLoading 
                                  ? null 
                                  : () {
                                      context.read<AuthBloc>().add(
                                        AuthLoggedIn(
                                          _usernameController.text, 
                                          _passwordController.text
                                        ),
                                      );
                                    },
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppTheme.primaryColor,
                                  foregroundColor: Colors.white,
                                  minimumSize: const Size(double.infinity, 56),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                                  elevation: 8,
                                  shadowColor: AppTheme.primaryColor.withOpacity(0.5),
                                ),
                                child: state is AuthLoading 
                                  ? const CircularProgressIndicator(color: Colors.white)
                                  : Text(
                                      "دخول آمن",
                                      style: GoogleFonts.notoKufiArabic(
                                        fontSize: 16,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                              ),
                            ],
                          ),
                        ).animate().fadeIn(delay: 500.ms).slideY(begin: 0.05);
                      },
                    ),
                    
                    const SizedBox(height: 40),
                    
                    Text(
                      "YECO Edition • v2.1.0",
                      style: GoogleFonts.outfit(
                        fontSize: 12,
                        color: Colors.white.withOpacity(0.3),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    bool isPassword = false,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: TextField(
        controller: controller,
        obscureText: isPassword && !_isPasswordVisible,
        textAlign: TextAlign.right,
        style: const TextStyle(color: Colors.white),
        decoration: InputDecoration(
          labelText: label,
          labelStyle: GoogleFonts.notoKufiArabic(color: Colors.white.withOpacity(0.5), fontSize: 13),
          prefixIcon: isPassword 
            ? IconButton(
                icon: Icon(
                  _isPasswordVisible ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                  color: Colors.white.withOpacity(0.3),
                ),
                onPressed: () => setState(() => _isPasswordVisible = !_isPasswordVisible),
              )
            : null,
          suffixIcon: Icon(icon, color: AppTheme.primaryColor.withOpacity(0.7)),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        ),
      ),
    );
  }
}
