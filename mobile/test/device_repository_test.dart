import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/models/device.dart';
import 'package:phone_remote/repositories/device_repository.dart';

import 'support/memory_storage.dart';

void main() {
  late MemoryMetadataStorage metadata;
  late MemoryCredentialStorage credentials;
  late RealDeviceRepository repository;

  setUp(() {
    metadata = MemoryMetadataStorage();
    credentials = MemoryCredentialStorage();
    repository = RealDeviceRepository(
      metadataStorage: metadata,
      credentialStorage: credentials,
    );
  });

  test('stores credential only in secure storage', () async {
    final device = _device(serverId: 'server-1', clientId: 'client-1');

    await repository.savePaired(device, 'top-secret-credential');

    expect(await repository.getAll(), <Device>[device]);
    expect(await repository.readCredential(device), 'top-secret-credential');
    expect(metadata.values.values.single,
        isNot(contains('top-secret-credential')));
    expect(
      credentials.values,
      <String, String>{
        'phone_remote.credential.client-1': 'top-secret-credential',
      },
    );
  });

  test('supports multiple PCs and keeps favorites first', () async {
    final office = _device(serverId: 'office', clientId: 'client-office');
    final livingRoom = _device(
      serverId: 'living-room',
      clientId: 'client-living-room',
      favorite: true,
    );

    await repository.savePaired(office, 'office-secret');
    await repository.savePaired(livingRoom, 'living-room-secret');

    expect(
      (await repository.getAll()).map((device) => device.serverId),
      <String>['living-room', 'office'],
    );
  });

  test('updates a known server without duplicating it', () async {
    final original = _device(serverId: 'server-1', clientId: 'client-1');
    await repository.savePaired(original, 'secret-1');

    final updated = original.copyWith(host: '192.168.1.99', name: 'Renamed PC');
    await repository.save(updated);

    final devices = await repository.getAll();
    expect(devices, hasLength(1));
    expect(devices.single.host, '192.168.1.99');
    expect(devices.single.name, 'Renamed PC');
  });

  test('removing one PC removes only its credential', () async {
    final first = _device(serverId: 'first', clientId: 'client-first');
    final second = _device(serverId: 'second', clientId: 'client-second');
    await repository.savePaired(first, 'first-secret');
    await repository.savePaired(second, 'second-secret');

    await repository.remove(first);

    expect((await repository.getAll()).single, second);
    expect(await repository.readCredential(first), isNull);
    expect(await repository.readCredential(second), 'second-secret');
  });
}

Device _device({
  required String serverId,
  required String clientId,
  bool favorite = false,
}) {
  return Device(
    id: serverId,
    serverId: serverId,
    name: '$serverId PC',
    host: '192.168.1.20',
    serverIdentity: 'a' * 64,
    certificateFingerprint: 'b' * 64,
    clientId: clientId,
    credentialReference: 'phone_remote.credential.$clientId',
    favorite: favorite,
  );
}
