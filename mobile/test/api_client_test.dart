import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/services/api_client.dart';

void main() {
  test('bounded response reader combines chunks below the limit', () async {
    final bytes = await readBoundedResponseBytes(
      Stream<List<int>>.fromIterable(<List<int>>[
        utf8.encode('hello '),
        utf8.encode('world'),
      ]),
      maximumBytes: 11,
      timeout: const Duration(seconds: 1),
    );

    expect(utf8.decode(bytes), 'hello world');
  });

  test('bounded response reader rejects an oversized body', () async {
    await expectLater(
      readBoundedResponseBytes(
        Stream<List<int>>.value(List<int>.filled(5, 1)),
        maximumBytes: 4,
        timeout: const Duration(seconds: 1),
      ),
      throwsA(
        isA<ApiException>().having(
          (error) => error.message,
          'message',
          contains('too large'),
        ),
      ),
    );
  });

  test('bounded response reader applies one total deadline', () async {
    final controller = StreamController<List<int>>();
    addTearDown(controller.close);

    await expectLater(
      readBoundedResponseBytes(
        controller.stream,
        maximumBytes: 4,
        timeout: const Duration(milliseconds: 10),
      ),
      throwsA(isA<TimeoutException>()),
    );
  });
}
