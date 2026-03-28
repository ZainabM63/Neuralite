import 'package:flutter/material.dart';
import 'screens/chat_screen.dart';

void main() {
  runApp(const NeuraApp());
}

class NeuraApp extends StatelessWidget {
  const NeuraApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Neura AI Assistant',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: Colors.grey[100],
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: Colors.grey[900],
      ),
      themeMode: ThemeMode.light,
      home: const ChatScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}