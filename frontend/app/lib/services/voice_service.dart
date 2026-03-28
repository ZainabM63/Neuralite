import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';

enum VoiceServiceState { idle, listening, speaking, error }

class VoiceService {
  static final VoiceService _instance = VoiceService._internal();
  factory VoiceService() => _instance;
  VoiceService._internal();

  final SpeechToText _speech = SpeechToText();
  final FlutterTts _tts = FlutterTts();
  
  bool _isInitialized = false;
  bool _isListening = false;
  bool _isSpeaking = false;
  bool _isMaleVoice = true;
  
  VoiceServiceState _state = VoiceServiceState.idle;
  String _lastRecognized = '';
  String? _errorMessage;
  
  Function(String)? onResult;
  Function(VoiceServiceState)? onStateChange;
  Function(String)? onError;

  bool get isInitialized => _isInitialized;
  bool get isListening => _isListening;
  bool get isSpeaking => _isSpeaking;
  VoiceServiceState get state => _state;
  String get lastRecognized => _lastRecognized;

  Future<bool> initialize() async {
    if (_isInitialized) return true;
    
    try {
      _isInitialized = await _speech.initialize(
        onStatus: _onSpeechStatus,
        onError: (error) => _onSpeechError(error.errorMsg),
        debugLogging: kDebugMode,
      );
      
      await _tts.setLanguage('en-US');
      await _tts.setSpeechRate(0.5);
      await _tts.setVolume(1.0);
      await setVoiceGender(_isMaleVoice);
      
      _tts.setCompletionHandler(() {
        _state = VoiceServiceState.idle;
        _isSpeaking = false;
        onStateChange?.call(_state);
      });
      
      _tts.setErrorHandler((message) {
        _state = VoiceServiceState.error;
        _errorMessage = message;
        _isSpeaking = false;
        onStateChange?.call(_state);
        onError?.call(message);
      });
      
      return _isInitialized;
    } catch (e) {
      _isInitialized = false;
      _errorMessage = e.toString();
      return false;
    }
  }

  String _currentLocale = 'en_US';
  
  Future<bool> startListening({String? localeId}) async {
    if (!_isInitialized) {
      final success = await initialize();
      if (!success) {
        onError?.call('Voice service not available');
        return false;
      }
    }
    
    if (_isListening) return true;
    
    _state = VoiceServiceState.listening;
    _isListening = true;
    _lastRecognized = '';
    onStateChange?.call(_state);
    
    final selectedLocale = localeId ?? _currentLocale;
    
    try {
      await _speech.listen(
        onResult: (result) {
          _lastRecognized = result.recognizedWords;
          if (result.finalResult) {
            _isListening = false;
            _state = VoiceServiceState.idle;
            onStateChange?.call(_state);
            onResult?.call(_lastRecognized);
          }
        },
        listenFor: const Duration(seconds: 60),
        pauseFor: const Duration(seconds: 5),
        partialResults: true,
        localeId: selectedLocale,
        cancelOnError: true,
      );
      return true;
    } catch (e) {
      _isListening = false;
      _state = VoiceServiceState.error;
      _errorMessage = e.toString();
      onStateChange?.call(_state);
      onError?.call(e.toString());
      return false;
    }
  }

  Future<void> stopListening() async {
    if (!_isListening) return;
    
    await _speech.stop();
    _isListening = false;
    _state = VoiceServiceState.idle;
    onStateChange?.call(_state);
  }

  Future<void> speak(String text) async {
    if (_isSpeaking) {
      await stopSpeaking();
    }
    
    if (!_isInitialized) {
      await initialize();
    }
    
    _state = VoiceServiceState.speaking;
    _isSpeaking = true;
    onStateChange?.call(_state);
    
    try {
      await _tts.speak(text);
    } catch (e) {
      _isSpeaking = false;
      _state = VoiceServiceState.error;
      _errorMessage = e.toString();
      onStateChange?.call(_state);
      onError?.call(e.toString());
    }
  }

  Future<void> stopSpeaking() async {
    if (!_isSpeaking) return;
    
    await _tts.stop();
    _isSpeaking = false;
    _state = VoiceServiceState.idle;
    onStateChange?.call(_state);
  }

  void _onSpeechStatus(String status) {
    if (status == 'done' || status == 'notListening') {
      _isListening = false;
      _state = VoiceServiceState.idle;
      onStateChange?.call(_state);
    }
  }

  void _onSpeechError(String error) {
    _isListening = false;
    _state = VoiceServiceState.error;
    _errorMessage = error;
    _isSpeaking = false;
    onStateChange?.call(_state);
    onError?.call(error);
  }

  Future<List<LocaleName>> getLocales() async {
    return await _speech.locales();
  }

  Future<void> setLocale(String localeId) async {
    _currentLocale = localeId;
    if (localeId == 'ur_PK' || localeId == 'ur') {
      try {
        await _tts.setLanguage('ur-PK');
      } catch (e) {
        await _tts.setLanguage('en-US');
      }
    } else {
      await _tts.setLanguage('en-US');
    }
  }

  Future<void> setSpeechRate(double rate) async {
    await _tts.setSpeechRate(rate.clamp(0.1, 1.0));
  }
  
  Future<void> setLanguage(String languageCode) async {
    if (languageCode == 'urdu' || languageCode == 'roman_urdu') {
      try {
        await _tts.setLanguage('ur-PK');
        _currentLocale = 'ur_PK';
      } catch (e) {
        await _tts.setLanguage('en-US');
      }
    } else {
      await _tts.setLanguage('en-US');
      _currentLocale = 'en_US';
    }
  }
  
  Future<void> setVoiceGender(bool isMale) async {
    _isMaleVoice = isMale;
    if (isMale) {
      await _tts.setPitch(1.0);
    } else {
      await _tts.setPitch(0.85);
    }
  }
  
  bool get isMaleVoice => _isMaleVoice;
  
  double _currentSpeechRate = 0.8;
  double get currentSpeechRate => _currentSpeechRate;

  Future<void> dispose() async {
    await stopListening();
    await stopSpeaking();
  }
}
