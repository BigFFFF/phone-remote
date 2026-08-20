import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Android launcher resources are adaptive and keep legacy fallbacks',
      () async {
    final manifest =
        await File('android/app/src/main/AndroidManifest.xml').readAsString();
    expect(manifest, contains('android:icon="@mipmap/ic_launcher"'));
    expect(manifest, contains('android:roundIcon="@mipmap/ic_launcher_round"'));

    for (final name in <String>['ic_launcher.xml', 'ic_launcher_round.xml']) {
      final adaptive = await File(
        'android/app/src/main/res/mipmap-anydpi-v26/$name',
      ).readAsString();
      expect(adaptive, contains('<adaptive-icon'));
      expect(adaptive, contains('@drawable/ic_launcher_background'));
      expect(adaptive, contains('@drawable/ic_launcher_foreground'));
    }

    final expectedSizes = <String, int>{
      'mdpi': 48,
      'hdpi': 72,
      'xhdpi': 96,
      'xxhdpi': 144,
      'xxxhdpi': 192,
    };
    for (final entry in expectedSizes.entries) {
      for (final fileName in <String>[
        'ic_launcher.png',
        'ic_launcher_round.png',
      ]) {
        final image = await _decode(
          'android/app/src/main/res/mipmap-${entry.key}/$fileName',
        );
        expect(image.width, entry.value, reason: '$fileName ${entry.key}');
        expect(image.height, entry.value, reason: '$fileName ${entry.key}');
        image.dispose();
      }
    }
  });

  test('iOS AppIcon files have exact dimensions and no transparency', () async {
    final expectedSizes = <String, int>{
      'Icon-App-1024x1024@1x.png': 1024,
      'Icon-App-20x20@1x.png': 20,
      'Icon-App-20x20@2x.png': 40,
      'Icon-App-20x20@3x.png': 60,
      'Icon-App-29x29@1x.png': 29,
      'Icon-App-29x29@2x.png': 58,
      'Icon-App-29x29@3x.png': 87,
      'Icon-App-40x40@1x.png': 40,
      'Icon-App-40x40@2x.png': 80,
      'Icon-App-40x40@3x.png': 120,
      'Icon-App-60x60@2x.png': 120,
      'Icon-App-60x60@3x.png': 180,
      'Icon-App-76x76@1x.png': 76,
      'Icon-App-76x76@2x.png': 152,
      'Icon-App-83.5x83.5@2x.png': 167,
    };
    const directory = 'ios/Runner/Assets.xcassets/AppIcon.appiconset';
    for (final entry in expectedSizes.entries) {
      final image = await _decode('$directory/${entry.key}');
      expect(image.width, entry.value, reason: entry.key);
      expect(image.height, entry.value, reason: entry.key);
      final pixels = await image.toByteData(format: ui.ImageByteFormat.rawRgba);
      expect(pixels, isNotNull, reason: entry.key);
      final bytes = pixels!.buffer.asUint8List();
      expect(
        _alphaValues(bytes).every((alpha) => alpha == 255),
        isTrue,
        reason: '${entry.key} must be opaque for App Store validation',
      );
      image.dispose();
    }
  });

  test('launch artwork is branded and uses real transparency', () async {
    final storyboard = await File(
      'ios/Runner/Base.lproj/LaunchScreen.storyboard',
    ).readAsString();
    expect(storyboard, contains('width="168"'));
    expect(storyboard, contains('height="168"'));
    expect(storyboard, contains('red="0.02352941176"'));

    final launchImage = await _decode(
      'ios/Runner/Assets.xcassets/LaunchImage.imageset/LaunchImage@3x.png',
    );
    expect(launchImage.width, 504);
    expect(launchImage.height, 504);
    final pixels = await launchImage.toByteData(
      format: ui.ImageByteFormat.rawRgba,
    );
    final alpha = _alphaValues(pixels!.buffer.asUint8List()).toSet();
    expect(alpha, contains(0));
    expect(alpha, contains(255));
    launchImage.dispose();

    final androidLaunch = await File(
      'android/app/src/main/res/drawable/launch_background.xml',
    ).readAsString();
    expect(androidLaunch, contains('@color/launch_background'));
    expect(androidLaunch, contains('@drawable/ic_launcher_foreground'));
  });
}

Future<ui.Image> _decode(String path) async {
  final bytes = await File(path).readAsBytes();
  final codec = await ui.instantiateImageCodec(bytes);
  try {
    return (await codec.getNextFrame()).image;
  } finally {
    codec.dispose();
  }
}

Iterable<int> _alphaValues(Uint8List rgba) sync* {
  for (var index = 3; index < rgba.length; index += 4) {
    yield rgba[index];
  }
}
