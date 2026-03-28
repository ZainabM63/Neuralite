import 'package:flutter/material.dart';
import '../models/message.dart';

class MessageBubble extends StatelessWidget {
  final Message message;
  final Function(String)? onOptionSelected;
  final VoidCallback? onConfirm;
  final VoidCallback? onCancel;

  const MessageBubble({
    super.key,
    required this.message,
    this.onOptionSelected,
    this.onConfirm,
    this.onCancel,
  });

  @override
  Widget build(BuildContext context) {
    final bool isUser = message.sender == 'user';
    
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 4.0),
          child: Column(
            crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
            decoration: BoxDecoration(
              color: isUser ? Colors.blue[600] : Colors.grey[300],
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(12.0),
                topRight: const Radius.circular(12.0),
                bottomLeft: Radius.circular(isUser ? 12.0 : 0.0),
                bottomRight: Radius.circular(isUser ? 0.0 : 12.0),
              ),
            ),
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.75,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  message.content,
                  style: TextStyle(
                    color: isUser ? Colors.white : Colors.black87,
                    fontSize: 16.0,
                  ),
                ),
                const SizedBox(height: 4.0),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      _getEmotionIcon(message.emotion),
                      size: 12.0,
                      color: isUser ? Colors.white70 : Colors.black54,
                    ),
                    const SizedBox(width: 4.0),
                    Text(
                      message.emotion,
                      style: TextStyle(
                        color: isUser ? Colors.white70 : Colors.black54,
                        fontSize: 10.0,
                      ),
                    ),
                    const SizedBox(width: 8.0),
                    Icon(
                      _getIntentIcon(message.intent),
                      size: 12.0,
                      color: isUser ? Colors.white70 : Colors.black54,
                    ),
                    const SizedBox(width: 4.0),
                    Flexible(
                      child: Text(
                        message.intent,
                        style: TextStyle(
                          color: isUser ? Colors.white70 : Colors.black54,
                          fontSize: 10.0,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          if (message.hasOptions) ...[
            const SizedBox(height: 8.0),
            _buildOptions(context, isUser),
          ],
          if (message.requiresConfirmation && !message.hasOptions && !isUser) ...[
            const SizedBox(height: 8.0),
            _buildConfirmationButtons(context),
          ],
        ],
      ),
    );
  }

  Widget _buildOptions(BuildContext context, bool isUser) {
    return Wrap(
      spacing: 8.0,
      runSpacing: 8.0,
      alignment: isUser ? WrapAlignment.end : WrapAlignment.start,
      children: message.options!.map((option) {
        final isPrimary = option.toLowerCase().contains('yes') ||
            option.toLowerCase().contains('confirm') ||
            option.toLowerCase().contains('send') ||
            option.toLowerCase().contains('call') ||
            option.toLowerCase().contains('open');
        
        return InkWell(
          onTap: () => onOptionSelected?.call(option),
          borderRadius: BorderRadius.circular(16.0),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 6.0),
            decoration: BoxDecoration(
              color: isPrimary ? Colors.blue[600] : Colors.grey[200],
              borderRadius: BorderRadius.circular(16.0),
              border: Border.all(
                color: isPrimary ? Colors.blue[600]! : Colors.grey[400]!,
              ),
            ),
            child: Text(
              option,
              style: TextStyle(
                color: isPrimary ? Colors.white : Colors.black87,
                fontSize: 12.0,
              ),
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildConfirmationButtons(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        ElevatedButton.icon(
          onPressed: onConfirm,
          icon: const Icon(Icons.check, size: 16.0),
          label: const Text('Yes'),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.green,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
          ),
        ),
        const SizedBox(width: 8.0),
        ElevatedButton.icon(
          onPressed: onCancel,
          icon: const Icon(Icons.close, size: 16.0),
          label: const Text('No'),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.red,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
          ),
        ),
      ],
    );
  }

  IconData _getEmotionIcon(String emotion) {
    switch (emotion.toLowerCase()) {
      case 'happy':
        return Icons.sentiment_satisfied_alt;
      case 'sad':
        return Icons.sentiment_dissatisfied;
      case 'stressed':
        return Icons.psychology;
      case 'angry':
        return Icons.sentiment_very_dissatisfied;
      default:
        return Icons.sentiment_neutral;
    }
  }

  IconData _getIntentIcon(String intent) {
    switch (intent.toLowerCase()) {
      case 'send_message':
        return Icons.message;
      case 'make_call':
        return Icons.phone;
      case 'open_app':
        return Icons.apps;
      case 'search_web':
        return Icons.search;
      case 'set_reminder':
        return Icons.alarm;
      case 'set_alarm':
        return Icons.alarm;
      case 'send_email':
        return Icons.email;
      default:
        return Icons.chat_bubble;
    }
  }
}
