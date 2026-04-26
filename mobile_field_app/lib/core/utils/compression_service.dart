import 'dart:io';
import 'dart:math';
import 'package:flutter_image_compress/flutter_image_compress.dart';

class CompressionService {
  static const int maxFileSizeKb = 100; // 2G Survival Standard

  static Future<File?> compressImage(File file) async {
    final filePath = file.absolute.path;
    final lastIndex = filePath.lastIndexOf(RegExp(r'.png|.jp'));
    final splitted = filePath.substring(0, (lastIndex));
    final outPath = "${splitted}_out${filePath.substring(lastIndex)}";

    int quality = 85;
    XFile? result = await FlutterImageCompress.compressAndGetFile(
      file.absolute.path,
      outPath,
      quality: quality,
      minWidth: 1024,
      minHeight: 1024,
    );

    if (result == null) return null;

    int fileSize = await result.length();
    
    // Recursive aggressive compression if still too large
    while (fileSize > maxFileSizeKb * 1024 && quality > 10) {
      quality -= 15;
      result = await FlutterImageCompress.compressAndGetFile(
        file.absolute.path,
        outPath,
        quality: max(quality, 5),
        minWidth: 800,
        minHeight: 800,
      );
      if (result == null) break;
      fileSize = await result.length();
    }

    return result != null ? File(result.path) : null;
  }
}
