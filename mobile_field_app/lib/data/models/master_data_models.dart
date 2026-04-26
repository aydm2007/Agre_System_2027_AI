/// AgriAsset Master Model: CropPlan
/// Enforces Axis 6 (Tenant Isolation) and Axis 11 (Analytical Purity).
class CropPlanModel {
  final int id;
  final String name;
  final int farmId;
  final int cropId;
  final List<int> locationIds;

  CropPlanModel({
    required this.id,
    required this.name,
    required this.farmId,
    required this.cropId,
    required this.locationIds,
  });

  factory CropPlanModel.fromJson(Map<String, dynamic> json) {
    return CropPlanModel(
      id: json['id'],
      name: json['name'],
      farmId: json['farm'],
      cropId: json['crop'],
      locationIds: List<int>.from(json['locations'] ?? []),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'farm': farmId,
      'crop': cropId,
      'locations': locationIds,
    };
  }
}

/// AgriAsset Master Model: Item (Material)
class ItemModel {
  final int id;
  final String name;
  final String uom;
  final double currentStock;

  ItemModel({
    required this.id,
    required this.name,
    required this.uom,
    this.currentStock = 0,
  });

  factory ItemModel.fromJson(Map<String, dynamic> json) {
    return ItemModel(
      id: json['id'],
      name: json['name'],
      uom: json['uom_display'] ?? json['uom'] ?? 'PCS',
      currentStock: (json['current_stock'] ?? 0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'uom': uom,
      'current_stock': currentStock,
    };
  }
}

/// AgriAsset Master Model: TaskArchetype
class TaskArchetypeModel {
  final int id;
  final String code;
  final String name;
  final String nameArabic;

  TaskArchetypeModel({
    required this.id,
    required this.code,
    required this.name,
    required this.nameArabic,
  });

  factory TaskArchetypeModel.fromJson(Map<String, dynamic> json) {
    return TaskArchetypeModel(
      id: json['id'],
      code: json['code'] ?? '',
      name: json['name'] ?? '',
      nameArabic: json['name_arabic'] ?? json['name'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'code': code,
      'name': name,
      'name_arabic': nameArabic,
    };
  }
}
