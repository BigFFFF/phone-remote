import 'package:flutter/material.dart';

class AppLanguageScope extends InheritedWidget {
  const AppLanguageScope({
    super.key,
    required this.locale,
    required this.onLocaleChanged,
    required super.child,
  });

  final Locale locale;
  final ValueChanged<Locale> onLocaleChanged;

  static AppLanguageScope? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<AppLanguageScope>();

  @override
  bool updateShouldNotify(AppLanguageScope oldWidget) =>
      locale != oldWidget.locale;
}

extension LocalizedBuildContext on BuildContext {
  String tr(String english) {
    final locale = Localizations.maybeLocaleOf(this);
    if (locale?.languageCode != 'zh') {
      return english;
    }
    return _zh[english] ?? english;
  }
}

const Map<String, String> _zh = <String, String>{
  'Unable to load saved devices.': '无法加载已保存的设备。',
  'Control your Windows PC\nfrom your phone.': '用手机控制你的 Windows 电脑。',
  'Get Started': '开始使用',
  'Find your PC': '查找电脑',
  'Unable to find that PC. Check the address and try again.':
      '无法找到该电脑，请检查地址后重试。',
  'Finding Computers…': '正在查找电脑…',
  'Find Computers': '查找电脑',
  'Enter Address Manually': '手动输入地址',
  'Try Demo': '试用演示',
  'Creating a secure pairing session on the Windows PC…':
      '正在 Windows 电脑上创建安全配对会话…',
  'Available': '可用设备',
  'Secure API v1': '安全 API v1',
  'Update required': '需要更新',
  'Pair': '配对',
  'Enter PC address': '输入电脑地址',
  'Cancel': '取消',
  'Continue': '继续',
  'Pair securely': '安全配对',
  'Enter the six-digit code shown by Phone Remote on your Windows PC.':
      '输入 Windows 电脑上 Phone Remote 显示的六位验证码。',
  'Pairing code': '配对码',
  'The code expires in': '验证码有效期为',
  'minutes.': '分钟。',
  'Demo': '演示',
  'Remote': '遥控',
  'Apps': '应用',
  'Devices': '设备',
  'Settings': '设置',
  'Online': '在线',
  'Connecting': '连接中',
  'Waking': '正在唤醒',
  'Identity alert': '身份警告',
  'Pair again': '重新配对',
  'Offline': '离线',
  'Disconnected': '已断开',
  'Touch and move to control the pointer': '触摸并移动以控制指针',
  'Back': '返回',
  'Keyboard': '键盘',
  'Fullscreen': '全屏',
  'Desktop': '桌面',
  'Close active window': '关闭当前窗口',
  'Volume down': '降低音量',
  'Mute': '静音',
  'Volume up': '提高音量',
  'Previous': '上一首',
  'Play / Pause': '播放 / 暂停',
  'Next': '下一首',
  'Touchpad': '触控板',
  'D-pad': '方向键',
  'Pointer move': '移动指针',
  'Scroll': '滚动',
  'Left click': '左键单击',
  'Right click': '右键单击',
  'Double click': '双击',
  'Text sent': '文字已发送',
  'Text Input': '文字输入',
  'Enter': '回车',
  'Tab': 'Tab',
  'Escape': 'Esc',
  'Backspace': '退格',
  'Send': '发送',
  'Sending Wake on LAN…': '正在发送网络唤醒…',
  'Connecting securely…': '正在安全连接…',
  'Not connected.': '未连接。',
  'Retry': '重试',
  'Touchpad. One finger moves. Tap clicks. Two-finger tap right-clicks. Two-finger drag scrolls.':
      '触控板。单指移动，轻点单击，双指轻点右键，双指拖动滚动。',
  'Up': '向上',
  'Left': '向左',
  'Right': '向右',
  'Down': '向下',
  'Browser': '浏览器',
  'Music': '音乐',
  'Movies': '电影',
  'Connect to a PC to load approved apps.': '连接电脑后加载已批准的应用。',
  'No approved Windows apps are configured.': '尚未配置已批准的 Windows 应用。',
  'Unavailable': '不可用',
  'Living Room PC': '客厅电脑',
  'Saved securely': '已安全保存',
  'Remove favorite': '取消收藏',
  'Make favorite': '设为收藏',
  'Add PC': '添加电脑',
  'Forget this PC?': '忘记这台电脑？',
  'Forget': '忘记',
  'Local and private': '本地且私密',
  'No cloud account, analytics, ads, or keyboard content collection.':
      '无云账户、分析、广告，也不会收集键盘内容。',
  'Wake on LAN': '网络唤醒',
  'Standby (S3)': '待机 (S3)',
  'Standby': '待机',
  'Hibernate': '休眠',
  'Restart': '重启',
  'Shut down': '关机',
  'Pointer sensitivity': '指针灵敏度',
  'Scroll sensitivity': '滚动灵敏度',
  'Reset touchpad settings': '重置触控板设置',
  'Language': '语言',
  'Chinese': '中文',
  'English': 'English',
  'Wake on LAN simulated in Demo': '演示模式已模拟网络唤醒',
  'PC connection is ready': '电脑连接已就绪',
  'Unsaved work on the Windows PC may be lost.': 'Windows 电脑上未保存的工作可能会丢失。',
};
