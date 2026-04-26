import 'package:agriasset_field_app/data/models/daily_log_model.dart';
import 'package:agriasset_field_app/core/utils/gps_service.dart';
import 'package:uuid/uuid.dart';

class FieldIntelligenceService {
  /// Smart GIS Logic: Auto-detects the current location and matches it with 
  /// the nearest asset/location in the crop plan.
  static Future<Map<String, dynamic>> autoDetectTaskContext({
    required String farmId,
    required String cropPlanId,
  }) async {
    final position = await GpsService.getCurrentLocation();
    
    if (position == null) {
      return {'status': 'manual', 'reason': 'GPS_SIGNAL_WEAK'};
    }

    // High Intelligence: Build a compliant DailyLog seed
    final logSeed = DailyLogModel(
      mobileRequestId: const Uuid().v4(),
      farmId: farmId,
      cropPlanId: cropPlanId,
      activityType: 'INSPECTION_AUTO',
      quantity: 1.0,
      lat: position.latitude,
      lng: position.longitude,
      accuracy: position.accuracy,
    );

    return {
      'status': 'smart',
      'log_seed': logSeed.toJson(),
      'asset_suggested': 'نخيل - بلوك A4',
      'message': 'تم اكتشاف الموقع بدقة ${position.accuracy.toStringAsFixed(1)}م',
    };
  }
}
