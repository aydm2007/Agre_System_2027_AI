import 'package:dio/dio.dart';
import 'package:agriasset_field_app/data/models/master_data_models.dart';
import 'package:agriasset_field_app/data/models/farm_settings_model.dart';
import 'package:agriasset_field_app/data/sources/local/offline_storage.dart';
import 'package:hive/hive.dart';

class MasterDataRepository {
  final Dio _dio;
  static const String baseUrl = "http://195.94.24.180:8000/api/v1";

  MasterDataRepository(this._dio);

  Future<void> fetchAndCacheAll(int farmId) async {
    await Future.wait([
      fetchCrops(farmId),
      fetchItems(farmId),
      fetchFarmSettings(farmId),
    ]);
  }

  Future<List<CropPlanModel>> fetchCrops(int farmId) async {
    try {
      final DateTime? lastSync = OfflineStorage.getLastSync(OfflineStorage.cropsBox);
      final Map<String, dynamic> params = {'farm': farmId};
      if (lastSync != null) {
        params['updated_at__gt'] = lastSync.toIso8601String();
      }

      final response = await _dio.get("$baseUrl/crop-plans/", queryParameters: params);
      final List data = response.data['results'] ?? response.data;
      final crops = data.map((json) => CropPlanModel.fromJson(json)).toList();
      
      // Cache locally (Axis 11) - Use .put() to overwrite/add without clearing
      final box = Hive.box(OfflineStorage.cropsBox);
      for (var crop in crops) {
        await box.put(crop.id, crop.toJson());
      }
      
      await OfflineStorage.setLastSync(OfflineStorage.cropsBox, DateTime.now());
      return crops;
    } catch (e) {
      return [];
    }
  }

  Future<List<ItemModel>> fetchItems(int farmId) async {
    try {
      final DateTime? lastSync = OfflineStorage.getLastSync(OfflineStorage.itemsBox);
      final Map<String, dynamic> params = {'farm': farmId};
      if (lastSync != null) {
        params['updated_at__gt'] = lastSync.toIso8601String();
      }

      final response = await _dio.get("$baseUrl/items/", queryParameters: params);
      final List data = response.data['results'] ?? response.data;
      final items = data.map((json) => ItemModel.fromJson(json)).toList();
      
      final box = Hive.box(OfflineStorage.itemsBox);
      for (var item in items) {
        await box.put(item.id, item.toJson());
      }
      
      await OfflineStorage.setLastSync(OfflineStorage.itemsBox, DateTime.now());
      return items;
    } catch (e) {
      return [];
    }
  }

  Future<FarmSettingsModel?> fetchFarmSettings(int farmId) async {
    try {
      final response = await _dio.get("$baseUrl/farm-settings/", queryParameters: {'farm': farmId});
      final List data = response.data['results'] ?? response.data;
      if (data.isNotEmpty) {
        final settings = FarmSettingsModel.fromJson(data.first);
        final box = await Hive.openBox('farm_settings');
        await box.put(farmId, settings.toJson());
        return settings;
      }
    } catch (e) {
      return null;
    }
    return null;
  }
}
