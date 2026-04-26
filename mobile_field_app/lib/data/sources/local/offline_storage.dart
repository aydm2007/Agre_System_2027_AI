import 'package:hive_flutter/hive_flutter.dart';

class OfflineStorage {
  static const String dailyLogsBox = 'daily_logs';
  static const String cropsBox = 'master_crops';
  static const String itemsBox = 'master_items';
  static const String settingsBox = 'farm_settings';
  static const String transfersBox = 'material_transfers';
  static const String syncMetadataBox = 'sync_metadata';

  static Future<void> init() async {
    await Hive.initFlutter();
    // Register adapters here after building them
    // Hive.registerAdapter(DailyLogModelAdapter());
    
    await Hive.openBox(dailyLogsBox);
    await Hive.openBox(cropsBox);
    await Hive.openBox(itemsBox);
    await Hive.openBox(settingsBox);
    await Hive.openBox(transfersBox);
    await Hive.openBox(syncMetadataBox);
  }

  static Future<void> saveLog(Map<String, dynamic> logData) async {
    final box = Hive.box(dailyLogsBox);
    await box.add(logData);
  }

  /// Returns a Map where the key is the Hive index and the value is the log data.
  /// This allows the repository to delete a specific log after a successful sync.
  static Map<int, Map<String, dynamic>> getPendingLogs() {
    final box = Hive.box(dailyLogsBox);
    final Map<int, Map<String, dynamic>> result = {};
    
    try {
      for (var i = 0; i < box.length; i++) {
        final dynamic key = box.keyAt(i);
        final dynamic value = box.get(key);
        
        // Defensive check: ensure value is a valid Map
        if (value != null && value is Map) {
          try {
            result[key as int] = Map<String, dynamic>.from(value);
          } catch (castError) {
            // Log/Skip individual corrupted entries rather than failing the whole set
            continue;
          }
        }
      }
    } catch (criticalError) {
      // Emergency fallback: return empty result if box enumeration fails
      return {};
    }
    return result;
  }

  static int getPendingCount() {
    return Hive.box(dailyLogsBox).length;
  }

  static Future<void> deleteLog(int index) async {
    final box = Hive.box(dailyLogsBox);
    await box.delete(index);
  }

  static Future<void> clearLogs() async {
    await Hive.box(dailyLogsBox).clear();
  }

  /// Sets the last sync timestamp for a specific master data type.
  static Future<void> setLastSync(String type, DateTime timestamp) async {
    final box = Hive.box(syncMetadataBox);
    await box.put(type, timestamp.toIso8601String());
  }

  /// Gets the last sync timestamp for a specific master data type.
  static DateTime? getLastSync(String type) {
    final box = Hive.box(syncMetadataBox);
    final String? timestamp = box.get(type);
    if (timestamp == null) return null;
    return DateTime.tryParse(timestamp);
  }
}
