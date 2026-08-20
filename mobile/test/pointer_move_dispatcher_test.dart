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

  test('keeps at most one aggregate queued while a request is in flight',
      () async {
    final firstRequest = Completer<void>();
    final calls = <(double, double)>[];
    final dispatcher = PointerMoveDispatcher(
      interval: const Duration(milliseconds: 2),
      send: (dx, dy) async {
        calls.add((dx, dy));
        if (calls.length == 1) {
          await firstRequest.future;
        }
      },
    );

    dispatcher.add(1, 1);
    await Future<void>.delayed(const Duration(milliseconds: 8));
    for (var index = 0; index < 100; index += 1) {
      dispatcher.add(1, -1);
    }
    expect(calls, hasLength(1));

    firstRequest.complete();
    await Future<void>.delayed(const Duration(milliseconds: 15));

    expect(calls, <(double, double)>[(1, 1), (100, -100)]);
    dispatcher.dispose();
  });
}
