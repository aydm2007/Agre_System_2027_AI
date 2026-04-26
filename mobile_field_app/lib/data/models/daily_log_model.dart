import 'package:uuid/uuid.dart';

/// AgriAsset Sovereign Model: DailyLog
/// Enforces Axis 6 (Tenant Isolation), Axis 20 (Idempotency), and Axis 26 (GIS).
class DailyLogModel {
  final String id;
  final String mobileRequestId; // IDEMPOTENCY KEY (Axis 20)
  final String farmId;          // TENANT SCOPE (Axis 6)
  final String cropPlanId;      // ANALYTICAL PURITY (Axis 11)
  final double quantity;         // DECIMAL-EQUIVALENT (Axis 2)
  final String activityType;
  final double lat;             // GIS (Axis 26)
  final double lng;
  final double accuracy;
  final DateTime timestamp;

  DailyLogModel({
    String? id,
    required this.mobileRequestId,
    required this.farmId,
    required this.cropPlanId,
    required this.quantity,
    required this.activityType,
    required this.lat,
    required this.lng,
    required this.accuracy,
    DateTime? timestamp,
  }) : id = id ?? const Uuid().v4(),
       timestamp = timestamp ?? DateTime.now();

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'mobile_request_id': mobileRequestId,
      'farm_id': farmId,
      'crop_plan_id': cropPlanId,
      'quantity': quantity,
      'activity_type': activityType,
      'lat': lat,
      'lng': lng,
      'accuracy': accuracy,
      'timestamp': timestamp.toIso8601String(),
    };
  }

  factory DailyLogModel.fromJson(Map<String, dynamic> json) {
    return DailyLogModel(
      id: json['id'],
      mobileRequestId: json['mobile_request_id'],
      farmId: json['farm_id'],
      cropPlanId: json['crop_plan_id'],
      quantity: json['quantity'].toDouble(),
      activityType: json['activity_type'],
      lat: json['lat'],
      lng: json['lng'],
      accuracy: json['accuracy'],
      timestamp: DateTime.parse(json['timestamp']),
    );
  }
}
