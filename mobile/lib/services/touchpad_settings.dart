import 'package:shared_preferences/shared_preferences.dart';

class TouchpadSettings {
  const TouchpadSettings({
    this.pointerSensitivity = defaultSensitivity,
    this.scrollSensitivity = defaultSensitivity,
  });

  static const double minimumSensitivity = 0.5;
  static const double maximumSensitivity = 2.0;
  static const double defaultSensitivity = 1.0;

  final double pointerSensitivity;
  final double scrollSensitivity;

  TouchpadSettings copyWith({
    double? pointerSensitivity,
    double? scrollSensitivity,
  }) {
    return TouchpadSettings(
      pointerSensitivity:
          _normalize(pointerSensitivity ?? this.pointerSensitivity),
      scrollSensitivity:
          _normalize(scrollSensitivity ?? this.scrollSensitivity),
    );
  }

  static double _normalize(double value) {
    if (!value.isFinite) {
      return defaultSensitivity;
    }
    return value.clamp(minimumSensitivity, maximumSensitivity);
  }
}

abstract interface class TouchpadSettingsStore {
  Future<TouchpadSettings> load();

  Future<void> save(TouchpadSettings settings);
}

class MemoryTouchpadSettingsStore implements TouchpadSettingsStore {
  MemoryTouchpadSettingsStore([
    this.settings = const TouchpadSettings(),
  ]);

  TouchpadSettings settings;

  @override
  Future<TouchpadSettings> load() async => settings;

  @override
  Future<void> save(TouchpadSettings settings) async {
    this.settings = settings;
  }
}

class SharedPreferencesTouchpadSettingsStore implements TouchpadSettingsStore {
  SharedPreferencesTouchpadSettingsStore([SharedPreferencesAsync? preferences])
      : _preferences = preferences ?? SharedPreferencesAsync();

  static const String _pointerKey = 'touchpad.pointerSensitivity';
  static const String _scrollKey = 'touchpad.scrollSensitivity';

  final SharedPreferencesAsync _preferences;

  @override
  Future<TouchpadSettings> load() async {
    final pointer = await _preferences.getDouble(_pointerKey);
    final scroll = await _preferences.getDouble(_scrollKey);
    return const TouchpadSettings().copyWith(
      pointerSensitivity: pointer,
      scrollSensitivity: scroll,
    );
  }

  @override
  Future<void> save(TouchpadSettings settings) async {
    await Future.wait(<Future<void>>[
      _preferences.setDouble(_pointerKey, settings.pointerSensitivity),
      _preferences.setDouble(_scrollKey, settings.scrollSensitivity),
    ]);
  }
}
