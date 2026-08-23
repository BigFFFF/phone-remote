import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/services/touchpad_settings.dart';

void main() {
  test('touchpad sensitivity settings use safe defaults and bounds', () {
    const defaults = TouchpadSettings();
    expect(defaults.pointerSensitivity, 1.0);
    expect(defaults.scrollSensitivity, 1.0);

    final normalized = defaults.copyWith(
      pointerSensitivity: 99,
      scrollSensitivity: -2,
    );
    expect(normalized.pointerSensitivity, 2.0);
    expect(normalized.scrollSensitivity, 0.5);

    final nonFinite = defaults.copyWith(pointerSensitivity: double.nan);
    expect(nonFinite.pointerSensitivity, 1.0);
  });

  test('memory settings store persists both sensitivity values', () async {
    final store = MemoryTouchpadSettingsStore();
    const settings = TouchpadSettings(
      pointerSensitivity: 1.5,
      scrollSensitivity: 0.75,
    );

    await store.save(settings);

    final loaded = await store.load();
    expect(loaded.pointerSensitivity, 1.5);
    expect(loaded.scrollSensitivity, 0.75);
  });
}
