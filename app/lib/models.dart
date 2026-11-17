// 後端 latest.json / history.json 的資料模型

Map<String, dynamic> jm(dynamic v) =>
    v is Map ? v.map((k, val) => MapEntry(k.toString(), val)) : <String, dynamic>{};
List<dynamic> jl(dynamic v) => v is List ? v : const [];
String js(dynamic v, [String d = '']) => v == null ? d : v.toString();
double? jd(dynamic v) => v is num ? v.toDouble() : (v is String ? double.tryParse(v) : null);
int ji(dynamic v, [int d = 0]) => v is num ? v.toInt() : d;
List<String> jls(dynamic v) => jl(v).map((e) => e.toString()).toList();

class Snapshot {
  final String symbol, name, date, trend;
  final double? close, changePct, change5d, change20d, sma20, sma60, rsi, macdHist;
  final double trendScore;
  final List<double?> series;
  final List<String> seriesDates;

  Snapshot.fromJson(Map<String, dynamic> j)
      : symbol = js(j['symbol']),
        name = js(j['name'], js(j['symbol'])),
        date = js(j['date']),
        trend = js(j['trend']),
        close = jd(j['close']),
        changePct = jd(j['change_pct']),
        change5d = jd(j['change_5d_pct']),
        change20d = jd(j['change_20d_pct']),
        sma20 = jd(j['sma20']),
        sma60 = jd(j['sma60']),
        rsi = jd(j['rsi']),
        macdHist = jd(j['macd_hist']),
        trendScore = jd(j['trend_score']) ?? 0,
        series = jl(j['series']).map(jd).toList(),
        seriesDates = jls(j['series_dates']);
}

class Consensus {
  final String stance;
  final double agreement;
  final Map<String, String> votes;
  Consensus.fromJson(Map<String, dynamic> j)
      : stance = js(j['stance'], 'neutral'),
        agreement = jd(j['agreement']) ?? 0,
        votes = jm(j['votes']).map((k, v) => MapEntry(k, v.toString()));
  static Consensus? maybe(dynamic v) => v is Map ? Consensus.fromJson(jm(v)) : null;
}

class MarketView {
  final String name, stance, stanceZh, summary;
  final int confidence;
  final List<String> drivers, risks;
  final List<Snapshot> indices;
  final Consensus? consensus;
  MarketView.fromJson(Map<String, dynamic> j)
      : name = js(j['name']),
        stance = js(j['stance'], 'neutral'),
        stanceZh = js(j['stance_zh'], '中性'),
        summary = js(j['summary']),
        confidence = ji(j['confidence']),
        drivers = jls(j['drivers']),
        risks = jls(j['risks']),
        indices = jl(j['indices']).map((e) => Snapshot.fromJson(jm(e))).toList(),
        consensus = Consensus.maybe(j['consensus']);
}

class KeywordItem {
  final String keyword;
  final int count24h;
  final double baseline, ratio;
  final List<String> themes;
  final List<double> series;
  KeywordItem.fromJson(Map<String, dynamic> j)
      : keyword = js(j['keyword']),
        count24h = ji(j['count_24h']),
        baseline = jd(j['baseline']) ?? 0,
        ratio = jd(j['ratio']) ?? 1,
        themes = jls(j['themes']),
        series = jl(j['series']).map((e) => jd(e) ?? 0).toList();
}

class ThemeStock {
  final String symbol, name, trend;
  final double? close, changePct, change5d;
  ThemeStock.fromJson(Map<String, dynamic> j)
      : symbol = js(j['symbol']),
        name = js(j['name'], js(j['symbol'])),
        trend = js(j['trend']),
        close = jd(j['close']),
        changePct = jd(j['change_pct']),
        change5d = jd(j['change_5d_pct']);
}

class ThemeItem {
  final String id, name, stance, stanceZh, reason;
  final int news24h;
  final double sentiment;
  final List<double?> sentimentDaily;
  final List<String> drivers, keywords;
  final List<ThemeStock> stocks;
  ThemeItem.fromJson(Map<String, dynamic> j)
      : id = js(j['id']),
        name = js(j['name']),
        stance = js(j['stance'], 'neutral'),
        stanceZh = js(j['stance_zh'], '中性'),
        reason = js(j['reason']),
        news24h = ji(j['news_24h']),
        sentiment = jd(j['sentiment']) ?? 0,
        sentimentDaily = jl(j['sentiment_daily']).map(jd).toList(),
        drivers = jls(j['drivers']),
        keywords = jls(j['keywords']),
        stocks = jl(j['stocks']).map((e) => ThemeStock.fromJson(jm(e))).toList();
}

class WatchItem {
  final Snapshot snap;
  final String stance, stanceZh, reason;
  final List<String> themes, newsIds;
  final Consensus? consensus;
  WatchItem.fromJson(Map<String, dynamic> j)
      : snap = Snapshot.fromJson(j),
        stance = js(j['stance'], 'neutral'),
        stanceZh = js(j['stance_zh'], '中性'),
        reason = js(j['reason']),
        themes = jls(j['themes']),
        newsIds = jls(j['news']),
        consensus = Consensus.maybe(j['consensus']);
}

class NewsItem {
  final String id, title, summary, url, source, published, eventType, eventTypeZh, region, analyzedBy;
  final double sentiment;
  final int importance;
  final List<String> themes, macros, tickers, keywords;
  NewsItem.fromJson(Map<String, dynamic> j)
      : id = js(j['id']),
        title = js(j['title']),
        summary = js(j['ai_summary']),
        url = js(j['url']),
        source = js(j['source']),
        published = js(j['published']),
        eventType = js(j['event_type']),
        eventTypeZh = js(j['event_type_zh'], '其他'),
        region = js(j['region']),
        analyzedBy = js(j['analyzed_by']),
        sentiment = jd(j['sentiment']) ?? 0,
        importance = ji(j['importance'], 1),
        themes = jls(j['themes']),
        macros = jls(j['macro_factors']),
        tickers = jls(j['tickers']),
        keywords = jls(j['keywords']);
}

class AnalogMatch {
  final String id, date, title, categoryName;
  final Map<String, Map<String, double?>> reactions;
  AnalogMatch.fromJson(Map<String, dynamic> j)
      : id = js(j['id']),
        date = js(j['date']),
        title = js(j['title']),
        categoryName = js(j['category_name']),
        reactions = parseReactions(j['reactions']);
}

Map<String, Map<String, double?>> parseReactions(dynamic v) =>
    jm(v).map((k, r) => MapEntry(k, jm(r).map((n, x) => MapEntry(n, jd(x)))));

class Analog {
  final String newsId, title;
  final List<AnalogMatch> matches;
  Analog.fromJson(Map<String, dynamic> j)
      : newsId = js(j['news_id']),
        title = js(j['title']),
        matches = jl(j['matches']).map((e) => AnalogMatch.fromJson(jm(e))).toList();
}

class AlertItem {
  final String id, level, kind, title, body, createdAt, url, symbol;
  AlertItem.fromJson(Map<String, dynamic> j)
      : id = js(j['id']),
        level = js(j['level'], 'info'),
        kind = js(j['kind']),
        title = js(j['title']),
        body = js(j['body']),
        createdAt = js(j['created_at']),
        url = js(j['url']),
        symbol = js(j['symbol']);
}

class Prediction {
  final String target, direction, rationale, provider, status, baseDate, evalDate, actual;
  final int horizon, confidence;
  final double? actualPct;
  Prediction.fromJson(Map<String, dynamic> j)
      : target = js(j['target']),
        direction = js(j['direction']),
        rationale = js(j['rationale']),
        provider = js(j['provider']),
        status = js(j['status']),
        baseDate = js(j['base_date']),
        evalDate = js(j['eval_date']),
        actual = js(j['actual']),
        horizon = ji(j['horizon_days'], 5),
        confidence = ji(j['confidence']),
        actualPct = jd(j['actual_pct']);
}

class DeepView {
  final String provider, model, headline, shortTerm, mediumTerm, historicalView;
  final MarketView? us, tw;
  final List<Prediction> predictions;
  DeepView.fromJson(this.provider, Map<String, dynamic> j)
      : model = js(j['model']),
        headline = js(j['headline']),
        shortTerm = js(jm(j['outlook'])['short_term']),
        mediumTerm = js(jm(j['outlook'])['medium_term']),
        historicalView = js(j['historical_view']),
        us = j['us'] is Map ? MarketView.fromJson(jm(j['us'])) : null,
        tw = j['tw'] is Map ? MarketView.fromJson(jm(j['tw'])) : null,
        predictions = jl(j['predictions']).map((e) => Prediction.fromJson(jm(e))).toList();
}

class DeepReport {
  final String generatedAt;
  final List<DeepView> views;
  final Map<String, Consensus> consensus;
  DeepReport.fromJson(Map<String, dynamic> j)
      : generatedAt = js(j['generated_at']),
        views = jm(j['providers']).entries.map((e) => DeepView.fromJson(e.key, jm(e.value))).toList(),
        consensus = jm(j['consensus']).map((k, v) => MapEntry(k, Consensus.fromJson(jm(v))));
}

class ProviderAccuracy {
  final String name;
  final int correct, wrong, pending;
  final double? accuracy;
  ProviderAccuracy.fromJson(this.name, Map<String, dynamic> j)
      : correct = ji(j['correct']),
        wrong = ji(j['wrong']),
        pending = ji(j['pending']),
        accuracy = jd(j['accuracy']);
}

class BudgetInfo {
  final String month;
  final double spentTwd, limitTwd, ratio;
  final int calls;
  BudgetInfo.fromJson(Map<String, dynamic> j)
      : month = js(j['month']),
        spentTwd = jd(j['spent_twd']) ?? 0,
        limitTwd = jd(j['limit_twd']) ?? 600,
        ratio = jd(j['ratio']) ?? 0,
        calls = ji(j['calls']);
}

class Latest {
  final String generatedAt, generatedAtTw, session, headline, disclaimer, fastAi;
  final bool demoPrices, demoNews;
  final List<String> deepAi;
  final MarketView us, tw;
  final List<Snapshot> macro;
  final List<KeywordItem> keywords;
  final List<ThemeItem> themes;
  final List<WatchItem> watchlist;
  final List<NewsItem> news;
  final List<Analog> analogs;
  final DeepReport? deep;
  final List<AlertItem> alerts;
  final List<ProviderAccuracy> accuracy;
  final List<Prediction> recentPredictions;
  final BudgetInfo budget;

  Latest.fromJson(Map<String, dynamic> j)
      : generatedAt = js(j['generated_at']),
        generatedAtTw = js(j['generated_at_tw']),
        session = js(j['session']),
        headline = js(j['headline']),
        disclaimer = js(j['disclaimer']),
        fastAi = js(jm(j['mode'])['fast_ai'], 'mock'),
        demoPrices = jm(j['mode'])['demo_prices'] == true,
        demoNews = jm(j['mode'])['demo_news'] == true,
        deepAi = jls(jm(j['mode'])['deep_ai']),
        us = MarketView.fromJson(jm(jm(j['markets'])['us'])),
        tw = MarketView.fromJson(jm(jm(j['markets'])['tw'])),
        macro = jl(j['macro']).map((e) => Snapshot.fromJson(jm(e))).toList(),
        keywords = jl(j['keywords']).map((e) => KeywordItem.fromJson(jm(e))).toList(),
        themes = jl(j['themes']).map((e) => ThemeItem.fromJson(jm(e))).toList(),
        watchlist = jl(j['watchlist']).map((e) => WatchItem.fromJson(jm(e))).toList(),
        news = jl(j['news']).map((e) => NewsItem.fromJson(jm(e))).toList(),
        analogs = jl(j['analogs']).map((e) => Analog.fromJson(jm(e))).toList(),
        deep = j['deep'] is Map ? DeepReport.fromJson(jm(j['deep'])) : null,
        alerts = jl(j['alerts']).map((e) => AlertItem.fromJson(jm(e))).toList(),
        accuracy = jm(jm(j['accuracy'])['by_provider'])
            .entries
            .map((e) => ProviderAccuracy.fromJson(e.key, jm(e.value)))
            .toList(),
        recentPredictions =
            jl(jm(j['accuracy'])['recent']).map((e) => Prediction.fromJson(jm(e))).toList(),
        budget = BudgetInfo.fromJson(jm(j['budget']));

  bool get isMockAi => fastAi == 'mock';

  NewsItem? newsById(String id) {
    for (final n in news) {
      if (n.id == id) return n;
    }
    return null;
  }

  ThemeItem? themeById(String id) {
    for (final t in themes) {
      if (t.id == id) return t;
    }
    return null;
  }

  Analog? analogFor(String newsId) {
    for (final a in analogs) {
      if (a.newsId == newsId) return a;
    }
    return null;
  }
}

// ---------------- 歷史事件庫 ----------------

class HistoryEvent {
  final String id, date, datePrecision, title, category, categoryName, region, source, confidence;
  final List<String> themes;
  final Map<String, double?> moves;
  final Map<String, Map<String, double?>> reactions;
  HistoryEvent.fromJson(Map<String, dynamic> j)
      : id = js(j['id']),
        date = js(j['date']),
        datePrecision = js(j['date_precision'], 'day'),
        title = js(j['title']),
        category = js(j['category']),
        categoryName = js(j['category_name']),
        region = js(j['region']),
        source = js(j['source']),
        confidence = js(j['confidence']),
        themes = jls(j['themes']),
        moves = jm(j['moves']).map((k, v) => MapEntry(k, jd(jm(v)['ret']))),
        reactions = parseReactions(j['reactions']);
}

class CategoryStat {
  final String category, name;
  final int count;
  final Map<String, Map<String, double?>> avg, upRatio;
  CategoryStat.fromJson(Map<String, dynamic> j)
      : category = js(j['category']),
        name = js(j['name']),
        count = ji(j['count']),
        avg = parseReactions(j['avg']),
        upRatio = parseReactions(j['up_ratio']);
}

class StockMove {
  final String date, symbol, cause, confidence;
  final double? ret, marketRet, abnormal;
  final Map<String, double?> forward;
  StockMove.fromJson(Map<String, dynamic> j)
      : date = js(j['date']),
        symbol = js(j['symbol']),
        cause = js(j['cause']),
        confidence = js(j['confidence']),
        ret = jd(j['ret']),
        marketRet = jd(j['market_ret']),
        abnormal = jd(j['abnormal']),
        forward = jm(j['forward']).map((k, v) => MapEntry(k, jd(v)));
}

class Drawdown {
  final String peak, trough, recovered;
  final double? depth;
  final int days;
  Drawdown.fromJson(Map<String, dynamic> j)
      : peak = js(j['peak']),
        trough = js(j['trough']),
        recovered = js(j['recovered']),
        depth = jd(j['depth_pct']),
        days = ji(j['days_to_trough']);
}

class HistoryData {
  final bool demo;
  final String generatedAt, annotatedBy;
  final List<int> forwardDays;
  final List<HistoryEvent> events;
  final List<CategoryStat> stats;
  final Map<String, List<StockMove>> stockMoves;
  final Map<String, List<Drawdown>> drawdowns;
  HistoryData.fromJson(Map<String, dynamic> j)
      : demo = j['demo_data'] == true,
        generatedAt = js(j['generated_at']),
        annotatedBy = js(j['annotated_by']),
        forwardDays = jl(j['forward_days']).map((e) => ji(e)).toList(),
        events = jl(j['events']).map((e) => HistoryEvent.fromJson(jm(e))).toList(),
        stats = jl(j['category_stats']).map((e) => CategoryStat.fromJson(jm(e))).toList(),
        stockMoves = jm(j['stock_moves'])
            .map((k, v) => MapEntry(k, jl(v).map((e) => StockMove.fromJson(jm(e))).toList())),
        drawdowns = jm(j['drawdowns'])
            .map((k, v) => MapEntry(k, jl(v).map((e) => Drawdown.fromJson(jm(e))).toList()));
}
