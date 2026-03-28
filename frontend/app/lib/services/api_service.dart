import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'conversation_history_service.dart';

class ApiService {
  static String _baseUrl = 'http://192.168.100.8:8000';
  static bool _initialized = false;
  
  final http.Client _client = http.Client();

  static Future<void> initialize() async {
    if (_initialized) return;
    final prefs = await SharedPreferences.getInstance();
    final savedUrl = prefs.getString('backend_url');
    if (savedUrl != null && savedUrl.isNotEmpty) {
      _baseUrl = savedUrl;
    }
    _initialized = true;
  }

  static Future<void> setBaseUrl(String url) async {
    _baseUrl = url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('backend_url', url);
  }

  static String get baseUrl => _baseUrl;

  Future<Map<String, dynamic>> sendMessage(String message, {String userId = 'user_123', String? lastIntent, String? lastTarget}) async {
    try {
      print('Sending request to backend...');
      
      final conversationContext = await ConversationHistoryService.getContextString(userId);
      
      final requestBody = {
        'user_id': userId,
        'text': message,
        'conversation_context': conversationContext,
      };
      
      if (lastIntent != null) {
        requestBody['last_intent'] = lastIntent;
      }
      if (lastTarget != null) {
        requestBody['last_target'] = lastTarget;
      }
      
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/process'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(requestBody),
      ).timeout(const Duration(seconds: 30));

      print('Response status: ${response.statusCode}');

      if (response.statusCode == 200) {
        final responseData = Map<String, dynamic>.from(jsonDecode(response.body));
        
        await ConversationHistoryService.addMessage(userId, 'user', message);
        
        final reply = responseData['reply'] as String?;
        if (reply != null && reply.isNotEmpty) {
          await ConversationHistoryService.addMessage(userId, 'assistant', reply);
        }
        
        return responseData;
      } else {
        throw Exception('Server error: ${response.statusCode}');
      }
    } catch (e) {
      print('API Error: $e');
      throw Exception('Unable to connect to server. Please make sure the backend is running.');
    }
  }

  Future<Map<String, dynamic>> confirmAction(String userInput, {String userId = 'user_123'}) async {
    try {
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/confirm_action'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'user_id': userId,
          'text': userInput,
        }),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        return Map<String, dynamic>.from(jsonDecode(response.body));
      } else {
        throw Exception('Server error: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Unable to connect to server: $e');
    }
  }

  Future<Map<String, dynamic>> executeDeviceAction({
    required String actionType,
    required String target,
    required Map<String, dynamic> data,
    bool confirmed = false,
  }) async {
    try {
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/device_action'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'action_type': actionType,
          'target': target,
          'data': data,
          'confirmed': confirmed,
        }),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        return Map<String, dynamic>.from(jsonDecode(response.body));
      } else {
        throw Exception('Server error: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Unable to connect to server: $e');
    }
  }

  Future<Map<String, dynamic>> getUserPreferences(String userId) async {
    try {
      final response = await _client.get(
        Uri.parse('$_baseUrl/api/v1/user/$userId/preferences'),
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        return Map<String, dynamic>.from(jsonDecode(response.body));
      } else {
        throw Exception('Server error: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Unable to connect to server: $e');
    }
  }

  Future<void> clearHistory(String userId) async {
    try {
      await ConversationHistoryService.clearHistory(userId);
      await _client.delete(
        Uri.parse('$_baseUrl/api/v1/user/$userId/history'),
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 30));
    } catch (e) {
      throw Exception('Failed to clear history: $e');
    }
  }

  void dispose() {
    _client.close();
  }
}
