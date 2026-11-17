import 'package:material_ui/material_ui.dart';

import '../state.dart';
import '../widgets.dart';

class AccuracyPage extends StatelessWidget {
  const AccuracyPage({super.key});
  @override
  Widget build(BuildContext context) {
    final l = AppScope.of(context).latest;
    if (l == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final b = l.budget;
    return Scaffold(
      appBar: AppBar(title: const Text('準確率與花費')),
      body: ListView(padding: const EdgeInsets.only(bottom: 24), children: [
        const SectionTitle('AI 預測準確率'),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 16),
          child: Text('每次深度分析都會預測 5 個交易日後的方向（漲 / 跌 / 持平 ±1%），到期後自動比對實際結果。',
              style: TextStyle(fontSize: 12, color: Colors.grey)),
        ),
        for (final a in l.accuracy)
          Card(
            child: ListTile(
              leading: CircleAvatar(child: Text((providerZh[a.name] ?? a.name).substring(0, 1))),
              title: Text(providerZh[a.name] ?? a.name),
              subtitle: Text('答對 ${a.correct} · 答錯 ${a.wrong} · 等待結果 ${a.pending}'),
              trailing: Text(
                a.accuracy == null ? '累積中' : '${(a.accuracy! * 100).toStringAsFixed(0)}%',
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),
          ),
        if (l.accuracy.isEmpty)
          const Padding(padding: EdgeInsets.all(16), child: Text('還沒有預測紀錄', style: TextStyle(color: Colors.grey))),
        if (l.recentPredictions.isNotEmpty) ...[
          const SectionTitle('最近的預測結果'),
          for (final p in l.recentPredictions)
            ListTile(
              dense: true,
              leading: Icon(p.status == 'correct' ? Icons.check_circle : Icons.cancel,
                  color: p.status == 'correct' ? Colors.green : Colors.red),
              title: Text('${symName(p.target)}：預測${directionZh[p.direction]}，實際${directionZh[p.actual] ?? '-'}'),
              subtitle: Text('${providerZh[p.provider] ?? p.provider} · ${p.baseDate} → ${p.evalDate}'),
              trailing: ChangeText(p.actualPct),
            ),
        ],
        const SectionTitle('本月 AI 花費'),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('NT\$${b.spentTwd.toStringAsFixed(1)} / NT\$${b.limitTwd.toStringAsFixed(0)}',
                  style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 8),
              LinearProgressIndicator(
                value: b.ratio.clamp(0, 1).toDouble(),
                minHeight: 8,
                borderRadius: BorderRadius.circular(4),
                color: b.ratio > 0.85 ? Colors.red : null,
              ),
              const SizedBox(height: 8),
              Text('${b.month} · 呼叫 AI ${b.calls} 次。超過 85% 會暫停深度分析，達 100% 全部改用模擬 AI。',
                  style: const TextStyle(fontSize: 12, color: Colors.grey)),
            ]),
          ),
        ),
      ]),
    );
  }
}
