import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/application/phone_remote_controller.dart';
import 'package:phone_remote/models/api_models.dart';
import 'package:phone_remote/models/device.dart';
import 'package:phone_remote/repositories/device_repository.dart';
import 'package:phone_remote/services/api_client.dart';
import 'package:phone_remote/services/discovery_service.dart';
import 'package:phone_remote/services/pairing_service.dart';
import 'package:phone_remote/services/remote_session.dart';
import 'package:phone_remote/services/wake_service.dart';

import 'support/fake_api.dart';
import 'support/memory_storage.dart';

void main() {
  test('controller chooses and changes a single favorite PC', () async {
    final repository = RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );
    final first = _device('first', favorite: true);
    final second = _device('second');
    await repository.savePaired(first, 'first-secret');
    await repository.savePaired(second, 'second-secret');
    final controller = _controller(repository);
    await controller.initialize();

    expect(controller.preferredDevice?.serverId, 'first');
    await controller.toggleFavorite(second);

    expect(controller.preferredDevice?.serverId, 'second');
    expect(controller.devices.where((device) => device.favorite), hasLength(1));
  });

  test('controller publishes merged discovery results', () async {
    final repository = RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );
    final controller = _controller(
      repository,
      discovery: const _FakeDiscoveryService(),
    );
    await controller.initialize();

    await controller.discover();

    expect(controller.searching, isFalse);
    expect(controller.discoveredDevices.single.serverId, 'discovered-1');
  });

  test('sends Wake on LAN and retries a trusted offline PC', () async {
    final repository = RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );
    final device = _device('sleeping').copyWith(mac: '00:11:22:33:44:55');
    await repository.savePaired(device, 'secret');
    final sessions = _FlakySessionFactory();
    final wake = _RecordingWakeService();
    final waits = <Duration>[];
    final apiFactory = _apiFactory();
    final controller = PhoneRemoteController(
      deviceRepository: repository,
      discoveryService: const _FakeDiscoveryService(),
      pairingService: PairingService(
        apiClientFactory: apiFactory,
        deviceRepository: repository,
      ),
      remoteSessionFactory: sessions,
      wakeService: wake,
      delay: (duration) async => waits.add(duration),
    );

    await controller.connect(device);

    expect(controller.connectionPhase, RemoteConnectionPhase.connected);
    expect(sessions.attempts, 2);
    expect(wake.sent, 1);
    expect(waits, <Duration>[const Duration(seconds: 1)]);
  });
}

PhoneRemoteController _controller(
  DeviceRepository repository, {
  DiscoveryService discovery = const _FakeDiscoveryService(),
}) {
  final factory = _apiFactory();
  return PhoneRemoteController(
    deviceRepository: repository,
    discoveryService: discovery,
    pairingService: PairingService(
      apiClientFactory: factory,
      deviceRepository: repository,
    ),
    remoteSessionFactory: RealRemoteSessionFactory(
      deviceRepository: repository,
      apiClientFactory: factory,
    ),
    wakeService: const UnavailableWakeService('Unavailable in tests.'),
  );
}

FakeApiClientFactory _apiFactory() => FakeApiClientFactory(
      info: ServerInfo(
        serverId: 'server',
        name: 'PC',
        version: '1.0.0',
        apiVersion: 1,
        pairing: true,
        identityFingerprint: 'a' * 64,
        certificateFingerprint: 'b' * 64,
      ),
      session: const PairingSession(sessionId: 'session', expiresIn: 300),
      result: PairingResult(
        clientId: 'client',
        credential: 'secret',
        serverId: 'server',
        identityFingerprint: 'a' * 64,
      ),
    );

Device _device(String serverId, {bool favorite = false}) {
  return Device(
    id: serverId,
    serverId: serverId,
    name: '$serverId PC',
    host: '192.168.1.20',
    serverIdentity: 'a' * 64,
    clientId: '$serverId-client',
    credentialReference: 'credential.$serverId',
    favorite: favorite,
  );
}

class _FakeDiscoveryService implements DiscoveryService {
  const _FakeDiscoveryService();

  @override
  Future<List<DiscoveredDevice>> discover({
    Duration timeout = const Duration(seconds: 5),
  }) async {
    return const <DiscoveredDevice>[
      DiscoveredDevice(
        serverId: 'discovered-1',
        name: 'Living Room PC',
        host: '192.168.1.30',
        port: 8765,
        apiVersion: 1,
        tls: true,
      ),
    ];
  }
}

class _FlakySessionFactory implements RemoteSessionFactory {
  int attempts = 0;

  @override
  Future<RemoteSession> connect(Device device) async {
    attempts += 1;
    if (attempts == 1) {
      throw const ApiException('PC is offline.');
    }
    return _TestRemoteSession(device);
  }
}

class _TestRemoteSession implements RemoteSession {
  _TestRemoteSession(this.device);

  @override
  final Device device;

  @override
  ServerStatus get status => ServerStatus(
        serverId: device.serverId,
        name: device.name,
        version: '1.0.0',
        apiVersion: 1,
        addresses: const <String>['192.168.1.20'],
        port: 8765,
        configOk: true,
      );

  @override
  void close() {}

  @override
  Future<List<ConfiguredApp>> getApps() async => const <ConfiguredApp>[];

  @override
  Future<void> launchApp(String appId) async {}

  @override
  Future<void> sendAction(String action) async {}

  @override
  Future<void> sendMouseClick({String button = 'left'}) async {}

  @override
  Future<void> sendMouseDoubleClick() async {}

  @override
  Future<void> sendMouseMove(double dx, double dy) async {}

  @override
  Future<void> sendMouseWheel(double delta) async {}

  @override
  Future<void> sendPowerAction(String action) async {}

  @override
  Future<void> sendText(String text) async {}
}

class _RecordingWakeService implements WakeService {
  int sent = 0;

  @override
  Future<WakeCapability> capability(Device device) async =>
      const WakeCapability.available();

  @override
  Future<void> wake(Device device) async {
    sent += 1;
  }
}
