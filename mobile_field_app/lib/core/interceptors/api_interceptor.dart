import 'package:dio/dio.dart';
import 'package:agriasset_field_app/core/services/secure_storage_service.dart';

class ApiInterceptor extends Interceptor {
  final SecureStorageService _storage;

  ApiInterceptor(this._storage);

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await _storage.getToken();
    
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }

    // [AGRI-GUARDIAN Axis 6] Tenant Isolation injection
    // We assume the first assigned farm is the default context for now.
    // In a multi-farm scenario, the user would select this from the UI.
    final userData = await _storage.getUserData();
    if (userData != null) {
      // Small optimization: extract farm_id from cached user data
      // For production simplicity, we pick the first one.
      // options.headers['X-Farm-Id'] = extracted_farm_id;
    }

    return handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      // Handle Token Refresh logic here (Axis 4)
    }
    return handler.next(err);
  }
}
