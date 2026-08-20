import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/application/phone_remote_controller.dart';
import 'package:phone_remote/main.dart';
import 'package:phone_remote/models/api_models.dart';
import 'package:phone_remote/models/device.dart';
import 'package:phone_remote/repositories/device_repository.dart';
import 'package:phone_remote/services/discovery_service.dart';
import 'package:phone_remote/services/pairing_service.dart';
import 'package:phone_remote/services/remote_session.dart';
import 'package:phone_remote/services/wake_service.dart';

import 'support/fake_api.dart';
import 'support/memory_storage.dart';

void main() {
  testWidgets('first launch leads to discovery and an explicit Demo mode', (
    tester,
  ) async {
    final repository = _repository();
    await tester
        .pumpWidget(PhoneRemoteApp(controller: _controller(repository)));
    await tester.pumpAndSettle();

    expect(find.text('Phone Remote'), findsOneWidget);
    expect(
        find.text('Control your Windows PC\nfrom your phone.'), findsOneWidget);

    await tester.tap(find.text('Get Started'));
    await tester.pumpAndSettle();
    expect(find.text('Find Computers'), findsOneWidget);
    expect(find.text('Enter Address Manually'), findsOneWidget);
    expect(find.text('Try Demo'), findsOneWidget);

    await tester.tap(find.text('Try Demo'));
    await tester.pumpAndSettle();
    expect(find.text('Demo'), findsOneWidget);
    expect(find.text('Touchpad'), findsWidgets);
    expect(find.text('Remote'), findsOneWidget);
  });

  testWidgets('manual address dialog rejects HTTP and URL paths',
      (tester) async {
    final repository = _repository();
    await tester
        .pumpWidget(PhoneRemoteApp(controller: _controller(repository)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Get Started'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Enter Address Manually'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'http://example.test/api');
    await tester.tap(find.text('Continue'));
    await tester.pump();

    expect(
      find.text('Use a host or IP address, optionally followed by a port.'),
      findsOneWidget,
    );
  });

  testWidgets('a saved favorite PC opens the Remote shell', (tester) async {
    final repository = _repository();
    final device = Device(
      id: 'living-room',
      serverId: 'living-room',
      name: 'Living Room PC',
      host: '192.168.1.20',
      serverIdentity: 'a' * 64,
      clientId: 'client-1',
      credentialReference: 'credential.client-1',
      favorite: true,
    );
    await repository.savePaired(device, 'credential');

    await tester
        .pumpWidget(PhoneRemoteApp(controller: _controller(repository)));
    await tester.pumpAndSettle();

    expect(find.text('Living Room PC'), findsOneWidget);
    expect(find.text('Remote'), findsOneWidget);
    expect(find.text('Devices'), findsOneWidget);
  });

  testWidgets('connected native controls and approved apps reach API v1',
      (tester) async {
    tester.view.physicalSize = const Size(800, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final repository = _repository();
    final device = Device(
      id: 'living-room',
      serverId: 'server-1',
      name: 'Living Room PC',
      host: '192.168.1.20',
      serverIdentity: 'a' * 64,
      clientId: 'client-1',
      credentialReference: 'credential.client-1',
      favorite: true,
    );
    await repository.savePaired(device, 'credential');
    final apiFactory = _apiFactory(
      apps: const <ConfiguredApp>[
        ConfiguredApp(
          id: 'steam',
          name: 'Steam',
          available: true,
          icon: 'default',
        ),
        ConfiguredApp(
          id: 'missing',
          name: 'Missing App',
          available: false,
          icon: 'default',
        ),
      ],
    );

    await tester.pumpWidget(
      PhoneRemoteApp(
        controller: _controller(repository, apiFactory: apiFactory),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Online'), findsOneWidget);
    await tester.ensureVisible(find.text('Back'));
    await tester.tap(find.text('Back'));
    await tester.pump();
    expect(apiFactory.commands, contains('action:escape'));

    await tester.tap(find.text('Apps'));
    await tester.pumpAndSettle();
    expect(find.text('Steam'), findsOneWidget);
    expect(find.text('Missing App'), findsOneWidget);
    expect(find.text('Unavailable'), findsOneWidget);
    await tester.tap(find.text('Steam'));
    await tester.pump();
    expect(apiFactory.commands, contains('launch:steam'));
  });
}

RealDeviceRepository _repository() => RealDeviceRepository(
      metadataStorage: MemoryMetadataStorage(),
      credentialStorage: MemoryCredentialStorage(),
    );

PhoneRemoteController _controller(
  DeviceRepository repository, {
  FakeApiClientFactory? apiFactory,
}) {
  final currentApiFactory = apiFactory ?? _apiFactory();
  return PhoneRemoteController(
    deviceRepository: repository,
    discoveryService: const _EmptyDiscoveryService(),
    pairingService: PairingService(
      apiClientFactory: currentApiFactory,
      deviceRepository: repository,
    ),
    remoteSessionFactory: RealRemoteSessionFactory(
      deviceRepository: repository,
      apiClientFactory: currentApiFactory,
    ),
    wakeService: const UnavailableWakeService('Unavailable in tests.'),
  );
}

FakeApiClientFactory _apiFactory({
  List<ConfiguredApp> apps = const <ConfiguredApp>[],
}) =>
    FakeApiClientFactory(
      info: ServerInfo(
        serverId: 'server-1',
        name: 'Living Room PC',
        version: '1.0.0',
        apiVersion: 1,
        pairing: true,
        identityFingerprint: 'a' * 64,
        certificateFingerprint: 'b' * 64,
      ),
      session: const PairingSession(sessionId: 'session', expiresIn: 300),
      result: PairingResult(
        clientId: 'client-1',
        credential: 'secret',
        serverId: 'server-1',
        identityFingerprint: 'a' * 64,
      ),
      apps: apps,
    );

class _EmptyDiscoveryService implements DiscoveryService {
  const _EmptyDiscoveryService();

  @override
  Future<List<DiscoveredDevice>> discover({
    Duration timeout = const Duration(seconds: 5),
  }) async =>
      const <DiscoveredDevice>[];
}
