import 'package:material_ui/material_ui.dart';

import '../models.dart';
import '../state.dart';
import '../widgets.dart';
import 'common.dart';
import 'news_page.dart';

class WatchlistPage extends StatelessWidget {
  const WatchlistPage({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('自選股'), actions: commonActions(context)),
        body: LatestBuilder(
          builder: (context, l) => ListView(padding: const EdgeInsets.symmetric(vertical: 8), children: [
            for (final w in l.watchlist) _WatchTile(w),
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('自選股清單在後端的 config/watchlist.yaml 設定',
                  textAlign: TextAlign.center, style: TextStyle(fontSize: 12, color: Colors.grey)),
            ),
          ]),
        ),
      );
}

class _WatchTile extends StatelessWidget {
  final WatchItem w;
  const _WatchTile(this.w);
  @override
  Widget build(BuildContext context) {
    final s = w.snap;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => StockDetailPage(w))),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(children: [
            Expanded(
              flex: 3,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(s.name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                const SizedBox(height: 2),
                Row(children: [
                  Text(s.symbol, style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  const SizedBox(width: 6),
                  StanceChip(w.stance, small: true),
                ]),
              ]),
            ),
            Expanded(flex: 2, child: LineChart(s.series, height: 32)),
            SizedBox(
              width: 86,
              child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Text(fmtNum(s.close), style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                ChangeText(s.changePct, fontSize: 13),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

class StockDetailPage extends StatefulWidget {
  final WatchItem w;
  const StockDetailPage(this.w, {super.key});
  @override
  State<StockDetailPage> createState() => _StockDetailPageState();
}

class _StockDetailPageState extends State<StockDetailPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => AppScope.read(context).loadHistory());
  }

  @override
  Widget build(BuildContext context) {
    final st = AppScope.of(context);
    final l = st.latest;
    final w = widget.w;
    final s = w.snap;
    final news = w.newsIds.map((id) => l?.newsById(id)).whereType<NewsItem>().toList();
    final moves = st.history?.stockMoves[s.symbol] ?? [];
    final preds = <(String, Prediction)>[
      for (final v in l?.deep?.views ?? <DeepView>[])
        for (final p in v.predictions)
          if (p.target == s.symbol) (v.provider, p),
    ];
    return Scaffold(
      appBar: AppBar(title: Text('${s.name} ${s.symbol}')),
      body: ListView(padding: const EdgeInsets.only(bottom: 24), children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Wrap(crossAxisAlignment: WrapCrossAlignment.end, spacing: 10, children: [
                Text(fmtNum(s.close), style: Theme.of(context).textTheme.headlineMedium),
                ChangeText(s.changePct, fontSize: 18),
              ]),
              Text('資料日期 ${s.date}', style: const TextStyle(color: Colors.grey, fontSize: 12)),
              const SizedBox(height: 12),
              LineChart(s.series,
                  height: 140,
                  showLabels: true,
                  leftLabel: s.seriesDates.isNotEmpty ? s.seriesDates.first : null,
                  rightLabel: s.seriesDates.isNotEmpty ? s.seriesDates.last : null),
              const SizedBox(height: 12),
              Wrap(spacing: 16, runSpacing: 8, children: [
                _kv('5 日', ChangeText(s.change5d, fontSize: 13)),
                _kv('20 日', ChangeText(s.change20d, fontSize: 13)),
                _kv('月線 MA20', Text(fmtNum(s.sma20))),
                _kv('季線 MA60', Text(fmtNum(s.sma60))),
                _kv('RSI(14)', Text(s.rsi?.toStringAsFixed(1) ?? '-')),
                _kv('MACD 柱', Text(s.macdHist?.toStringAsFixed(2) ?? '-')),
                _kv('技術面', Text(s.trend)),
              ]),
            ]),
          ),
        ),
        const SectionTitle('AI 判斷'),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              StanceChip(w.stance),
              if (w.reason.isNotEmpty) ...[const SizedBox(height: 8), Text(w.reason)],
              if (w.consensus != null && w.consensus!.votes.isNotEmpty) ...[
                const SizedBox(height: 10),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  for (final e in w.consensus!.votes.entries)
                    StanceChip(e.value, label: '${providerZh[e.key] ?? e.key} ${stanceZh[e.value]}', small: true),
                ]),
              ],
              for (final (provider, p) in preds) ...[
                const Divider(height: 20),
                Text('${providerZh[provider] ?? provider} 預測 ${p.horizon} 個交易日：${directionZh[p.direction]}（信心 ${p.confidence}）',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                if (p.rationale.isNotEmpty) Text(p.rationale, style: const TextStyle(fontSize: 13)),
              ],
            ]),
          ),
        ),
        SectionTitle('相關新聞（${news.length}）'),
        for (final n in news) NewsTile(n),
        if (news.isEmpty)
          const Padding(padding: EdgeInsets.symmetric(horizontal: 16), child: Text('近期沒有相關新聞', style: TextStyle(color: Colors.grey))),
        const SectionTitle('過去的異常漲跌（扣除大盤影響）'),
        if (st.historyLoading) const Center(child: Padding(padding: EdgeInsets.all(16), child: CircularProgressIndicator())),
        if (!st.historyLoading && moves.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Text('尚無資料（需要先執行歷史事件庫建置）', style: TextStyle(color: Colors.grey)),
          ),
        for (final m in moves.reversed.take(15))
          Card(
            child: ListTile(
              title: Text(m.cause),
              subtitle: Text('${m.date} · 大盤 ${fmtPct(m.marketRet)} · 20 天後 ${fmtPct(m.forward['20'])}'),
              trailing: ChangeText(m.ret),
            ),
          ),
      ]),
    );
  }

  Widget _kv(String k, Widget v) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(k, style: const TextStyle(fontSize: 11.5, color: Colors.grey)),
        v,
      ]);
}
