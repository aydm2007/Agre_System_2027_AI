import 'dart:io';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import 'package:image/image.dart' as img;

class AttachmentSanitizer {
  /// Enhanced Sanitization with Auto-Clarity and Smart Scaling.
  static Future<File?> sanitizeImage(File originalFile, {bool autoEnhance = true}) async {
    try {
      final tempDir = await getTemporaryDirectory();
      String currentSourcePath = originalFile.absolute.path;

      // 1. [OPTIONAL] [AUTO-CLARITY]
      if (autoEnhance) {
        final bytes = await originalFile.readAsBytes();
        final image = img.decodeImage(bytes);
        if (image != null) {
          // Linear enhancement for field legibility (Axis 29)
          final enhanced = img.adjustColor(
            image, 
            brightness: 1.05, 
            contrast: 1.1,
            saturation: 1.1,
          );
          final enhancedPath = p.join(tempDir.path, "ENH_${DateTime.now().millisecondsSinceEpoch}.jpg");
          await File(enhancedPath).writeAsBytes(img.encodeJpg(enhanced, quality: 90));
          currentSourcePath = enhancedPath;
        }
      }

      final targetPath = p.join(
        tempDir.path, 
        "S_IMG_${DateTime.now().millisecondsSinceEpoch}.jpg"
      );

      // 2. [SMART SCALING] 
      // Higher compression & lower resolution for very large files (> 5MB)
      final int originalSize = await originalFile.length();
      final int targetWidth = originalSize > 5 * 1024 * 1024 ? 1280 : 1600;
      final int quality = originalSize > 5 * 1024 * 1024 ? 75 : 85;

      // 3. [AGRI-GUARDIAN] Axis 29: Strip metadata and final compress.
      final XFile? result = await FlutterImageCompress.compressAndGetFile(
        currentSourcePath,
        targetPath,
        quality: quality,
        minWidth: targetWidth,
        minHeight: 1200,
        format: CompressFormat.jpeg,
      );

      if (result == null) return null;
      return File(result.path);
    } catch (e) {
      return originalFile;
    }
  }

  /// Verifies if a file is 'Sovereign-Safe' (optional extension check)
  static bool isSafeExtension(String filePath) {
    final ext = p.extension(filePath).toLowerCase();
    const allowed = ['.jpg', '.jpeg', '.png', '.pdf'];
    return allowed.contains(ext);
  }
}
