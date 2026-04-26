import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:agriasset_field_app/data/models/user_model.dart';
import 'package:agriasset_field_app/data/repositories/auth_repository.dart';

// --- Events ---
abstract class AuthEvent {}
class AuthAppStarted extends AuthEvent {}
class AuthLoggedIn extends AuthEvent {
  final String username;
  final String password;
  AuthLoggedIn(this.username, this.password);
}
class AuthLoggedOut extends AuthEvent {}

// --- States ---
abstract class AuthState {}
class AuthInitial extends AuthState {}
class AuthLoading extends AuthState {}
class AuthAuthenticated extends AuthState {
  final UserModel user;
  AuthAuthenticated(this.user);
}
class AuthUnauthenticated extends AuthState {}
class AuthFailure extends AuthState {
  final String message;
  AuthFailure(this.message);
}

// --- Bloc ---
class AuthBloc extends Bloc<AuthEvent, AuthState> {
  final AuthRepository _authRepository;

  AuthBloc(this._authRepository) : super(AuthInitial()) {
    on<AuthAppStarted>(_onAppStarted);
    on<AuthLoggedIn>(_onLoggedIn);
    on<AuthLoggedOut>(_onLoggedOut);
  }

  Future<void> _onAppStarted(AuthAppStarted event, Emitter<AuthState> emit) async {
    try {
      // Check if we have a stored session
      // (Simplified logic: repo will handle profile fetch if token exists)
      // For now, assume Unauthenticated until explicit login
      emit(AuthUnauthenticated());
    } catch (e) {
      emit(AuthFailure(e.toString()));
    }
  }

  Future<void> _onLoggedIn(AuthLoggedIn event, Emitter<AuthState> emit) async {
    emit(AuthLoading());
    try {
      final user = await _authRepository.login(event.username, event.password);
      if (user != null) {
        emit(AuthAuthenticated(user));
      } else {
        emit(AuthFailure("فشل تسجيل الدخول. يرجى التحقق من البيانات."));
      }
    } catch (e) {
      emit(AuthFailure("حدث كخطأ أثناء الاتصال بالسيرفر."));
    }
  }

  Future<void> _onLoggedOut(AuthLoggedOut event, Emitter<AuthState> emit) async {
    await _authRepository.logout();
    emit(AuthUnauthenticated());
  }
}
