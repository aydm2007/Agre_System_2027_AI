import 'package:geolocator/geolocator.dart';

class GpsService {
  static const double grpMaxAccuracyMeters = 50.0;

  static Future<Position?> getCurrentLocation() async {
    // ... code ...
    try {
      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 15),
      );
      
      // Sovereign Rule: Reject accuracy worse than threshold for technical logs
      if (position.accuracy > grpMaxAccuracyMeters) {
        return null; 
      }
      
      return position;
    } catch (e) {
      return null;
    }
  }

  static bool isLocationValid(Position? position) {
    if (position == null) return false;
    return position.accuracy <= grpMaxAccuracyMeters;
  }
}
