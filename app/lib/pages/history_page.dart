import 'package:material_ui/material_ui.dart';

import '../models.dart';
import '../state.dart';
import '../widgets.dart';
import 'common.dart';

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key});
  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final st = AppScope.read(context);
    if (st.history == null && !st.historyLoading && st.historyError == null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => st.loadHistory());
    }
  }

  @override
  Widget build(BuildContext context) {
    final st = AppScope.of(context);
    final h = st.history;
    Widget body;
    if (h == null) {
      body = st.historyError != null
          ? MessageView(
              icon: Icons.cloud_off,
              title: '無法載入歷史事件庫',
              message: st.historyError,
              action: FilledButton(onPressed: () => st.loadHistory(force: true), child: const Text('重試')),
            )
          : const Center(child: CircularProgressIndicator());
    } else {
      body = TabBarView(children: [_EventList(h), _StatsView(h), _DrawdownView(h)]);
    }
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('20 年歷史事件'),
          actions: commonActions(context),
          bottom: const TabBar(tabs: [Tab(text: '事件'), Tab(text: '各類統計'), Tab(text: '修正波段')]),
        ),
        body: body,
      ),
    );
  }
}

class _EventList extends StatefulWidget {
  final HistoryData h;
  const _EventList(this.h);
  @override
  State<_EventList> createState() => _EventListState();
}

class _EventListState extends State<_EventList> {
  String _cat = '';
  String _source = 'all';
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final h = widget.h;
    final cats = <String, String>{};
    for (final e in h.events) {
      if (e.categoryName.isNotEmpty) cats[e.category] = e.categoryName;
    }
    final list = h.events.where((e) {
      if (_cat.isNotEmpty && e.category != _cat) return false;
      if (_source == 'seed' && e.source != 'seed') return false;
      if (_source == 'detected' && e.source != 'detected') return false;
      if (_q.isNotEmpty && !e.title.contains(_q) && !e.date.contains(_q)) return false;
      return true;
    }).toList();
    return Column(children: [
      if (h.demo)
        Container(
          width: double.infinity,
          color: Theme.of(context).colorScheme.tertiaryContainer,
          padding: const EdgeInsets.all(8),
          child: const Text('目前為示範資料：事件是真實的，但漲跌數字是模擬的', style: TextStyle(fontSize: 12)),
        ),
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
        child: TextField(
          decoration: const InputDecoration(
            prefixIcon: Icon(Icons.search),
            hintText: '搜尋事件或年份（例如 2008、關稅）',
            isDense: true,
            border: OutlineInputBorder(),
          ),
          onChanged: (v) => setState(() => _q = v.trim()),
        ),
      ),
      SizedBox(
        height: 48,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
          for (final (k, label) in [('all', '全部'), ('seed', '重大事件'), ('detected', '自動偵測')])
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 6),
              child: ChoiceChip(label: Text(label), selected: _source == k, onSelected: (_) => setState(() => _source = k)),
            ),
          const VerticalDivider(),
          for (final e in cats.entries)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 6),
              child: FilterChip(
                label: Text(e.value),
                selected: _cat == e.key,
                onSelected: (sel) => setState(() => _cat = sel ? e.key : ''),
              ),
            ),
        ]),
      ),
      Expanded(
        child: ListView.builder(
          itemCount: list.length,
          itemBuilder: (context, i) {
            final e = list[i];
            final us = e.reactions['^GSPC']?['1'];
            final tw = e.reactions['^TWII']?['1'];
            return ListTile(
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => EventDetailPage(e, h.forwardDays))),
              leading: Icon(
                e.source == 'seed' ? Icons.bookmark : Icons.bolt,
                color: e.source == 'seed' ? Colors.indigo : Colors.orange,
              ),
              title: Text(e.title, maxLines: 2, overflow: TextOverflow.ellipsis),
              subtitle: Text('${e.datePrecision == 'month' ? e.date.substring(0, 7) : e.date} · ${e.categoryName}'),
              trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                Row(mainAxisSize: MainAxisSize.min, children: [const Text('美 ', style: TextStyle(fontSize: 11)), ChangeText(us, fontSize: 12)]),
                Row(mainAxisSize: MainAxisSize.min, children: [const Text('台 ', style: TextStyle(fontSize: 11)), ChangeText(tw, fontSize: 12)]),
              ]),
            );
          },
        ),
      ),
    ]);
  }
}

class EventDetailPage extends StatelessWidget {
  final HistoryEvent e;
  final List<int> days;
  const EventDetailPage(this.e, this.days, {super.key});
  @override
  Widget build(BuildContext context) {
    final l = AppScope.of(context).latest;
    final conf = {'high': '高', 'medium': '中', 'low': '低（AI 推測，待查證）', 'none': '尚未標註'}[e.confidence] ?? e.confidence;
    return Scaffold(
      appBar: AppBar(title: Text(e.date)),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text(e.title, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 10),
        Wrap(spacing: 6, runSpacing: 6, children: [
          Tag(e.categoryName),
          Tag(e.source == 'seed' ? '人工整理' : '自動偵測'),
          Tag('可信度：$conf'),
          for (final t in e.themes) Tag(l?.themeById(t)?.name ?? t),
        ]),
        if (e.moves.isNotEmpty) ...[
          const SizedBox(height: 16),
          const Text('當天的大幅波動', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          Wrap(spacing: 14, children: [
            for (final m in e.moves.entries)
              Row(mainAxisSize: MainAxisSize.min, children: [Text('${symName(m.key)} '), ChangeText(m.value)]),
          ]),
        ],
        const SizedBox(height: 20),
        const Text('事件後的累積漲跌', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 4),
        const Text('以事件前一個交易日收盤為基準', style: TextStyle(fontSize: 12, color: Colors.grey)),
        const SizedBox(height: 10),
        ReactionTable(e.reactions, days: days),
      ]),
    );
  }
}

class _StatsView extends StatelessWidget {
  final HistoryData h;
  const _StatsView(this.h);
  @override
  Widget build(BuildContext context) {
    if (h.stats.isEmpty) {
      return const MessageView(icon: Icons.bar_chart, title: '還沒有統計資料');
    }
    return ListView(padding: const EdgeInsets.symmetric(vertical: 8), children: [
      const Padding(
        padding: EdgeInsets.fromLTRB(16, 4, 16, 8),
        child: Text('各類事件發生後，大盤的平均累積漲跌與上漲機率（只計算可信度中以上的事件）',
            style: TextStyle(fontSize: 12, color: Colors.grey)),
      ),
      for (final s in h.stats)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Flexible(child: Text(s.name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold))),
                const SizedBox(width: 8),
                Text('${s.count} 個事件', style: const TextStyle(color: Colors.grey, fontSize: 12)),
              ]),
              const SizedBox(height: 10),
              ReactionTable(s.avg, days: h.forwardDays),
              const SizedBox(height: 8),
              Text(
                '上漲機率（20 天）：${s.upRatio.entries.map((e) => '${symName(e.key)} ${e.value['20'] == null ? '-' : '${(e.value['20']! * 100).toStringAsFixed(0)}%'}').join('　')}',
                style: const TextStyle(fontSize: 12.5),
              ),
            ]),
          ),
        ),
    ]);
  }
}

class _DrawdownView extends StatelessWidget {
  final HistoryData h;
  const _DrawdownView(this.h);
  @override
  Widget build(BuildContext context) {
    if (h.drawdowns.isEmpty) return const MessageView(icon: Icons.show_chart, title: '還沒有資料');
    return ListView(padding: const EdgeInsets.symmetric(vertical: 8), children: [
      for (final entry in h.drawdowns.entries) ...[
        SectionTitle('${symName(entry.key)}：回檔超過 10% 共 ${entry.value.length} 次'),
        for (final d in entry.value.reversed)
          ListTile(
            dense: true,
            title: Text('${d.peak} → ${d.trough}（${d.days} 個交易日）'),
            subtitle: Text(d.recovered.isEmpty ? '尚未回到前高' : '${d.recovered} 回到前高'),
            trailing: ChangeText(d.depth),
          ),
      ],
    ]);
  }
}
