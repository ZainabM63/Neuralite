class Message {
  final String content;
  final String sender;
  final String emotion;
  final String intent;
  final String? actionType;
  final String? actionTarget;
  final Map<String, dynamic>? actionData;
  final Map<String, dynamic>? deviceAction;
  final String? status;
  final List<String>? options;
  final bool requiresConfirmation;

  Message({
    required this.content,
    required this.sender,
    required this.emotion,
    required this.intent,
    this.actionType,
    this.actionTarget,
    this.actionData,
    this.deviceAction,
    this.status,
    this.options,
    this.requiresConfirmation = false,
  });

  factory Message.fromJson(Map<String, dynamic> json) {
    final action = json['action'] as Map<String, dynamic>?;
    
    return Message(
      content: json['reply'] ?? '',
      sender: 'assistant',
      emotion: json['emotion'] ?? 'neutral',
      intent: json['intent'] ?? 'general_chat',
      actionType: action?['type'] as String?,
      actionTarget: action?['target'] as String?,
      actionData: action?['data'] as Map<String, dynamic>?,
      deviceAction: json['device_action'] as Map<String, dynamic>?,
      status: json['status'] as String?,
      options: (json['options'] as List<dynamic>?)?.cast<String>(),
      requiresConfirmation: json['requires_confirmation'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'content': content,
      'sender': sender,
      'emotion': emotion,
      'intent': intent,
      'action_type': actionType,
      'action_target': actionTarget,
      'action_data': actionData,
      'device_action': deviceAction,
      'status': status,
      'options': options,
      'requires_confirmation': requiresConfirmation,
    };
  }

  bool get needsConfirmation => requiresConfirmation || status == 'need_clarification';
  bool get hasOptions => options != null && options!.isNotEmpty;
  bool get hasDeviceAction => deviceAction != null && deviceAction!['success'] == true;
  String get deviceActionType => deviceAction?['type'] as String? ?? deviceAction?['action'] as String? ?? '';
}

class UserMessage extends Message {
  UserMessage({
    required String content,
  }) : super(
          content: content,
          sender: 'user',
          emotion: 'neutral',
          intent: 'user_input',
        );
}
