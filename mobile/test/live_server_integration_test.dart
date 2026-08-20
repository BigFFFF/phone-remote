import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/models/server_endpoint.dart';
import 'package:phone_remote/repositories/device_repository.dart';
import 'package:phone_remote/services/api_client.dart';
import 'package:phone_remote/services/pairing_service.dart';
import 'package:phone_remote/services/remote_session.dart';

import 'support/memory_storage.dart';

void main() {
  final enabled = Platform.environment['PHONE_REMOTE_LIVE_SERVER_TEST'] == '1';

  test(
    'pairs and reconnects against the real Python HTTPS server',
    () async {
      final portProbe =
          await ServerSocket.bind(InternetAddress.loopbackIPv4, 0);
      final port = portProbe.port;
      await portProbe.close();

      final repositoryRoot = Directory.current.parent.absolute;
      final python = Platform.environment['PHONE_REMOTE_PYTHON'] ??
          '${repositoryRoot.path}${Platform.pathSeparator}.venv${Platform.pathSeparator}Scripts${Platform.pathSeparator}python.exe';
      final dataDirectory =
          await Directory.systemTemp.createTemp('phone-remote-live-test-');
      final ready = Completer<void>();
      final pairCode = Completer<String>();
      final output = <String>[];
      final process = await Process.start(
        python,
        <String>[
          '-m',
          'phone_remote',
          '--host',
          '127.0.0.1',
          '--port',
          '$port',
          '--name',
          'Flutter Integration PC',
          '--data-dir',
          dataDirectory.path,
          '--no-tray',
          '--no-discovery',
          '--print-pair-code',
        ],
        workingDirectory:
            '${repositoryRoot.path}${Platform.pathSeparator}server',
        environment: <String, String>{
          ...Platform.environment,
          'PYTHONUNBUFFERED': '1',
        },
      );

      void capture(String line) {
        output.add(line);
        if (!ready.isCompleted && line.contains('https://127.0.0.1:$port')) {
          ready.complete();
        }
        final match = RegExp(r'pairing code: ([0-9]{6})').firstMatch(line);
        if (!pairCode.isCompleted && match != null) {
          pairCode.complete(match.group(1)!);
        }
      }

      final stdoutSubscription = process.stdout
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen(capture);
      final stderrSubscription = process.stderr
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen(capture);

      try {
        await ready.future.timeout(const Duration(seconds: 15));
        final repository = RealDeviceRepository(
          metadataStorage: MemoryMetadataStorage(),
          credentialStorage: MemoryCredentialStorage(),
        );
        const apiFactory = HttpApiClientFactory(
          timeout: Duration(seconds: 5),
        );
        final pairing = PairingService(
          apiClientFactory: apiFactory,
          deviceRepository: repository,
        );
        final endpoint = ServerEndpoint(host: '127.0.0.1', port: port);

        final attempt = await pairing.begin(endpoint);
        final code = await pairCode.future.timeout(const Duration(seconds: 5));
        final device = await pairing.complete(
          attempt: attempt,
          code: code,
          deviceName: 'Flutter Integration Test',
          platform: 'test',
        );
        final session = await RealRemoteSessionFactory(
          deviceRepository: repository,
          apiClientFactory: apiFactory,
        ).connect(device);

        expect(session.status.serverId, attempt.server.serverId);
        expect(
            session.device.serverIdentity, attempt.server.identityFingerprint);
        expect(await session.getApps(), isA<List>());
        session.close();
      } finally {
        process.kill();
        await process.exitCode.timeout(
          const Duration(seconds: 5),
          onTimeout: () => -1,
        );
        await stdoutSubscription.cancel();
        await stderrSubscription.cancel();
        await dataDirectory.delete(recursive: true);
      }
    },
    skip: enabled
        ? false
        : 'Set PHONE_REMOTE_LIVE_SERVER_TEST=1 to run the local HTTPS integration.',
    timeout: const Timeout(Duration(seconds: 45)),
  );
}
