// This is a basic Flutter widget test.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/main.dart';

void main() {
  testWidgets('Neura app loads correctly', (WidgetTester tester) async {
    await tester.pumpWidget(const NeuraApp());
    expect(find.byType(TextField), findsOneWidget);
  });
}
