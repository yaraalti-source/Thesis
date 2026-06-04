import 'package:flutter/material.dart';
import 'package:gesture_talk/services/connectivity_service.dart';
import 'package:gesture_talk/theme/app_theme.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

class OfflineIndicator extends StatelessWidget {
  const OfflineIndicator({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<ConnectivityService>(
      builder: (context, connectivity, child) {
        if (connectivity.isOnline) {
          return const SizedBox.shrink();
        }

        return Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: AppTheme.warning.withOpacity(0.2),
            border: Border(
              bottom: BorderSide(
                color: AppTheme.warning.withOpacity(0.5),
                width: 1,
              ),
            ),
          ),
          child: Row(
            children: [
              Icon(
                Icons.cloud_off,
                color: AppTheme.warning,
                size: 20,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Offline Mode - Translations will sync when online',
                  style: GoogleFonts.poppins(
                    fontSize: 12,
                    color: AppTheme.warning,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}










