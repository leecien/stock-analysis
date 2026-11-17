import 'package:material_ui/material_ui.dart';

import '../models.dart';
import '../state.dart';
import '../widgets.dart';

/// 深度分析：多家 AI 的觀點並排比較
class DeepPage extends StatelessWidget {
  const DeepPage({super.key});
  @override
  Widget build(BuildContext context) {
    final d = AppScope.of(context).latest?.deep;
    if (d == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('深度分析')),
        body: const MessageView(icon: Icons.psychology_outlined, title: '尚未產生深度分析'),
      );
    }
    return DefaultTabController(
      length: d.views.length,
      child: Scaffold(
        appBar: AppBar(
          title: Text('深度分析 · ${timeAgo(d.generatedAt)}'),
          bottom: TabBar(
            isScrollable: d.views.length > 3,
            tabs: [for (final v in d.views) Tab(text: providerZh[v.provider] ?? v.provider)],
          ),
        ),
        body: TabBarView(children: [for (final v in d.views) _View(v, d)]),
      ),
    );
  }
}

class _View extends StatelessWidget {
  final DeepView v;
  final DeepReport d;
  const _View(this.v, this.d);
  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.only(bottom: 24), children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          child: Text('模型：${v.model}', style: const TextStyle(fontSize: 12, color: Colors.grey)),
        ),
        if (v.headline.isNotEmpty)
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(v.headline, style: Theme.of(context).textTheme.titleMedium),
          ),
        for (final m in [v.us, v.tw].whereType<MarketView>())
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Text(m == v.us ? '美股' : '台股', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(width: 8),
                  StanceChip(m.stance),
                  const Spacer(),
                  Text('信心 ${m.confidence}', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                ]),
                const SizedBox(height: 8),
                Text(m.summary),
                if (m.drivers.isNotEmpty) ...[const SizedBox(height: 6), Bullets(m.drivers, icon: Icons.trending_up, color: upColor(context))],
                if (m.risks.isNotEmpty) Bullets(m.risks, icon: Icons.trending_down, color: downColor(context)),
              ]),
            ),
          ),
        if (v.shortTerm.isNotEmpty || v.mediumTerm.isNotEmpty) ...[
          const SectionTitle('展望'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('短期（1~5 個交易日）', style: TextStyle(fontWeight: FontWeight.w600)),
                Text(v.shortTerm),
                const SizedBox(height: 10),
                const Text('中期（1~3 個月）', style: TextStyle(fontWeight: FontWeight.w600)),
                Text(v.mediumTerm),
              ]),
            ),
          ),
        ],
        if (v.historicalView.isNotEmpty) ...[
          const SectionTitle('歷史對照'),
          Padding(padding: const EdgeInsets.symmetric(horizontal: 16), child: Text(v.historicalView)),
        ],
        if (v.predictions.isNotEmpty) ...[
          const SectionTitle('預測（到期後自動驗證）'),
          Card(
            child: Column(children: [
              for (final p in v.predictions)
                ListTile(
                  dense: true,
                  title: Text('${symName(p.target)}　${p.horizon} 個交易日'),
                  subtitle: p.rationale.isEmpty ? null : Text(p.rationale, maxLines: 2, overflow: TextOverflow.ellipsis),
                  trailing: StanceChip(
                    p.direction == 'up' ? 'bullish' : p.direction == 'down' ? 'bearish' : 'neutral',
                    label: '${directionZh[p.direction]} ${p.confidence}',
                    small: true,
                  ),
                ),
            ]),
          ),
        ],
        if (d.views.length > 1) ...[
          const SectionTitle('各家 AI 意見一致度'),
          Card(
            child: Column(children: [
              for (final e in d.consensus.entries)
                ListTile(
                  dense: true,
                  title: Text(e.key == 'us' ? '美股' : e.key == 'tw' ? '台股' : e.key),
                  subtitle: Text(e.value.votes.entries.map((x) => '${providerZh[x.key] ?? x.key}：${stanceZh[x.value]}').join('　')),
                  trailing: Text('${(e.value.agreement * 100).toStringAsFixed(0)}% 一致'),
                ),
            ]),
          ),
        ],
      ]);
}
