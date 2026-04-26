import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:agriasset_field_app/data/models/user_model.dart';
import 'package:agriasset_field_app/core/services/secure_storage_service.dart';

class AuthRepository {
  final Dio _dio;
  final SecureStorageService _storage;
  
  static const String baseUrl = "http://195.94.24.180:8000/api";

  AuthRepository(this._dio, this._storage);

  Future<UserModel?> login(String username, String password) async {
    try {
      final response = await _dio.post(
        "$baseUrl/auth/token/",
        data: {
          "username": username,
          "password": password,
        },
      );

      if (response.statusCode == 200) {
        final accessToken = response.data['access'];
        final refreshToken = response.data['refresh'];

        await _storage.saveToken(accessToken);
        await _storage.saveRefreshToken(refreshToken);

        // Fetch Full Profile including Roles & Permissions (RBAC Enforcement)
        return await fetchProfile(accessToken);
      }
    } catch (e) {
      // Log for forensics
      rethrow;
    }
    return null;
  }

  Future<UserModel?> fetchProfile(String token) async {
    try {
      final response = await _dio.get(
        "$baseUrl/v1/auth/users/me/",
        options: Options(
          headers: {'Authorization': 'Bearer $token'},
        ),
      );

      if (response.statusCode == 200) {
        // [AGRI-GUARDIAN Axis 4] Mapping backend roles to mobile RBAC
        final user = UserModel.fromJson({
          'id': response.data['user']['id'],
          'username': response.data['user']['username'],
          'full_name': response.data['user']['first_name'] + " " + response.data['user']['last_name'],
          'role': _mapRole(response.data['farms']), 
          'assigned_farm_ids': response.data['farm_ids'],
          'permissions': { for (var p in response.data['permissions']) p : true },
        });

        await _storage.saveUserData(jsonEncode(user.toJson()));
        return user;
      }
    } catch (e) {
      rethrow;
    }
    return null;
  }

  String _mapRole(List farms) {
    if (farms.isEmpty) return 'USER';
    // Priority role mapping: Manager > Finance > Supervisor
    final roles = farms.map((f) => f['role'].toString()).toList();
    if (roles.contains('مدير المزرعة')) return 'MANAGER';
    if (roles.contains('المدير المالي للمزرعة')) return 'FINANCE';
    if (roles.contains('مشرف ميداني')) return 'SUPERVISOR';
    if (roles.contains('أمين المخزن')) return 'STOREKEEPER';
    return 'USER';
  }

  Future<void> logout() async {
    await _storage.deleteAll();
  }
}
