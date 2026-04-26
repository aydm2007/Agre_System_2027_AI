import 'dart:typed_data';
import 'package:uuid/uuid.dart';

/// AgriAsset Sovereign Model: MaterialTransfer
/// Enforces Axis 11 (Analytical Purity) and Axis 22 (Attachment Lifecycle).
class MaterialTransferModel {
  final String id;
  final String mobileRequestId;
  final int farmId;
  final int storekeeperId;
  final int receiverId; // Usually Supervisor
  final List<TransferItem> items;
  final Uint8List? signature; // Forensic Artifact (Axis 22)
  final DateTime timestamp;

  MaterialTransferModel({
    String? id,
    required this.mobileRequestId,
    required this.farmId,
    required this.storekeeperId,
    required this.receiverId,
    required this.items,
    this.signature,
    DateTime? timestamp,
  }) : id = id ?? const Uuid().v4(),
       timestamp = timestamp ?? DateTime.now();

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'mobile_request_id': mobileRequestId,
      'farm_id': farmId,
      'storekeeper_id': storekeeperId,
      'receiver_id': receiverId,
      'items': items.map((i) => i.toJson()).toList(),
      'timestamp': timestamp.toIso8601String(),
      // Signature handle separately as a blob/file upload
    };
  }
}

class TransferItem {
  final int itemId;
  final String itemName;
  final double quantity;
  final String uom;

  TransferItem({
    required this.itemId,
    required this.itemName,
    required this.quantity,
    required this.uom,
  });

  Map<String, dynamic> toJson() {
    return {
      'item_id': itemId,
      'item_name': itemName,
      'quantity': quantity,
      'uom': uom,
    };
  }
}
