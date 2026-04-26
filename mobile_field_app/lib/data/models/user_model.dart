import 'dart:convert';

/// AgriAsset Sovereign Model: User
/// Enforces Axis 4 (RBAC) and Axis 6 (Tenant Isolation).
class UserModel {
  final int id;
  final String username;
  final String fullName;
  final String role; // e.g., 'SUPERVISOR', 'MANAGER', 'ADMIN'
  final List<int> assignedFarmIds;
  final Map<String, bool> permissions;

  UserModel({
    required this.id,
    required this.username,
    required this.fullName,
    required this.role,
    required this.assignedFarmIds,
    this.permissions = const {},
  });

  bool hasPermission(String permission) => permissions[permission] ?? false;

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'full_name': fullName,
      'role': role,
      'assigned_farm_ids': assignedFarmIds,
      'permissions': permissions,
    };
  }

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'],
      username: json['username'],
      fullName: json['full_name'] ?? json['username'],
      role: json['role'] ?? 'USER',
      assignedFarmIds: List<int>.from(json['assigned_farm_ids'] ?? []),
      permissions: Map<String, bool>.from(json['permissions'] ?? {}),
    );
  }
}
