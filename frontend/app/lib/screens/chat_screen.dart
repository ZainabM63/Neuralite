import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import '../models/message.dart';
import '../services/api_service.dart';
import '../services/voice_service.dart';
import '../services/device_action_service.dart';
import '../widgets/input_area.dart';
import '../widgets/message_bubble.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<Message> _messages = [];
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _focusNode = FocusNode();
  final ApiService _apiService = ApiService();
  final VoiceService _voiceService = VoiceService();
  final DeviceActionService _deviceActionService = DeviceActionService();
  
  bool _isLoading = false;
  bool _isListening = false;
  bool _isSpeaking = false;
  bool _autoSpeak = true;
  bool _isMaleVoice = true;
  double _speechRate = 0.8;
  Message? _pendingConfirmation;
  String _userId = 'user_123';
  String _serverUrl = ApiService.baseUrl;
  String _lastIntent = 'general_chat';
  String _lastTarget = '';

  @override
  void initState() {
    super.initState();
    _initializeServices();
    _initializeVoiceService();
    _setupVoiceCallbacks();
  }

  Future<void> _initializeServices() async {
    await ApiService.initialize();
    setState(() {
      _serverUrl = ApiService.baseUrl;
    });
  }

  Future<void> _initializeVoiceService() async {
    await _voiceService.initialize();
    setState(() {
      _isMaleVoice = _voiceService.isMaleVoice;
    });
  }

  void _setupVoiceCallbacks() {
    _voiceService.onResult = (text) {
      if (text.isNotEmpty) {
        _textController.text = text;
        _sendMessage();
      }
    };

    _voiceService.onStateChange = (state) {
      setState(() {
        _isListening = state == VoiceServiceState.listening;
        _isSpeaking = state == VoiceServiceState.speaking;
      });
    };

    _voiceService.onError = (error) {
      _showSnackBar('Voice error: $error');
    };
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    _voiceService.dispose();
    _apiService.dispose();
    super.dispose();
  }

  Future<void> _requestPermissions() async {
    final micStatus = await Permission.microphone.request();
    if (micStatus.isDenied) {
      _showSnackBar('Microphone permission is required for voice input');
    }
  }

  Future<void> _toggleVoiceInput() async {
    if (_isListening) {
      await _voiceService.stopListening();
    } else {
      await _requestPermissions();
      await _voiceService.startListening();
    }
  }

  Future<void> _sendMessage() async {
    final String text = _textController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _messages.insert(0, UserMessage(content: text));
      _textController.clear();
      _isLoading = true;
      _pendingConfirmation = null;
    });
    _scrollToBottom();

    try {
      final Map<String, dynamic> response = await _apiService.sendMessage(
        text, 
        userId: _userId,
        lastIntent: _lastIntent,
        lastTarget: _lastTarget,
      );
      final Message assistantMessage = Message.fromJson(response);
      
      setState(() {
        _messages.insert(0, assistantMessage);
        _isLoading = false;
        
        if (assistantMessage.requiresConfirmation) {
          _pendingConfirmation = assistantMessage;
          _lastIntent = assistantMessage.intent;
          _lastTarget = assistantMessage.actionType ?? '';
        }
      });
      _scrollToBottom();
      
      if (_autoSpeak && !assistantMessage.requiresConfirmation) {
        await _speakMessage(assistantMessage.content);
      }
      
      if (assistantMessage.hasDeviceAction && assistantMessage.actionType != 'search_web') {
        await _executeDeviceAction(assistantMessage);
      }
    } catch (e) {
      String errorMessage = 'Unable to connect to server. Please make sure the backend is running on port 8000.';
      
      // Extract cleaner error message
      String error = e.toString();
      if (error.contains('SocketException') || error.contains('Connection refused')) {
        errorMessage = 'Cannot connect to server. Please start the backend:\n\ncd backend\npython -m uvicorn app.main:app --reload';
      } else if (error.contains('timeout')) {
        errorMessage = 'Server is taking too long to respond. Please try again.';
      }
      
      setState(() {
        _messages.insert(0, Message(
          content: errorMessage,
          sender: 'assistant',
          emotion: 'neutral',
          intent: 'error',
        ));
        _isLoading = false;
      });
      _scrollToBottom();
    }
  }

  Future<void> _handleConfirmation(bool confirmed) async {
    if (_pendingConfirmation == null) return;

    final response = confirmed
        ? 'yes'
        : 'no';

    setState(() {
      _isLoading = true;
    });

    try {
      final Map<String, dynamic> apiResponse = await _apiService.confirmAction(response, userId: _userId);
      final Message confirmationResponse = Message.fromJson(apiResponse);
      
      setState(() {
        _messages.insert(0, confirmationResponse);
        _isLoading = false;
        _pendingConfirmation = null;
      });
      _scrollToBottom();
      
      if (_autoSpeak) {
        await _speakMessage(confirmationResponse.content);
      }
      
      if (confirmationResponse.hasDeviceAction) {
        await _executeDeviceAction(confirmationResponse);
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _pendingConfirmation = null;
      });
      _showSnackBar('Error: $e');
    }
  }

  Future<void> _handleOptionSelected(String option, Message message) async {
    setState(() {
      _messages.insert(0, UserMessage(content: option));
      _isLoading = true;
    });
    _scrollToBottom();

    try {
      final response = await _apiService.sendMessage(option, userId: _userId);
      final assistantMessage = Message.fromJson(response);
      
      setState(() {
        _messages.insert(0, assistantMessage);
        _isLoading = false;
        
        if (assistantMessage.requiresConfirmation) {
          _pendingConfirmation = assistantMessage;
        }
      });
      _scrollToBottom();
      
      if (_autoSpeak && !assistantMessage.requiresConfirmation) {
        await _speakMessage(assistantMessage.content);
      }
      
      if (assistantMessage.hasDeviceAction && assistantMessage.actionType != 'search_web') {
        await _executeDeviceAction(assistantMessage);
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
      _showSnackBar('Error: $e');
    }
  }

  Future<void> _executeDeviceAction(Message message, {bool confirmed = false}) async {
    final deviceAction = message.deviceAction;
    if (deviceAction == null) return;

    final requiresConfirmation = deviceAction['requires_confirmation'] as bool? ?? false;
    
    if (requiresConfirmation && !confirmed) {
      _showDeviceActionConfirmation(deviceAction);
      return;
    }

    final success = await _deviceActionService.executeAction(deviceAction);
    if (!success) {
      _showSnackBar('Could not execute action');
    } else {
      final actionType = deviceAction['type'] ?? deviceAction['action'] ?? 'action';
      _showSnackBar('Action executed: $actionType');
    }
  }

  void _showDeviceActionConfirmation(Map<String, dynamic> deviceAction) {
    final actionType = deviceAction['type'] ?? deviceAction['action'] ?? 'this action';
    final target = deviceAction['target'] ?? '';
    final appName = deviceAction['app_name'] ?? deviceAction['app'] ?? target;
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Confirm Action'),
        content: Text('Do you want to $actionType ${appName.isNotEmpty ? appName : target}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);
              _showSnackBar('Action confirmed');
              final success = await _deviceActionService.executeAction(deviceAction);
              if (!success) {
                _showSnackBar('Could not execute action');
              } else {
                _showSnackBar('Action executed: $actionType');
              }
            },
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
  }

  Future<void> _speakMessage(String text) async {
    if (_isSpeaking) {
      await _voiceService.stopSpeaking();
    }
    await _voiceService.speak(text);
  }

  void _stopSpeaking() {
    _voiceService.stopSpeaking();
    setState(() {
      _isSpeaking = false;
    });
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          0.0,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(seconds: 2),
        action: SnackBarAction(
          label: 'OK',
          onPressed: () {},
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Neura AI'),
        backgroundColor: Colors.blue[800],
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(_autoSpeak ? Icons.volume_up : Icons.volume_off),
            onPressed: () {
              setState(() {
                _autoSpeak = !_autoSpeak;
              });
              _showSnackBar(_autoSpeak ? 'Voice output enabled' : 'Voice output disabled');
            },
            tooltip: 'Toggle voice output',
          ),
          if (_isSpeaking)
            IconButton(
              icon: const Icon(Icons.stop),
              onPressed: _stopSpeaking,
              tooltip: 'Stop speaking',
            ),
          PopupMenuButton<String>(
            onSelected: (value) {
              switch (value) {
                case 'clear':
                  setState(() {
                    _messages.clear();
                  });
                  break;
                case 'settings':
                  _showSettingsDialog();
                  break;
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'clear',
                child: Row(
                  children: [
                    Icon(Icons.delete_outline),
                    SizedBox(width: 8),
                    Text('Clear chat'),
                  ],
                ),
              ),
              const PopupMenuItem(
                value: 'settings',
                child: Row(
                  children: [
                    Icon(Icons.settings),
                    SizedBox(width: 8),
                    Text('Settings'),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      resizeToAvoidBottomInset: true,
      body: Column(
        children: [
          Expanded(
            child: _messages.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.smart_toy,
                          size: 64,
                          color: Colors.blue[300],
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Hello! I\'m Neura, your AI assistant.',
                          style: TextStyle(
                            color: Colors.grey[600],
                            fontSize: 16,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Try voice input by tapping the mic button!',
                          style: TextStyle(
                            color: Colors.grey[500],
                            fontSize: 14,
                          ),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    reverse: true,
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      final message = _messages[index];
                      final showConfirmation = message == _pendingConfirmation;
                      
                      return MessageBubble(
                        message: message,
                        onConfirm: showConfirmation ? () => _handleConfirmation(true) : null,
                        onCancel: showConfirmation ? () => _handleConfirmation(false) : null,
                        onOptionSelected: message.hasOptions ? (option) => _handleOptionSelected(option, message) : null,
                      );
                    },
                  ),
          ),
          InputArea(
            textController: _textController,
            focusNode: _focusNode,
            onSend: _sendMessage,
            onVoiceStart: _toggleVoiceInput,
            onVoiceStop: _toggleVoiceInput,
            isLoading: _isLoading,
            isListening: _isListening,
          ),
        ],
      ),
    );
  }

  void _showSettingsDialog() {
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Settings'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                title: const Text('Server Address'),
                subtitle: Text(_serverUrl, style: const TextStyle(fontSize: 12)),
                trailing: const Icon(Icons.edit),
                onTap: () {
                  Navigator.pop(context);
                  _showServerUrlDialog();
                },
              ),
              const Divider(),
              SwitchListTile(
                title: const Text('Auto voice output'),
                subtitle: const Text('Automatically speak responses'),
                value: _autoSpeak,
                onChanged: (value) {
                  setState(() {
                    _autoSpeak = value;
                  });
                },
              ),
              SwitchListTile(
                title: const Text('Male Voice'),
                subtitle: const Text('Toggle between male and female voice'),
                value: _isMaleVoice,
                onChanged: (value) {
                  setState(() {
                    _isMaleVoice = value;
                  });
                  _voiceService.setVoiceGender(value);
                  _showSnackBar(value ? 'Male voice enabled' : 'Female voice enabled');
                },
              ),
              const SizedBox(height: 8),
              ListTile(
                title: const Text('Speech Speed'),
                subtitle: Slider(
                  value: _speechRate,
                  min: 0.3,
                  max: 1.0,
                  divisions: 7,
                  label: _getSpeechRateLabel(_speechRate),
                  onChanged: (value) {
                    setState(() {
                      _speechRate = value;
                    });
                    setDialogState(() {});
                    _voiceService.setSpeechRate(value);
                  },
                ),
              ),
              const Divider(),
              ListTile(
                title: const Text('User ID'),
                subtitle: Text(_userId),
                trailing: const Icon(Icons.edit),
                onTap: () {
                  Navigator.pop(context);
                  _showUserIdDialog();
                },
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            ),
          ],
        ),
      ),
    );
  }

  void _showServerUrlDialog() {
    final controller = TextEditingController(text: _serverUrl);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Server Address'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Enter your laptop\'s local IP address:',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'Server URL',
                hintText: 'http://192.168.1.100:8000',
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Make sure your phone and laptop are on the same WiFi network.',
              style: TextStyle(fontSize: 11, color: Colors.grey),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              final url = controller.text.trim();
              if (url.isNotEmpty) {
                await ApiService.setBaseUrl(url);
                setState(() {
                  _serverUrl = url;
                });
                _showSnackBar('Server updated to: $url');
              }
              Navigator.pop(context);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }
  
  String _getSpeechRateLabel(double rate) {
    if (rate < 0.5) return 'Slow';
    if (rate < 0.7) return 'Normal';
    if (rate < 0.9) return 'Fast';
    return 'Very Fast';
  }

  void _showUserIdDialog() {
    final controller = TextEditingController(text: _userId);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Set User ID'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'User ID',
            hintText: 'Enter your user ID',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              setState(() {
                _userId = controller.text.trim().isNotEmpty 
                    ? controller.text.trim() 
                    : 'user_123';
              });
              Navigator.pop(context);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }
}
