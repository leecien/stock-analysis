import 'package:material_ui/material_ui.dart';

import 'notifications.dart';
import 'pages/history_page.dart';
import 'pages/home_page.dart';
import 'pages/news_page.dart';
import 'pages/themes_page.dart';
import 'pages/watchlist_page.dart';
import 'state.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final state = AppState();
  runApp(AppScope(state: state, child: const StockApp()));
  await state.init();
  try {
    await initNotifications();
    await scheduleBackgroundCheck(state.settings);
  } catch (_) {
    // 通知功能失敗不影響主程式
  }
}

class StockApp extends StatelessWidget {
  const StockApp({super.key});
  @override
  Widget build(BuildContext context) {
    ThemeData theme(Brightness b) => ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1F5FAD), brightness: b),
          useMaterial3: true,
          cardTheme: const CardThemeData(margin: EdgeInsets.symmetric(horizontal: 12, vertical: 6)),
        );
    return MaterialApp(
      title: '股票 AI 分析',
      debugShowCheckedModeBanner: false,
      theme: theme(Brightness.light),
      darkTheme: theme(Brightness.dark),
      home: const HomeShell(),
    );
  }
}

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _tab = 0;
  static const _pages = [HomePage(), NewsPage(), ThemesPage(), WatchlistPage(), HistoryPage()];

  @override
  Widget build(BuildContext context) => Scaffold(
        body: IndexedStack(index: _tab, children: _pages),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _tab,
          onDestinationSelected: (i) => setState(() => _tab = i),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.dashboard_outlined), selectedIcon: Icon(Icons.dashboard), label: '總覽'),
            NavigationDestination(icon: Icon(Icons.local_fire_department_outlined), selectedIcon: Icon(Icons.local_fire_department), label: '熱門'),
            NavigationDestination(icon: Icon(Icons.category_outlined), selectedIcon: Icon(Icons.category), label: '產業'),
            NavigationDestination(icon: Icon(Icons.star_outline), selectedIcon: Icon(Icons.star), label: '自選'),
            NavigationDestination(icon: Icon(Icons.history_edu_outlined), selectedIcon: Icon(Icons.history_edu), label: '歷史'),
          ],
        ),
      );
}
