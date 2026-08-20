import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/models/api_models.dart';
import 'package:phone_remote/models/server_endpoint.dart';
import 'package:phone_remote/repositories/device_repository.dart';
import 'package:phone_remote/services/api_client.dart';
import 'package:phone_remote/services/pairing_service.dart';

import 'support/fake_api.dart';
import 'support/memory_storage.dart';

void main() {
  late FakeApiClientFactory apiFactory;
  late RealDeviceRepository repository;
  late PairingService service;

  setUp(() {
    apiFactory = FakeApiClientFactory(
      info: ServerInfo(
        serverId: 'server-1',
        name: 'Living Room PC',
        version: '1.0.0',
        apiVersion: 1,
        pairing: false,
        identityFingerprint: 'a' * 64,
        certificateFingerprint: 'b' * 64,
      ),
      session: const PairingSession(sessionId: 'session-1', expiresIn: 300),
      result: PairingResult(
        clientId: 'client-1',
        credential: 'secret-credential',
        serverId: 'server-1',
        identityFingerprint: 'a' * 64,
      ),
    );
    repository = RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );
    service = PairingService(
      apiClientFactory: apiFactory,
      deviceRepository: repository,
    );
  });

  test('probes once, then pins identity before requesting a code', () async {
    final attempt = await service.begin(
      const ServerEndpoint(host: '192.168.1.20'),
    );

    expect(attempt.server.serverId, 'server-1');
    expect(apiFactory.invocations, hasLength(2));
    expect(apiFactory.invocations.first.trustedIdentity, isNull);
    expect(apiFactory.invocations.last.trustedIdentity, 'a' * 64);
    expect(apiFactory.invocations.last.expectedServerId, 'server-1');
    expect(apiFactory.clients.every((client) => client.closed), isTrue);
  });

  test('stores an independently issued credential after pairing', () async {
    final attempt = await service.begin(
      const ServerEndpoint(host: '192.168.1.20'),
    );

    final device = await service.complete(
      attempt: attempt,
      code: '123456',
      deviceName: 'Pixel',
      platform: 'android',
    );

    expect(device.serverId, 'server-1');
    expect(device.clientId, 'client-1');
    expect(await repository.readCredential(device), 'secret-credential');
  });

  test('rejects a server identity switch during completion', () async {
    final attempt = await service.begin(
      const ServerEndpoint(host: '192.168.1.20'),
    );
    apiFactory.result = PairingResult(
      clientId: 'client-1',
      credential: 'secret-credential',
      serverId: 'server-1',
      identityFingerprint: 'c' * 64,
    );

    expect(
      () => service.complete(
        attempt: attempt,
        code: '123456',
        deviceName: 'Pixel',
        platform: 'android',
      ),
      throwsA(isA<IdentityMismatchException>()),
    );
  });

  test('validates the out-of-band pairing code locally', () async {
    final attempt = await service.begin(
      const ServerEndpoint(host: '192.168.1.20'),
    );

    expect(
      () => service.complete(
        attempt: attempt,
        code: '12345',
        deviceName: 'Pixel',
        platform: 'android',
      ),
      throwsFormatException,
    );
  });
}
