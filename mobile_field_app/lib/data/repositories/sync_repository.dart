import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:agriasset_field_app/data/sources/local/offline_storage.dart';
import 'package:hive/hive.dart';

class SyncRepository {
  final Dio _dio;
  static const String baseUrl = "http://195.94.24.180:8000/api/v1";

  SyncRepository(this._dio);

  /// Unified Sync Entry Point
  Future<void> syncAll() async {
    await syncPendingLogs();
    await syncPendingTransfers();
  }

  /// [AGRI-GUARDIAN Axis 20] Sequential Replay for Daily Logs
  Future<void> syncPendingLogs() async {
    final box = Hive.box(OfflineStorage.dailyLogsBox);
    final sortedKeys = box.keys.toList()..sort();

    for (var key in sortedKeys) {
      final log = box.get(key);
      final requestId = log['mobile_request_id'];

      try {
        final response = await _dio.post(
          "$baseUrl/core/offline-daily-log-replay/",
          data: {
            "idempotency_key": requestId,
            "uuid": requestId,
            "log": log,
          },
          options: Options(headers: {'X-Idempotency-Key': requestId}),
        );

        if (response.statusCode == 201 || response.statusCode == 200) {
          await box.delete(key);
        }
      } catch (e) {
        continue; // Fail-safe: keep locally on error
      }
    }
  }

  /// [AGRI-GUARDIAN Axis 22] Sync Material Transfers with Signatures
  Future<void> syncPendingTransfers() async {
    final box = Hive.box(OfflineStorage.transfersBox);
    final sortedKeys = box.keys.toList()..sort();

    for (var key in sortedKeys) {
      final transfer = box.get(key);
      final requestId = transfer['mobile_request_id'];

      try {
        // [SOVEREIGN HANDSHAKE] Signature persistence
        // Signatures are stored as Uint8List in the model, converted to Base64 for sync
        final response = await _dio.post(
          "$baseUrl/inventory/material-transfer-replay/",
          data: {
            "idempotency_key": requestId,
            "uuid": requestId,
            "transfer": transfer,
            // "signature_b64": transfer['signature'] != null ? base64Encode(transfer['signature']) : null,
          },
          options: Options(headers: {'X-Idempotency-Key': requestId}),
        );

        if (response.statusCode == 201 || response.statusCode == 200) {
          await box.delete(key);
        }
      } catch (e) {
        continue;
      }
    }
  }
}
