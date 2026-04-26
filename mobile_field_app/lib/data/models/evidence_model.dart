import 'dart:io';
import 'package:hive/hive.dart';

part 'evidence_model.g.dart';

@HiveType(typeId: 10)
class EvidenceModel extends HiveObject {
  @HiveField(0)
  final String filePath;
  
  @HiveField(1)
  final DateTime capturedAt;
  
  @HiveField(2)
  final String category; // e.g., 'DailyLog', 'Transfer'
  
  @HiveField(3)
  final String? referenceId; // The ID of the log/transfer
  
  @HiveField(4)
  final bool isSynced;

  EvidenceModel({
    required this.filePath,
    required this.capturedAt,
    required this.category,
    this.referenceId,
    this.isSynced = false,
  });

  Map<String, dynamic> toJson() => {
    'filePath': filePath,
    'capturedAt': capturedAt.toIso8601String(),
    'category': category,
    'referenceId': referenceId,
    'isSynced': isSynced,
  };
}

class EvidenceRepository {
  static const String boxName = 'evidence_vault';

  Future<void> addEvidence(EvidenceModel evidence) async {
    final box = await Hive.openBox<EvidenceModel>(boxName);
    await box.add(evidence);
  }

  Future<List<EvidenceModel>> getAllEvidence() async {
    final box = await Hive.openBox<EvidenceModel>(boxName);
    return box.values.toList().reversed.toList();
  }

  /// Axix 23: Purge evidence older than 7 days.
  Future<void> purgeOldEvidence() async {
    final box = await Hive.openBox<EvidenceModel>(boxName);
    final now = DateTime.now();
    final sevenDaysAgo = now.subtract(const Duration(days: 7));
    
    final toDelete = box.keys.where((key) {
      final evidence = box.get(key);
      return evidence != null && evidence.capturedAt.isBefore(sevenDaysAgo);
    }).toList();

    for (var key in toDelete) {
      final evidence = box.get(key);
      if (evidence != null) {
        final file = File(evidence.filePath);
        if (await file.exists()) {
          await file.delete();
        }
        await box.delete(key);
      }
    }
  }
}
