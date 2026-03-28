import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class ConversationHistoryService {
  static const String _historyKeyPrefix = 'conversation_history_';
  static const int _maxHistorySize = 50;
  
  static Future<List<Map<String, dynamic>>> getHistory(String userId) async {
    final prefs = await SharedPreferences.getInstance();
    final key = '$_historyKeyPrefix$userId';
    final historyJson = prefs.getString(key);
    
    if (historyJson == null || historyJson.isEmpty) {
      return [];
    }
    
    try {
      final List<dynamic> decoded = jsonDecode(historyJson);
      return decoded.cast<Map<String, dynamic>>();
    } catch (e) {
      return [];
    }
  }
  
  static Future<void> addMessage(String userId, String role, String content, {String? language}) async {
    final prefs = await SharedPreferences.getInstance();
    final key = '$_historyKeyPrefix$userId';
    
    final history = await getHistory(userId);
    
    history.add({
      'role': role,
      'content': content,
      'timestamp': DateTime.now().toIso8601String(),
      'language': language ?? 'english',
    });
    
    if (history.length > _maxHistorySize) {
      history.removeRange(0, history.length - _maxHistorySize);
    }
    
    await prefs.setString(key, jsonEncode(history));
  }
  
  static Future<void> clearHistory(String userId) async {
    final prefs = await SharedPreferences.getInstance();
    final key = '$_historyKeyPrefix$userId';
    await prefs.remove(key);
  }
  
  static Future<String> getContextString(String userId) async {
    final history = await getHistory(userId);
    
    if (history.isEmpty) {
      return '';
    }
    
    final contextParts = <String>[];
    for (final msg in history) {
      final role = msg['role'] as String? ?? 'user';
      final content = msg['content'] as String? ?? '';
      if (content.isNotEmpty) {
        contextParts.add('$role: $content');
      }
    }
    
    return contextParts.join('\n');
  }
}
