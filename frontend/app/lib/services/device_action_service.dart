import 'package:url_launcher/url_launcher.dart';
import 'package:flutter/services.dart';

class DeviceActionService {
  static final DeviceActionService _instance = DeviceActionService._internal();
  factory DeviceActionService() => _instance;
  DeviceActionService._internal();

  static const MethodChannel _channel = MethodChannel('com.neura.app/device_actions');

  Future<bool> executeAction(Map<String, dynamic> action) async {
    final actionType = action['type'] as String? ?? action['action'] as String? ?? '';
    final data = action['data'] as Map<String, dynamic>? ?? {};
    final target = action['target'] as String? ?? '';
    
    try {
      switch (actionType) {
        case 'send_message':
        case 'send_whatsapp_message':
        case 'make_call':
        case 'make_whatsapp_call':
        case 'set_reminder':
        case 'set_alarm':
        case 'send_email':
          return await _executeViaNative(actionType, target, data);
        case 'open_app':
          return await _handleOpenApp(data);
        case 'search_web':
          return await _handleSearchWeb(data);
        default:
          return false;
      }
    } catch (e) {
      print('Error executing action: $e');
      return false;
    }
  }

  Future<bool> _executeViaNative(String actionType, String target, Map<String, dynamic> data) async {
    try {
      final result = await _channel.invokeMethod('executeDeviceAction', {
        'action_type': actionType,
        'target': target,
        'data': data,
        'confirmed': true,
      });
      return result != null;
    } catch (e) {
      print('Native execution failed: $e');
      return false;
    }
  }

  Future<bool> _handleOpenApp(Map<String, dynamic> data) async {
    final package = data['package'] as String?;
    
    if (package == null) {
      return false;
    }
    
    try {
      await _channel.invokeMethod('launchApp', {'package': package});
      return true;
    } catch (e) {
      print('Error launching app: $e');
      return false;
    }
  }

  Future<bool> _handleSearchWeb(Map<String, dynamic> data) async {
    final searchUrl = data['search_url'] as String?;
    final query = data['query'] as String?;
    
    String url = searchUrl ?? '';
    if (url.isEmpty && query != null) {
      final encodedQuery = Uri.encodeComponent(query);
      url = 'https://www.google.com/search?q=$encodedQuery';
    }
    
    if (url.isEmpty) {
      return false;
    }
    
    return await _launchUri(url);
  }

  Future<bool> _launchUri(String uriString) async {
    try {
      final uri = Uri.parse(uriString);
      if (await canLaunchUrl(uri)) {
        return await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
      return false;
    } catch (e) {
      print('Error launching URI: $e');
      return false;
    }
  }

  Future<Map<String, dynamic>?> getDeviceActionResponse({
    required String actionType,
    required String target,
    required Map<String, dynamic> data,
    bool confirmed = false,
  }) async {
    try {
      final result = await _channel.invokeMethod('executeDeviceAction', {
        'action_type': actionType,
        'target': target,
        'data': data,
        'confirmed': confirmed,
      });
      return Map<String, dynamic>.from(result ?? {});
    } catch (e) {
      print('Error getting device action response: $e');
      return null;
    }
  }
}
