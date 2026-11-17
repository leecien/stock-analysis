import 'package:material_ui/material_ui.dart';

import '../models.dart';
import '../state.dart';
import '../widgets.dart';
import 'alerts_page.dart';
import 'settings_page.dart';

/// 每個分頁共用的 AppBar 按鈕：警示、設定
List<Widget> commonActions(BuildContext context) {
  final st = AppScope.of(context);
  final n = st.latest?.alerts.where((a) => a.level != 'info').length ?? 0;
  return [
    IconButton(
      tooltip: '警示',
      icon: Badge(isLabelVisible: n > 0, label: Text('$n'), child: const Icon(Icons.notifications_outlined)),
      onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const AlertsPage())),
    ),
    IconButton(
      tooltip: '設定',
      icon: const Icon(Icons.settings_outlined),
      onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsPage())),
    ),
  ];
}

/// 等資料載入完成才顯示內容；處理載入中、錯誤
class LatestBuilder extends StatelessWidget {
  final Widget Function(BuildContext, Latest) builder;
  const LatestBuilder({super.key, required this.builder});
  @override
  Widget build(BuildContext context) {
    final st = AppScope.of(context);
    final l = st.latest;
    if (l == null) {
      if (st.loading) return const Center(child: CircularProgressIndicator());
      return MessageView(
        icon: Icons.cloud_off,
        title: '無法載入資料',
        message: st.error,
        action: Wrap(spacing: 8, children: [
          FilledButton(onPressed: st.refresh, child: const Text('重試')),
          OutlinedButton(
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsPage())),
            child: const Text('檢查設定'),
          ),
        ]),
      );
    }
    return RefreshIndicator(onRefresh: st.refresh, child: builder(context, l));
  }
}

/// 示範資料 / 模擬 AI 提示
class ModeBanner extends StatelessWidget {
  final Latest l;
  const ModeBanner(this.l, {super.key});
  @override
  Widget build(BuildContext context) {
    final st = AppScope.of(context);
    final msgs = <String>[
      if (st.settings.source == DataSource.demo) '目前顯示內建示範資料。到「設定」連接 GitHub 後會顯示真實分析',
      if (st.settings.source != DataSource.demo && (l.demoPrices || l.demoNews)) '後端目前使用示範的股價或新聞',
      if (st.settings.source != DataSource.demo && l.isMockAi) '尚未接上 AI 金鑰，目前是規則式（模擬 AI）分析',
      if (st.warning != null) st.warning!,
    ];
    if (msgs.isEmpty) return const SizedBox.shrink();
    return Card(
      color: Theme.of(context).colorScheme.tertiaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(children: [
          const Icon(Icons.info_outline, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(msgs.join('\n'), style: const TextStyle(fontSize: 13))),
        ]),
      ),
    );
  }
}
