import 'package:material_ui/material_ui.dart';

import '../models.dart';
import '../state.dart';
import '../widgets.dart';
import 'common.dart';
import 'themes_page.dart';

class NewsPage extends StatelessWidget {
  const NewsPage({super.key});
  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 2,
        child: Scaffold(
          appBar: AppBar(
            title: const Text('熱門'),
            actions: commonActions(context),
            bottom: const TabBar(tabs: [Tab(text: '關鍵字熱度'), Tab(text: '最新新聞')]),
          ),
          body: LatestBuilder(
            builder: (context, l) => TabBarView(children: [_KeywordList(l), NewsList(l.news)]),
          ),
        ),
      );
}

class _KeywordList extends StatelessWidget {
  final Latest l;
  const _KeywordList(this.l);
  @override
  Widget build(BuildContext context) {
    if (l.keywords.isEmpty) {
      return ListView(children: const [
        MessageView(icon: Icons.search_off, title: '還沒有關鍵字資料', message: '後端每小時統計一次'),
      ]);
    }
    return ListView.separated(
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemCount: l.keywords.length + 1,
      separatorBuilder: (_, _) => const Divider(height: 1),
      itemBuilder: (context, i) {
        if (i == 0) {
          return const Padding(
            padding: EdgeInsets.fromLTRB(16, 4, 16, 8),
            child: Text('「熱度」= 近 24 小時出現次數 ÷ 前 7 天平均每天次數。倍數越高代表突然被大量討論。',
                style: TextStyle(fontSize: 12, color: Colors.grey)),
          );
        }
        final k = l.keywords[i - 1];
        final hot = k.ratio >= 3;
        return ListTile(
          onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => KeywordNewsPage(k.keyword))),
          leading: CircleAvatar(
            backgroundColor: hot ? Colors.deepOrange.withValues(alpha: 0.15) : null,
            child: Text('$i', style: TextStyle(color: hot ? Colors.deepOrange : null)),
          ),
          title: Row(children: [
            Flexible(child: Text(k.keyword, overflow: TextOverflow.ellipsis)),
            if (hot) const Text(' 🔥'),
          ]),
          subtitle: Text(
            '24h ${k.count24h} 次 · ${k.ratio.toStringAsFixed(1)} 倍'
            '${k.themes.isNotEmpty ? ' · ${k.themes.map((t) => l.themeById(t)?.name ?? t).join('、')}' : ''}',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          trailing: SizedBox(
            width: 80,
            child: LineChart(k.series.cast<double?>(), height: 28, color: hot ? Colors.deepOrange : Colors.blueGrey),
          ),
        );
      },
    );
  }
}

class NewsList extends StatelessWidget {
  final List<NewsItem> news;
  final Widget? header;
  const NewsList(this.news, {super.key, this.header});
  @override
  Widget build(BuildContext context) {
    if (news.isEmpty) {
      return ListView(children: [
        ?header,
        const MessageView(icon: Icons.article_outlined, title: '沒有相關新聞'),
      ]);
    }
    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemCount: news.length + (header == null ? 0 : 1),
      itemBuilder: (context, i) {
        if (header != null && i == 0) return header!;
        return NewsTile(news[i - (header == null ? 0 : 1)]);
      },
    );
  }
}

class NewsTile extends StatelessWidget {
  final NewsItem n;
  const NewsTile(this.n, {super.key});
  @override
  Widget build(BuildContext context) {
    final c = changeColor(context, n.sentiment.abs() < 0.15 ? 0 : n.sentiment);
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => NewsDetailPage(n))),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
                width: 4,
                height: 48,
                margin: const EdgeInsets.only(right: 10),
                decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(2))),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(n.title, style: const TextStyle(fontWeight: FontWeight.w600), maxLines: 2, overflow: TextOverflow.ellipsis),
                if (n.summary.isNotEmpty && n.summary != n.title) ...[
                  const SizedBox(height: 4),
                  Text(n.summary, style: const TextStyle(fontSize: 13), maxLines: 2, overflow: TextOverflow.ellipsis),
                ],
                const SizedBox(height: 6),
                Wrap(spacing: 6, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
                  Importance(n.importance),
                  Tag(n.eventTypeZh),
                  Text('${n.source} · ${timeAgo(n.published)}', style: const TextStyle(fontSize: 11.5, color: Colors.grey)),
                ]),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

class NewsDetailPage extends StatelessWidget {
  final NewsItem n;
  const NewsDetailPage(this.n, {super.key});
  @override
  Widget build(BuildContext context) {
    final l = AppScope.of(context).latest;
    final analog = l?.analogFor(n.id);
    final senti = n.sentiment;
    return Scaffold(
      appBar: AppBar(title: const Text('新聞分析')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text(n.title, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 6),
        Text('${n.source} · ${timeAgo(n.published)} · 分析：${providerZh[n.analyzedBy] ?? n.analyzedBy}',
            style: const TextStyle(color: Colors.grey, fontSize: 12)),
        const SizedBox(height: 16),
        if (n.summary.isNotEmpty) ...[
          const Text('AI 摘要', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text(n.summary),
          const SizedBox(height: 16),
        ],
        Wrap(crossAxisAlignment: WrapCrossAlignment.center, children: [
          const Text('影響：'),
          Text(
            senti > 0.15 ? '正面 ${senti.toStringAsFixed(2)}' : senti < -0.15 ? '負面 ${senti.toStringAsFixed(2)}' : '中性',
            style: TextStyle(color: changeColor(context, senti.abs() < 0.15 ? 0 : senti), fontWeight: FontWeight.w600),
          ),
          const SizedBox(width: 16),
          const Text('重要性：'),
          Importance(n.importance),
        ]),
        const SizedBox(height: 8),
        SentimentBar(senti),
        const SizedBox(height: 16),
        _row(context, '事件類型', [Tag(n.eventTypeZh)]),
        if (n.themes.isNotEmpty)
          _row(context, '相關產業', [
            for (final t in n.themes)
              Tag(l?.themeById(t)?.name ?? t, onTap: () {
                final th = l?.themeById(t);
                if (th != null) Navigator.push(context, MaterialPageRoute(builder: (_) => ThemeDetailPage(th)));
              }),
          ]),
        if (n.tickers.isNotEmpty) _row(context, '相關個股', [for (final t in n.tickers) Tag(t)]),
        if (n.keywords.isNotEmpty) _row(context, '關鍵字', [for (final k in n.keywords) Tag(k)]),
        if (analog != null && analog.matches.isNotEmpty) ...[
          const SizedBox(height: 16),
          const Text('歷史上類似的事件', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 4),
          const Text('事件發生後，大盤在第 N 個交易日的累積漲跌', style: TextStyle(fontSize: 12, color: Colors.grey)),
          for (final m in analog.matches)
            Card(
              margin: const EdgeInsets.symmetric(vertical: 6),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${m.date}　${m.title}', style: const TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Tag(m.categoryName),
                  const SizedBox(height: 8),
                  ReactionTable(m.reactions),
                ]),
              ),
            ),
        ],
        const SizedBox(height: 20),
        if (n.url.isNotEmpty && !n.url.contains('example.com'))
          FilledButton.icon(
            onPressed: () => openUrl(n.url),
            icon: const Icon(Icons.open_in_new),
            label: const Text('閱讀原文'),
          ),
      ]),
    );
  }

  Widget _row(BuildContext context, String label, List<Widget> tags) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 72, child: Text(label, style: const TextStyle(color: Colors.grey))),
          Expanded(child: Wrap(spacing: 6, runSpacing: 6, children: tags)),
        ]),
      );
}

class KeywordNewsPage extends StatelessWidget {
  final String keyword;
  const KeywordNewsPage(this.keyword, {super.key});
  @override
  Widget build(BuildContext context) {
    final l = AppScope.of(context).latest;
    final low = keyword.toLowerCase();
    final news = (l?.news ?? [])
        .where((n) =>
            n.keywords.any((k) => k.toLowerCase() == low) ||
            n.title.toLowerCase().contains(low) ||
            n.summary.toLowerCase().contains(low))
        .toList();
    KeywordItem? k;
    for (final x in l?.keywords ?? <KeywordItem>[]) {
      if (x.keyword == keyword) k = x;
    }
    return Scaffold(
      appBar: AppBar(title: Text('關鍵字：$keyword')),
      body: NewsList(
        news,
        header: k == null
            ? null
            : Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('近 24 小時 ${k.count24h} 次，平常每天約 ${k.baseline.toStringAsFixed(1)} 次（${k.ratio.toStringAsFixed(1)} 倍）'),
                    const SizedBox(height: 8),
                    LineChart(k.series.cast<double?>(),
                        height: 60, showLabels: true, leftLabel: '48 小時前', rightLabel: '現在', color: Colors.deepOrange),
                  ]),
                ),
              ),
      ),
    );
  }
}
