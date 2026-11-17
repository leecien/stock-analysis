import 'dart:convert';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:material_ui/material_ui.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:workmanager/workmanager.dart';

import 'models.dart';
import 'state.dart';

const _taskName = 'check-alerts';
final _plugin = FlutterLocalNotificationsPlugin();

const _levelRank = {'info': 0, 'warning': 1, 'critical': 2};

Future<void> initNotifications() async {
  await _plugin.initialize(
    settings: const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')),
  );
}

Future<void> requestNotificationPermission() async {
  await _plugin
      .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
      ?.requestNotificationsPermission();
}

/// 每小時在背景檢查一次新警示（Android 最短間隔 15 分鐘，系統可能延後執行）
Future<void> scheduleBackgroundCheck(AppSettings s) async {
  await Workmanager().initialize(callbackDispatcher);
  if (!s.notifyEnabled || s.source == DataSource.demo) {
    await Workmanager().cancelByUniqueName(_taskName);
    return;
  }
  await Workmanager().registerPeriodicTask(
    _taskName,
    _taskName,
    frequency: const Duration(hours: 1),
    constraints: Constraints(networkType: NetworkType.connected),
    existingWorkPolicy: ExistingPeriodicWorkPolicy.update,
  );
}

@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    WidgetsFlutterBinding.ensureInitialized();
    try {
      await initNotifications();
      await checkNewAlerts();
    } catch (_) {
      // 背景工作失敗就等下次
    }
    return true;
  });
}

/// 下載最新資料，對「還沒通知過」且等級夠高的警示發通知。
/// 第一次執行只記錄、不通知，避免一次跳出一大堆。
Future<int> checkNewAlerts({bool notify = true}) async {
  final s = await AppSettings.load();
  if (s.source == DataSource.demo) return 0;
  final body = await DataService.fetchRemote(s, 'latest');
  final latest = Latest.fromJson(jm(jsonDecode(body)));
  final prefs = await SharedPreferences.getInstance();
  final first = !prefs.containsKey('notified_ids');
  final seen = (prefs.getStringList('notified_ids') ?? []).toSet();
  final minRank = _levelRank[s.notifyLevel] ?? 1;
  var sent = 0;
  for (final a in latest.alerts) {
    if (seen.contains(a.id)) continue;
    seen.add(a.id);
    if (first || !notify || (_levelRank[a.level] ?? 0) < minRank) continue;
    await _plugin.show(
      id: a.id.hashCode & 0x7fffffff,
      title: a.title,
      body: a.body,
      notificationDetails: NotificationDetails(
        android: AndroidNotificationDetails(
          'alerts',
          '股市警示',
          channelDescription: '重大新聞、大盤與自選股異動',
          importance: a.level == 'critical' ? Importance.high : Importance.defaultImportance,
          priority: a.level == 'critical' ? Priority.high : Priority.defaultPriority,
        ),
      ),
    );
    sent++;
  }
  final keep = seen.toList();
  await prefs.setStringList('notified_ids', keep.length > 500 ? keep.sublist(keep.length - 500) : keep);
  return sent;
}
