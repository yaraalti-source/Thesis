import 'dart:async';
import 'dart:io';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';

class ConnectivityService extends ChangeNotifier {
  final Connectivity _connectivity = Connectivity();
  StreamSubscription<ConnectivityResult>? _connectivitySubscription;
  
  bool _isOnline = true;
  bool get isOnline => _isOnline;
  bool get isConnected => _isOnline; // Alias for compatibility

  ConnectivityService() {
    _initConnectivity();
    _connectivitySubscription = _connectivity.onConnectivityChanged.listen(
      (result) async {
        await _updateConnectionStatus(result);
      },
      onError: (error) {
        print('Connectivity error: $error');
      },
    );
  }

  Future<void> _initConnectivity() async {
    try {
      final result = await _connectivity.checkConnectivity();
      await _updateConnectionStatus(result);
    } catch (e) {
      print('Error checking connectivity: $e');
      _isOnline = false;
      notifyListeners();
    }
  }

  Future<void> _updateConnectionStatus(ConnectivityResult result) async {
    final wasOnline = _isOnline;
    
    // First check if there's a network connection type
    if (result == ConnectivityResult.none) {
      _isOnline = false;
    } else {
      // If we have a network type (WiFi/mobile), assume online
      // The actual HTTP request will determine if really offline
      _isOnline = true;
    }
    
    if (wasOnline != _isOnline) {
      notifyListeners();
      print('Connection status changed: ${_isOnline ? "Online" : "Offline"}');
    }
  }

  // Check if there's actual internet connectivity (not just network type)
  Future<bool> _hasInternetConnection() async {
    try {
      // Try to reach a reliable server with shorter timeout
      final result = await InternetAddress.lookup('google.com')
          .timeout(const Duration(seconds: 3));
      if (result.isNotEmpty && result[0].rawAddress.isNotEmpty) {
        return true;
      }
    } catch (e) {
      print('Internet check failed (google.com): $e');
    }
    
    // Fallback: try another server
    try {
      final result = await InternetAddress.lookup('8.8.8.8')
          .timeout(const Duration(seconds: 2));
      if (result.isNotEmpty && result[0].rawAddress.isNotEmpty) {
        return true;
      }
    } catch (e2) {
      print('Internet check failed (8.8.8.8): $e2');
    }
    
    // If both fail, but we have network type, assume connected
    // (some networks block DNS but allow HTTP)
    return true; // Optimistic - let the HTTP request determine if really offline
  }

  Future<bool> checkConnectivity() async {
    try {
      final result = await _connectivity.checkConnectivity();
      if (result == ConnectivityResult.none) {
        _isOnline = false;
        notifyListeners();
        return false;
      }
      // If we have a network type, assume online
      // The HTTP request will handle actual connectivity
      _isOnline = true;
      notifyListeners();
      return true;
    } catch (e) {
      print('Error checking connectivity: $e');
      // On error, assume online and let HTTP request determine
      _isOnline = true;
      notifyListeners();
      return true;
    }
  }

  @override
  void dispose() {
    _connectivitySubscription?.cancel();
    super.dispose();
  }
}

