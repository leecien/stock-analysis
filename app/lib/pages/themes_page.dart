import 'package:material_ui/material_ui.dart';

import '../models.dart';
import '../state.dart';
import '../widgets.dart';
import 'common.dart';
import 'news_page.dart';

class ThemesPage extends StatelessWidget {
  const ThemesPage({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('產業主題'), actions: commonActions(context)),
        body: LatestBuilder(
          builder: (context, l) => ListView(padding: const EdgeInsets.symmetric(vertical: 8), children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(16, 4, 16, 8),
              child: Text('依近 24 小時新聞數排序。情緒條：右邊偏正面、左邊偏負面。',
                  style: TextStyle(fontSize: 12, color: Colors.grey)),
            ),
            for (final t in l.themes) _ThemeTile(t),
          ]),
        ),
      );
}

class _ThemeTile extends StatelessWidget {
  final ThemeItem t;
  const _ThemeTile(this.t);
  @override
  Widget build(BuildContext context) {
    final avg = t.stocks.where((s) => s.changePct != null).map((s) => s.changePct!).toList();
    final avgChange = avg.isEmpty ? null : avg.reduce((a, b) => a + b) / avg.length;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ThemeDetailPage(t))),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Flexible(
                child: Text(t.name,
                    overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ),
              const SizedBox(width: 8),
              StanceChip(t.stance, small: true),
              const Spacer(),
              if (avgChange != null) ...[
                const Text('族群平均 ', style: TextStyle(fontSize: 12, color: Colors.grey)),
                ChangeText(avgChange, fontSize: 13),
              ],
            ]),
            const SizedBox(height: 8),
            Row(children: [
              Text('${t.news24h} 則新聞', style: const TextStyle(fontSize: 12, color: Colors.grey)),
              const SizedBox(width: 10),
              Expanded(child: SentimentBar(t.sentiment)),
              const SizedBox(width: 8),
              SizedBox(
                width: 40,
                child: Text(t.sentiment.toStringAsFixed(2),
                    textAlign: TextAlign.right, style: const TextStyle(fontSize: 12)),
              ),
            ]),
            if (t.reason.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(t.reason, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
            ],
          ]),
        ),
      ),
    );
  }
}

class ThemeDetailPage extends StatelessWidget {
  final ThemeItem t;
  const ThemeDetailPage(this.t, {super.key});
  @override
  Widget build(BuildContext context) {
    final l = AppScope.of(context).latest;
    final news = (l?.news ?? []).where((n) => n.themes.contains(t.id)).toList();
    final daily = t.sentimentDaily;
    return Scaffold(
      appBar: AppBar(title: Text(t.name)),
      body: ListView(padding: const EdgeInsets.only(bottom: 24), children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                StanceChip(t.stance),
                const SizedBox(width: 10),
                Expanded(child: Text('近 24 小時 ${t.news24h} 則新聞 · 情緒 ${t.sentiment.toStringAsFixed(2)}')),
              ]),
              if (t.reason.isNotEmpty) ...[const SizedBox(height: 10), Text(t.reason)],
              if (daily.whereType<double>().length >= 2) ...[
                const SizedBox(height: 14),
                const Text('近 7 天新聞情緒', style: TextStyle(fontSize: 12, color: Colors.grey)),
                const SizedBox(height: 6),
                LineChart(daily, height: 60, zeroLine: true, showLabels: true, leftLabel: '7 天前', rightLabel: '今天'),
              ],
            ]),
          ),
        ),
        const SectionTitle('漲跌的典型原因'),
        Padding(padding: const EdgeInsets.symmetric(horizontal: 16), child: Bullets(t.drivers)),
        const SectionTitle('相關個股'),
        Card(
          child: Column(children: [
            for (final s in t.stocks)
              ListTile(
                dense: true,
                title: Text(s.name),
                subtitle: Text('${s.symbol} · ${s.trend}'),
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text(fmtNum(s.close)),
                  const SizedBox(width: 12),
                  SizedBox(width: 68, child: Align(alignment: Alignment.centerRight, child: ChangeText(s.changePct))),
                ]),
              ),
            if (t.stocks.isEmpty) const ListTile(title: Text('沒有股價資料')),
          ]),
        ),
        const SectionTitle('監控的關鍵字'),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Wrap(spacing: 6, runSpacing: 6, children: [for (final k in t.keywords) Tag(k)]),
        ),
        SectionTitle('相關新聞（${news.length}）'),
        for (final n in news.take(20)) NewsTile(n),
        if (news.isEmpty)
          const Padding(padding: EdgeInsets.all(16), child: Text('近期沒有相關新聞', style: TextStyle(color: Colors.grey))),
      ]),
    );
  }
}
