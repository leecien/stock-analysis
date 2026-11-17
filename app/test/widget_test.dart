import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:stock_ai/main.dart';
import 'package:stock_ai/models.dart';
import 'package:stock_ai/pages/accuracy_page.dart';
import 'package:stock_ai/pages/alerts_page.dart';
import 'package:stock_ai/pages/deep_page.dart';
import 'package:stock_ai/pages/history_page.dart';
import 'package:stock_ai/pages/news_page.dart';
import 'package:stock_ai/pages/settings_page.dart';
import 'package:stock_ai/pages/themes_page.dart';
import 'package:stock_ai/state.dart';

HistoryData _demoHistory() =>
    HistoryData.fromJson(jm(jsonDecode(File('assets/demo/history.json').readAsStringSync())));

void main() {
  test('示範資料可以完整解析', () {
    final latest = Latest.fromJson(jm(jsonDecode(File('assets/demo/latest.json').readAsStringSync())));
    expect(latest.us.indices, isNotEmpty);
    expect(latest.tw.indices, isNotEmpty);
    expect(latest.themes.length, greaterThan(10));
    expect(latest.watchlist, isNotEmpty);
    expect(latest.news, isNotEmpty);
    expect(latest.deep, isNotNull);
    final history = _demoHistory();
    expect(history.events.length, greaterThan(50));
    expect(history.events.any((e) => e.title.contains('雷曼')), isTrue);
  });

  testWidgets('首頁顯示大盤，切換各分頁不會出錯', (tester) async {
    tester.view.physicalSize = const Size(1080, 2340);
    tester.view.devicePixelRatio = 2.75;
    addTearDown(tester.view.reset);
    SharedPreferences.setMockInitialValues({});
    final state = AppState();
    await tester.pumpWidget(AppScope(state: state, child: const StockApp()));
    await tester.runAsync(state.init);
    state.history = _demoHistory(); // 測試環境不經過 rootBundle 載入大檔
    await tester.pumpAndSettle();

    expect(find.text('股票 AI 分析'), findsOneWidget);
    expect(find.text('美股'), findsWidgets);
    await tester.scrollUntilVisible(find.text('台股'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('台股'), findsWidgets);

    for (final label in ['熱門', '產業', '自選', '總覽']) {
      await tester.tap(find.text(label).last);
      await tester.pumpAndSettle();
    }

    // 自選股詳細頁
    await tester.tap(find.text('自選'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('台積電').first);
    await tester.pumpAndSettle();
    expect(find.text('AI 判斷'), findsOneWidget);
  });

  testWidgets('歷史事件頁', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final state = AppState();
    await tester.runAsync(state.init);
    state.history = _demoHistory();
    await tester.pumpWidget(AppScope(state: state, child: const MaterialApp(home: HistoryPage())));
    await tester.pumpAndSettle();
    expect(find.text('20 年歷史事件'), findsOneWidget);
    await tester.tap(find.text('各類統計'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('修正波段'));
    await tester.pumpAndSettle();
  });

  testWidgets('所有詳細頁都能正常顯示（手機尺寸）', (tester) async {
    tester.view.physicalSize = const Size(1080, 2340);
    tester.view.devicePixelRatio = 2.75;
    addTearDown(tester.view.reset);
    SharedPreferences.setMockInitialValues({});
    final state = AppState();
    await tester.runAsync(state.init);
    state.history = _demoHistory();
    final l = state.latest!;
    final h = state.history!;
    final pages = <Widget>[
      ThemeDetailPage(l.themes.first),
      NewsDetailPage(l.news.firstWhere((n) => l.analogFor(n.id) != null, orElse: () => l.news.first)),
      KeywordNewsPage(l.keywords.first.keyword),
      const DeepPage(),
      const AccuracyPage(),
      const AlertsPage(),
      const SettingsPage(),
      EventDetailPage(h.events.firstWhere((e) => e.source == 'seed'), h.forwardDays),
    ];
    for (final p in pages) {
      await tester.pumpWidget(AppScope(state: state, child: MaterialApp(home: p)));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull, reason: p.runtimeType.toString());
    }
  });
}
