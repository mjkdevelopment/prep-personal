// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:prep_personal/src/app.dart';
import 'package:prep_personal/src/core/theme/app_theme.dart';
import 'package:prep_personal/src/state/app_controller.dart';

void main() {
  testWidgets('renders prep personal home shell', (tester) async {
    final controller = AppController.preview();

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: AppShell(controller: controller),
      ),
    );

    expect(find.text('Disponible para hoy'), findsOneWidget);
    expect(find.text('Transacciones'), findsOneWidget);
    expect(find.text('Plan'), findsOneWidget);
  });
}
