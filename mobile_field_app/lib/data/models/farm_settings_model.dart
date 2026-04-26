/// AgriAsset Sovereign Model: FarmSettings
/// Governs Axis 14 (Feature Toggles) and Axial Dual-Mode (SIMPLE/STRICT).
class FarmSettingsModel {
  final int farmId;
  final String mode; // 'SIMPLE' or 'STRICT'
  final bool enableTreeGisZoning;
  final bool showDailyLogSmartCard;
  final bool allowCreatorSelfVarianceApproval;
  final String approvalProfile; // e.g., 'strict_finance'

  FarmSettingsModel({
    required this.farmId,
    required this.mode,
    this.enableTreeGisZoning = false,
    this.showDailyLogSmartCard = true,
    this.allowCreatorSelfVarianceApproval = false,
    this.approvalProfile = 'standard',
  });

  bool get isStrict => mode == 'STRICT';
  bool get isSimple => mode == 'SIMPLE';

  factory FarmSettingsModel.fromJson(Map<String, dynamic> json) {
    return FarmSettingsModel(
      farmId: json['farm_id'],
      mode: json['mode'] ?? 'SIMPLE',
      enableTreeGisZoning: json['enable_tree_gis_zoning'] ?? false,
      showDailyLogSmartCard: json['show_daily_log_smart_card'] ?? true,
      allowCreatorSelfVarianceApproval: json['allow_creator_self_variance_approval'] ?? false,
      approvalProfile: json['approval_profile'] ?? 'standard',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'farm_id': farmId,
      'mode': mode,
      'enable_tree_gis_zoning': enableTreeGisZoning,
      'show_daily_log_smart_card': showDailyLogSmartCard,
      'allow_creator_self_variance_approval': allowCreatorSelfVarianceApproval,
      'approval_profile': approvalProfile,
    };
  }
}
