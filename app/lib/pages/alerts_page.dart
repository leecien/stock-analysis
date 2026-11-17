import 'package:material_ui/material_ui.dart';

import '../models.dart';
import '../state.dart';
import '../widgets.dart';

class AlertsPage extends StatelessWidget {
  const AlertsPage({super.key});
  @override
  Widget build(BuildContext context) {
    final alerts = AppScope.of(context).latest?.alerts ?? [];
    return Scaffold(
      appBar: AppBar(title: const Text('警示')),
      body: alerts.isEmpty
          ? const MessageView(icon: Icons.notifications_none, title: '近 3 天沒有警示')
          : ListView(padding: const EdgeInsets.symmetric(vertical: 8), children: [for (final a in alerts) AlertTile(a)]),
    );
  }
}

class AlertTile extends StatelessWidget {
  final AlertItem a;
  const AlertTile(this.a, {super.key});
  @override
  Widget build(BuildContext context) {
    final (icon, color) = switch (a.level) {
      'critical' => (Icons.error, Colors.red),
      'warning' => (Icons.warning_amber_rounded, Colors.orange),
      _ => (Icons.info_outline, Colors.blue),
    };
    return Card(
      child: ListTile(
        leading: Icon(icon, color: color),
        title: Text(a.title),
        subtitle: Text('${a.body}\n${timeAgo(a.createdAt)}'),
        isThreeLine: true,
        onTap: a.url.isNotEmpty ? () => openUrl(a.url) : null,
      ),
    );
  }
}
