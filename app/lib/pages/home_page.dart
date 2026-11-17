import 'package:material_ui/material_ui.dart';

import '../models.dart';
import '../widgets.dart';
import 'accuracy_page.dart';
import 'alerts_page.dart';
import 'common.dart';
import 'deep_page.dart';
import 'news_page.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('股票 AI 分析'), actions: commonActions(context)),
        body: LatestBuilder(builder: (context, l) {
          return ListView(padding: const EdgeInsets.only(bottom: 24), children: [
            ModeBanner(l),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Text(
                '更新：${l.generatedAtTw}（${timeAgo(l.generatedAt)}）· ${l.session} · ${providerZh[l.fastAi] ?? l.fastAi}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
            if (l.headline.isNotEmpty)
              Card(
                child: ListTile(
                  leading: const Icon(Icons.campaign_outlined),
                  title: const Text('焦點', style: TextStyle(fontSize: 12)),
                  subtitle: Text(l.headline, style: Theme.of(context).textTheme.titleMedium),
                ),
              ),
            MarketCard(l.us),
            MarketCard(l.tw),
            if (l.macro.isNotEmpty) ...[
              const SectionTitle('總經指標'),
              SizedBox(
                height: 64,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  children: [
                    for (final m in l.macro)
                      Card(
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(m.name, style: const TextStyle(fontSize: 12)),
                              Row(children: [
                                Text(fmtNum(m.close)),
                                const SizedBox(width: 6),
                                ChangeText(m.changePct, fontSize: 12),
                              ]),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
            if (l.keywords.isNotEmpty) ...[
              const SectionTitle('熱門關鍵字（24 小時）'),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Wrap(spacing: 6, runSpacing: 6, children: [
                  for (final k in l.keywords.take(10))
                    ActionChip(
                      label: Text('${k.keyword} ${k.count24h}${k.ratio >= 2 ? ' 🔥' : ''}'),
                      onPressed: () => Navigator.push(
                          context, MaterialPageRoute(builder: (_) => KeywordNewsPage(k.keyword))),
                    ),
                ]),
              ),
            ],
            if (l.alerts.isNotEmpty) ...[
              SectionTitle('最新警示',
                  trailing: TextButton(
                    onPressed: () =>
                        Navigator.push(context, MaterialPageRoute(builder: (_) => const AlertsPage())),
                    child: const Text('全部'),
                  )),
              for (final a in l.alerts.take(3)) AlertTile(a),
            ],
            const SectionTitle('AI 深度分析'),
            Card(
              child: ListTile(
                leading: const Icon(Icons.psychology_outlined),
                title: Text(l.deep == null ? '尚未產生' : '多家 AI 觀點比較'),
                subtitle: Text(l.deep == null
                    ? '每天 08:00、22:00 自動執行'
                    : '${l.deep!.views.map((v) => providerZh[v.provider] ?? v.provider).join('、')} · ${timeAgo(l.deep!.generatedAt)}'),
                trailing: const Icon(Icons.chevron_right),
                onTap: l.deep == null
                    ? null
                    : () => Navigator.push(context, MaterialPageRoute(builder: (_) => const DeepPage())),
              ),
            ),
            Card(
              child: ListTile(
                leading: const Icon(Icons.fact_check_outlined),
                title: const Text('AI 預測準確率與花費'),
                subtitle: Text(_accuracyLine(l)),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const AccuracyPage())),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text(l.disclaimer,
                  style: Theme.of(context).textTheme.bodySmall, textAlign: TextAlign.center),
            ),
          ]);
        }),
      );

  String _accuracyLine(Latest l) {
    final parts = <String>[
      for (final a in l.accuracy)
        '${providerZh[a.name] ?? a.name} ${a.accuracy == null ? '累積中' : '${(a.accuracy! * 100).toStringAsFixed(0)}%'}',
    ];
    parts.add('本月花費 NT\$${l.budget.spentTwd.toStringAsFixed(0)} / ${l.budget.limitTwd.toStringAsFixed(0)}');
    return parts.join(' · ');
  }
}

class MarketCard extends StatelessWidget {
  final MarketView m;
  const MarketCard(this.m, {super.key});
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text(m.name, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(width: 10),
            StanceChip(m.stance),
            const Spacer(),
            Text('信心 ${m.confidence}', style: TextStyle(color: cs.onSurfaceVariant, fontSize: 12)),
          ]),
          const SizedBox(height: 10),
          for (final s in m.indices)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(children: [
                SizedBox(width: 86, child: Text(s.name, style: const TextStyle(fontSize: 13))),
                SizedBox(width: 76, child: Text(fmtNum(s.close), textAlign: TextAlign.right)),
                SizedBox(
                    width: 72,
                    child: Align(alignment: Alignment.centerRight, child: ChangeText(s.changePct, fontSize: 13))),
                const SizedBox(width: 10),
                Expanded(
                    child: LineChart(
                        s.series.length > 20 ? s.series.sublist(s.series.length - 20) : s.series,
                        height: 22)),
              ]),
            ),
          if (m.summary.isNotEmpty) ...[const SizedBox(height: 8), Text(m.summary)],
          if (m.drivers.isNotEmpty || m.risks.isNotEmpty)
            Theme(
              data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
              child: ExpansionTile(
                tilePadding: EdgeInsets.zero,
                childrenPadding: EdgeInsets.zero,
                title: const Text('利多與風險', style: TextStyle(fontSize: 14)),
                expandedCrossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (m.drivers.isNotEmpty) Bullets(m.drivers, icon: Icons.trending_up, color: upColor(context)),
                  if (m.risks.isNotEmpty) Bullets(m.risks, icon: Icons.trending_down, color: downColor(context)),
                ],
              ),
            ),
          if (m.consensus != null && m.consensus!.votes.length > 1) ...[
            const SizedBox(height: 6),
            Wrap(spacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
              Text('多家 AI：', style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant)),
              for (final e in m.consensus!.votes.entries)
                StanceChip(e.value, label: '${providerZh[e.key] ?? e.key} ${stanceZh[e.value]}', small: true),
            ]),
          ],
        ]),
      ),
    );
  }
}
