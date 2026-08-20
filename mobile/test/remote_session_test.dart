import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/models/api_models.dart';
import 'package:phone_remote/models/device.dart';
import 'package:phone_remote/repositories/device_repository.dart';
import 'package:phone_remote/services/remote_session.dart';

import 'support/fake_api.dart';
import 'support/memory_storage.dart';

void main() {
  test('connects with pinned identity and an independently stored credential',
      () async {
    final repository = RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );
    final device = _device();
    await repository.savePaired(device, 'top-secret');
    final apiFactory = _apiFactory();
    final factory = RealRemoteSessionFactory(
      deviceRepository: repository,
      apiClientFactory: apiFactory,
    );

    final session = await factory.connect(device);

    final invocation = apiFactory.invocations.single;
    expect(invocation.trustedIdentity, device.serverIdentity);
    expect(invocation.expectedServerId, device.serverId);
    expect(invocation.credential, 'top-secret');
    expect(session.status.serverId, device.serverId);
    expect(session.device.lastSeen, isNotNull);
    expect(session.device.lastIpv4, '192.168.1.20');
    expect(session.device.mac, '00:11:22:33:44:55');
    expect(session.device.broadcastAddress, '192.168.1.255');

    await session.sendAction('enter');
    await session.sendMouseMove(2, -3);
    await session.sendText('你好');
    await session.sendPowerAction('sleep');
    await session.launchApp('steam');
    expect(apiFactory.commands, <String>[
      'action:enter',
      'move:2.0:-3.0',
      'text:你好',
      'power:sleep',
      'launch:steam',
    ]);

    session.close();
    expect(apiFactory.clients.single.closed, isTrue);
  });

  test('refuses to connect when the secure credential is missing', () async {
    final repository = RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );
    await repository.save(_device());
    final factory = RealRemoteSessionFactory(
      deviceRepository: repository,
      apiClientFactory: _apiFactory(),
    );

    expect(() => factory.connect(_device()), throwsA(isA<Exception>()));
  });
}

FakeApiClientFactory _apiFactory() => FakeApiClientFactory(
      info: ServerInfo(
        serverId: 'server-1',
        name: 'Living Room PC',
        version: '1.0.0',
        apiVersion: 1,
        pairing: true,
        identityFingerprint: 'a' * 64,
        certificateFingerprint: 'b' * 64,
      ),
      status: const ServerStatus(
        serverId: 'server-1',
        name: 'Living Room PC',
        version: '1.0.0',
        apiVersion: 1,
        addresses: <String>['192.168.1.20'],
        port: 8765,
        configOk: true,
        wakeTargets: <WakeTarget>[
          WakeTarget(
            mac: '00:11:22:33:44:55',
            address: '192.168.1.20',
            broadcast: '192.168.1.255',
          ),
        ],
      ),
      apps: const <ConfiguredApp>[
        ConfiguredApp(
          id: 'steam',
          name: 'Steam',
          available: true,
          icon: 'default',
        ),
      ],
      session: const PairingSession(sessionId: 'session', expiresIn: 300),
      result: PairingResult(
        clientId: 'client',
        credential: 'secret',
        serverId: 'server-1',
        identityFingerprint: 'a' * 64,
      ),
    );

Device _device() => Device(
      id: 'server-1',
      serverId: 'server-1',
      name: 'Living Room PC',
      host: '192.168.1.20',
      serverIdentity: 'a' * 64,
      clientId: 'client',
      credentialReference: 'credential.client',
    );
