import 'dart:math' as math;

import 'package:material_ui/material_ui.dart';
import 'package:url_launcher/url_launcher.dart';

import 'state.dart';

const indexNames = {
  '^GSPC': 'S&P 500',
  '^IXIC': '那斯達克',
  '^DJI': '道瓊',
  '^SOX': '費半',
  '^TWII': '台股加權',
  '^VIX': 'VIX',
  '^TNX': '美債10年',
  'CL=F': '原油',
  'GC=F': '黃金',
};

const stanceZh = {'bullish': '偏多', 'neutral': '中性', 'bearish': '偏空'};
const directionZh = {'up': '上漲', 'down': '下跌', 'flat': '持平'};
const providerZh = {'claude': 'Claude', 'gemini': 'Gemini', 'openai': 'ChatGPT', 'mock': '模擬 AI'};

/// 台灣習慣紅漲綠跌（可在設定切換）
Color upColor(BuildContext c) => AppScope.of(c).settings.upIsRed ? Colors.red.shade600 : Colors.green.shade600;
Color downColor(BuildContext c) => AppScope.of(c).settings.upIsRed ? Colors.green.shade600 : Colors.red.shade600;

Color changeColor(BuildContext c, double? v) {
  if (v == null || v == 0) return Theme.of(c).colorScheme.onSurfaceVariant;
  return v > 0 ? upColor(c) : downColor(c);
}

Color stanceColor(BuildContext c, String stance) => switch (stance) {
      'bullish' => upColor(c),
      'bearish' => downColor(c),
      _ => Colors.blueGrey,
    };

String fmtNum(double? v) {
  if (v == null) return '-';
  if (v.abs() >= 1000) return v.toStringAsFixed(0);
  if (v.abs() >= 10) return v.toStringAsFixed(2);
  return v.toStringAsFixed(3);
}

String fmtPct(double? v, {int digits = 2}) => v == null ? '-' : '${v > 0 ? '+' : ''}${v.toStringAsFixed(digits)}%';

String timeAgo(String isoStr) {
  final t = DateTime.tryParse(isoStr);
  if (t == null) return '';
  final d = DateTime.now().toUtc().difference(t.toUtc());
  if (d.inMinutes < 1) return '剛剛';
  if (d.inMinutes < 60) return '${d.inMinutes} 分鐘前';
  if (d.inHours < 24) return '${d.inHours} 小時前';
  return '${d.inDays} 天前';
}

String symName(String s) => indexNames[s] ?? s;

Future<void> openUrl(String url) async {
  final u = Uri.tryParse(url);
  if (u == null || !u.hasScheme || url.contains('example.com')) return;
  await launchUrl(u, mode: LaunchMode.externalApplication);
}

class ChangeText extends StatelessWidget {
  final double? value;
  final double fontSize;
  final bool bold;
  const ChangeText(this.value, {super.key, this.fontSize = 14, this.bold = true});
  @override
  Widget build(BuildContext context) => Text(
        fmtPct(value),
        style: TextStyle(
          color: changeColor(context, value),
          fontSize: fontSize,
          fontWeight: bold ? FontWeight.w600 : FontWeight.normal,
          fontFeatures: const [FontFeature.tabularFigures()],
        ),
      );
}

class StanceChip extends StatelessWidget {
  final String stance;
  final String? label;
  final bool small;
  const StanceChip(this.stance, {super.key, this.label, this.small = false});
  @override
  Widget build(BuildContext context) {
    final c = stanceColor(context, stance);
    return Container(
      padding: EdgeInsets.symmetric(horizontal: small ? 6 : 10, vertical: small ? 2 : 4),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: c.withValues(alpha: 0.5)),
      ),
      child: Text(label ?? stanceZh[stance] ?? '中性',
          style: TextStyle(color: c, fontSize: small ? 11 : 13, fontWeight: FontWeight.w600)),
    );
  }
}

class Tag extends StatelessWidget {
  final String text;
  final Color? color;
  final VoidCallback? onTap;
  const Tag(this.text, {super.key, this.color, this.onTap});
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(
          color: (color ?? cs.secondaryContainer).withValues(alpha: color == null ? 1 : 0.15),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(text,
            style: TextStyle(fontSize: 11.5, color: color ?? cs.onSecondaryContainer)),
      ),
    );
  }
}

class SectionTitle extends StatelessWidget {
  final String title;
  final Widget? trailing;
  const SectionTitle(this.title, {super.key, this.trailing});
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 8),
        child: Row(children: [
          Expanded(child: Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold))),
          ?trailing,
        ]),
      );
}

class Bullets extends StatelessWidget {
  final List<String> items;
  final IconData icon;
  final Color? color;
  const Bullets(this.items, {super.key, this.icon = Icons.circle, this.color});
  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final t in items)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Padding(
                  padding: const EdgeInsets.only(top: 3, right: 6),
                  child: Icon(icon, size: icon == Icons.circle ? 7 : 15, color: color ?? Colors.grey),
                ),
                Expanded(child: Text(t)),
              ]),
            ),
        ],
      );
}

class Importance extends StatelessWidget {
  final int value;
  const Importance(this.value, {super.key});
  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [
        for (var i = 1; i <= 5; i++)
          Icon(i <= value ? Icons.star_rounded : Icons.star_outline_rounded,
              size: 13, color: i <= value ? Colors.amber.shade700 : Colors.grey.shade400),
      ]);
}

class SentimentBar extends StatelessWidget {
  final double value; // -1 ~ 1
  const SentimentBar(this.value, {super.key});
  @override
  Widget build(BuildContext context) {
    final v = value.clamp(-1.0, 1.0);
    final c = changeColor(context, v);
    return SizedBox(
      height: 6,
      child: LayoutBuilder(builder: (context, box) {
        final half = box.maxWidth / 2;
        return Stack(children: [
          Container(decoration: BoxDecoration(color: Colors.grey.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(3))),
          Positioned(
            left: v >= 0 ? half : half + v * half,
            width: v.abs() * half,
            top: 0,
            bottom: 0,
            child: Container(decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(3))),
          ),
          Positioned(left: half - 0.5, width: 1, top: 0, bottom: 0, child: Container(color: Colors.grey)),
        ]);
      }),
    );
  }
}

/// 線圖（股價、情緒走勢、關鍵字熱度）
class LineChart extends StatelessWidget {
  final List<double?> values;
  final Color? color;
  final double height;
  final bool showLabels;
  final String? leftLabel, rightLabel;
  final bool zeroLine;
  const LineChart(this.values,
      {super.key, this.color, this.height = 40, this.showLabels = false, this.leftLabel, this.rightLabel, this.zeroLine = false});

  @override
  Widget build(BuildContext context) {
    final pts = values.whereType<double>().toList();
    final c = color ?? (pts.length >= 2 ? changeColor(context, pts.last - pts.first) : Colors.grey);
    final labelStyle = TextStyle(fontSize: 10.5, color: Theme.of(context).colorScheme.onSurfaceVariant);
    final chart = SizedBox(
      height: height,
      child: CustomPaint(
        size: Size.infinite,
        painter: _LinePainter(values, c, zeroLine, showLabels ? labelStyle : null),
      ),
    );
    if (!showLabels || (leftLabel == null && rightLabel == null)) return chart;
    return Column(children: [
      chart,
      const SizedBox(height: 2),
      Row(children: [
        Text(leftLabel ?? '', style: labelStyle),
        const Spacer(),
        Text(rightLabel ?? '', style: labelStyle),
      ]),
    ]);
  }
}

class _LinePainter extends CustomPainter {
  final List<double?> values;
  final Color color;
  final bool zeroLine;
  final TextStyle? labelStyle;
  _LinePainter(this.values, this.color, this.zeroLine, this.labelStyle);

  @override
  void paint(Canvas canvas, Size size) {
    final pts = values.whereType<double>().toList();
    if (pts.length < 2) return;
    var lo = pts.reduce(math.min), hi = pts.reduce(math.max);
    if (zeroLine) {
      lo = math.min(lo, 0);
      hi = math.max(hi, 0);
    }
    if (hi == lo) {
      hi += 1;
      lo -= 1;
    }
    final labelW = labelStyle != null ? 48.0 : 0.0;
    final w = size.width - labelW, h = size.height;
    double y(double v) => h - (v - lo) / (hi - lo) * (h - 4) - 2;
    final n = values.length;
    final path = Path();
    var started = false;
    Offset? last;
    for (var i = 0; i < n; i++) {
      final v = values[i];
      if (v == null) continue;
      final p = Offset(n == 1 ? 0 : i / (n - 1) * w, y(v));
      started ? path.lineTo(p.dx, p.dy) : path.moveTo(p.dx, p.dy);
      started = true;
      last = p;
    }
    if (zeroLine) {
      final zp = Paint()
        ..color = Colors.grey.withValues(alpha: 0.5)
        ..strokeWidth = 1;
      canvas.drawLine(Offset(0, y(0)), Offset(w, y(0)), zp);
    }
    final fill = Path.from(path)
      ..lineTo(last!.dx, h)
      ..lineTo(0, h)
      ..close();
    canvas.drawPath(
      fill,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [color.withValues(alpha: 0.25), color.withValues(alpha: 0.0)],
        ).createShader(Rect.fromLTWH(0, 0, w, h)),
    );
    canvas.drawPath(
      path,
      Paint()
        ..color = color
        ..strokeWidth = 1.8
        ..style = PaintingStyle.stroke
        ..strokeJoin = StrokeJoin.round,
    );
    canvas.drawCircle(last, 3, Paint()..color = color);
    if (labelStyle != null) {
      void label(String t, double yy) {
        final tp = TextPainter(text: TextSpan(text: t, style: labelStyle), textDirection: TextDirection.ltr)..layout();
        tp.paint(canvas, Offset(w + 4, (yy - tp.height / 2).clamp(0, h - tp.height)));
      }

      label(fmtNum(hi), 0);
      label(fmtNum(lo), h);
    }
  }

  @override
  bool shouldRepaint(covariant _LinePainter old) => old.values != values || old.color != color;
}

/// 歷史事件後的漲跌表：列 = 指數，欄 = 第 N 個交易日
class ReactionTable extends StatelessWidget {
  final Map<String, Map<String, double?>> reactions;
  final List<int> days;
  final List<String>? symbols;
  const ReactionTable(this.reactions, {super.key, this.days = const [1, 5, 20, 60], this.symbols});
  @override
  Widget build(BuildContext context) {
    final syms = (symbols ?? reactions.keys.toList()).where(reactions.containsKey).toList();
    if (syms.isEmpty) return const Text('沒有價格資料', style: TextStyle(color: Colors.grey));
    final head = TextStyle(fontSize: 12, color: Theme.of(context).colorScheme.onSurfaceVariant);
    return Table(
      columnWidths: const {0: FlexColumnWidth(1.6)},
      defaultVerticalAlignment: TableCellVerticalAlignment.middle,
      children: [
        TableRow(children: [
          Text('指數', style: head),
          for (final d in days) Text(d == 1 ? '當天' : '$d 天', style: head, textAlign: TextAlign.right),
        ]),
        for (final s in syms)
          TableRow(children: [
            Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Text(symName(s), style: const TextStyle(fontSize: 13))),
            for (final d in days)
              Align(alignment: Alignment.centerRight, child: ChangeText(reactions[s]?['$d'], fontSize: 13, bold: false)),
          ]),
      ],
    );
  }
}

class MessageView extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? message;
  final Widget? action;
  const MessageView({super.key, required this.icon, required this.title, this.message, this.action});
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, size: 48, color: Colors.grey),
            const SizedBox(height: 12),
            Text(title, style: Theme.of(context).textTheme.titleMedium, textAlign: TextAlign.center),
            if (message != null) ...[
              const SizedBox(height: 8),
              Text(message!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.grey)),
            ],
            if (action != null) ...[const SizedBox(height: 16), action!],
          ]),
        ),
      );
}
