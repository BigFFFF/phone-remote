import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/services/pointer_move_dispatcher.dart';

void main() {
  test('coalesces pointer deltas into a bounded request rate', () async {
    final calls = <(double, double)>[];
    final dispatcher = PointerMoveDispatcher(
      interval: const Duration(milliseconds: 5),
      send: (dx, dy) async => calls.add((dx, dy)),
    );

    dispatcher.add(1, 2);
    dispatcher.add(3, 4);
    dispatcher.add(-1, 1);
    await Future<void>.delayed(const Duration(milliseconds: 25));

    expect(calls, <(double, double)>[(3, 7)]);
    dispatcher.dispose();
  });

  test('keeps a bounded number of sends in flight without waiting for RTT',
      () async {
    final requests = <Completer<void>>[];
    final calls = <(double, double)>[];
    var active = 0;
    var maxActive = 0;
    final dispatcher = PointerMoveDispatcher(
      interval: const Duration(milliseconds: 2),
      maxConcurrentSends: 2,
      send: (dx, dy) async {
        calls.add((dx, dy));
        active += 1;
        maxActive = active > maxActive ? active : maxActive;
        final request = Completer<void>();
        requests.add(request);
        await request.future;
        active -= 1;
      },
    );

    dispatcher.add(1, 1);
    await Future<void>.delayed(const Duration(milliseconds: 8));
    for (var index = 0; index < 100; index += 1) {
      dispatcher.add(1, -1);
    }
    await Future<void>.delayed(const Duration(milliseconds: 8));
    expect(calls, <(double, double)>[(1, 1), (100, -100)]);

    for (var index = 0; index < 50; index += 1) {
      dispatcher.add(1, 2);
    }
    await Future<void>.delayed(const Duration(milliseconds: 8));
    expect(calls, hasLength(2));

    requests.first.complete();
    await Future<void>.delayed(const Duration(milliseconds: 8));

    expect(
      calls,
      <(double, double)>[(1, 1), (100, -100), (50, 100)],
    );
    expect(maxActive, 2);
    for (final request in requests.skip(1)) {
      request.complete();
    }
    dispatcher.dispose();
  });

  test('splits large accumulated movement without losing distance', () async {
    final calls = <(double, double)>[];
    final dispatcher = PointerMoveDispatcher(
      interval: const Duration(milliseconds: 1),
      maxAbsoluteDelta: 120,
      send: (dx, dy) async => calls.add((dx, dy)),
    );

    dispatcher.add(500, -260);
    await Future<void>.delayed(const Duration(milliseconds: 30));

    expect(calls.every((call) => call.$1.abs() <= 120), isTrue);
    expect(calls.every((call) => call.$2.abs() <= 120), isTrue);
    expect(calls.fold<double>(0, (sum, call) => sum + call.$1), 500);
    expect(calls.fold<double>(0, (sum, call) => sum + call.$2), -260);
    dispatcher.dispose();
  });
}
