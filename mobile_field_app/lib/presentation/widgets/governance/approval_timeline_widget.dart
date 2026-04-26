import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

class ApprovalStageEvent {
  final String stage;
  final String status;
  final String actor;
  final DateTime timestamp;
  final String? notes;

  ApprovalStageEvent({
    required this.stage,
    required this.status,
    required this.actor,
    required this.timestamp,
    this.notes,
  });
}

class ApprovalTimelineWidget extends StatelessWidget {
  final List<ApprovalStageEvent> events;

  const ApprovalTimelineWidget({super.key, required this.events});

  @override
  Widget build(BuildContext context) {
    if (events.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Text(
            "لا يوجد سجل اعتمادات متاح",
            style: GoogleFonts.notoKufiArabic(color: Colors.white70),
          ),
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: events.length,
      itemBuilder: (context, index) {
        final event = events[index];
        final isLast = index == events.length - 1;

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Column(
              children: [
                Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    color: _getStatusColor(event.status),
                    shape: BoxShape.circle,
                  ),
                ),
                if (!isLast)
                  Container(
                    width: 2,
                    height: 50,
                    color: Colors.white24,
                  ),
              ],
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        event.stage,
                        style: GoogleFonts.notoKufiArabic(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                      Text(
                        DateFormat('yyyy/MM/dd HH:mm').format(event.timestamp),
                        style: GoogleFonts.notoKufiArabic(
                          color: Colors.white38,
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ),
                  Text(
                    "${event.actor} - ${_getStatusLabel(event.status)}",
                    style: GoogleFonts.notoKufiArabic(
                      color: _getStatusColor(event.status),
                      fontSize: 12,
                    ),
                  ),
                  if (event.notes != null && event.notes!.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 4, bottom: 8),
                      child: Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.05),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          event.notes!,
                          style: GoogleFonts.notoKufiArabic(
                            color: Colors.white70,
                            fontSize: 11,
                          ),
                        ),
                      ),
                    ),
                  const SizedBox(height: 16),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'approved':
      case 'finalApproved':
        return Colors.greenAccent;
      case 'rejected':
      case 'returned':
        return Colors.redAccent;
      case 'pending':
        return Colors.orangeAccent;
      default:
        return Colors.blueAccent;
    }
  }

  String _getStatusLabel(String status) {
    switch (status.toLowerCase()) {
      case 'approved': return "تم الاعتماد";
      case 'finalapproved': return "اعتماد نهائي";
      case 'rejected': return "تم الرفض";
      case 'returned': return "أعيد للمراجعة";
      case 'pending': return "قيد الانتظار";
      default: return status;
    }
  }
}
