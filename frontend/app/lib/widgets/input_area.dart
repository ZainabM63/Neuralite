import 'package:flutter/material.dart';

class InputArea extends StatefulWidget {
  final TextEditingController textController;
  final FocusNode? focusNode;
  final VoidCallback onSend;
  final VoidCallback? onVoiceStart;
  final VoidCallback? onVoiceStop;
  final bool isLoading;
  final bool isListening;

  const InputArea({
    super.key,
    required this.textController,
    this.focusNode,
    required this.onSend,
    this.onVoiceStart,
    this.onVoiceStop,
    this.isLoading = false,
    this.isListening = false,
  });

  @override
  State<InputArea> createState() => _InputAreaState();
}

class _InputAreaState extends State<InputArea> with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        left: 16.0,
        right: 16.0,
        top: 8.0,
        bottom: MediaQuery.of(context).padding.bottom + 8.0,
      ),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 4.0,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: IntrinsicHeight(
              child: TextField(
                controller: widget.textController,
                focusNode: widget.focusNode,
                maxLines: null,
                minLines: 1,
                expands: true,
                textAlignVertical: TextAlignVertical.center,
                decoration: InputDecoration(
                  hintText: widget.isListening ? 'Listening...' : 'Type your message...',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(20.0),
                    borderSide: BorderSide(color: Colors.grey[300]!),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(20.0),
                    borderSide: BorderSide(color: Colors.grey[300]!),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(20.0),
                    borderSide: BorderSide(
                      color: widget.isListening ? Colors.red : Colors.blue,
                    ),
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 16.0,
                    vertical: 12.0,
                  ),
                ),
                onSubmitted: (text) {
                  if (text.isNotEmpty && !widget.isLoading) {
                    widget.onSend();
                  }
                },
                enabled: !widget.isLoading && !widget.isListening,
              ),
            ),
          ),
          const SizedBox(width: 8.0),
          if (widget.onVoiceStart != null || widget.onVoiceStop != null)
            AnimatedBuilder(
              animation: _pulseController,
              builder: (context, child) {
                return Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: widget.isListening
                        ? Colors.red.withOpacity(0.1 + (_pulseController.value * 0.2))
                        : Colors.transparent,
                  ),
                  child: IconButton(
                    icon: Icon(
                      widget.isListening ? Icons.stop : Icons.mic,
                      color: widget.isListening ? Colors.red : Colors.blue,
                    ),
                    onPressed: widget.isLoading
                        ? null
                        : () {
                            if (widget.isListening) {
                              widget.onVoiceStop?.call();
                            } else {
                              widget.onVoiceStart?.call();
                            }
                          },
                    tooltip: widget.isListening ? 'Stop Listening' : 'Voice Input',
                  ),
                );
              },
            ),
          const SizedBox(width: 4.0),
          FloatingActionButton(
            onPressed: widget.isLoading || widget.isListening
                ? null
                : () {
                    if (widget.textController.text.isNotEmpty) {
                      widget.onSend();
                    }
                  },
            backgroundColor: widget.isLoading || widget.isListening
                ? Colors.grey[400]
                : Colors.blue,
            disabledElevation: 0,
            elevation: 2.0,
            mini: true,
            child: widget.isLoading
                ? const SizedBox(
                    width: 20.0,
                    height: 20.0,
                    child: CircularProgressIndicator(
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      strokeWidth: 2.0,
                    ),
                  )
                : const Icon(Icons.send, size: 20.0),
          ),
        ],
      ),
    );
  }
}
