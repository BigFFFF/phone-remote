import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/models/device.dart';

void main() {
  test('Device round-trips all durable metadata', () {
    final device = Device(
      id: 'local-1',
      serverId: 'server-1',
      name: 'Living Room PC',
      host: '192.168.1.20',
      port: 9443,
      mac: 'AA:BB:CC:DD:EE:FF',
      lastIpv4: '192.168.1.20',
      broadcastAddress: '192.168.1.255',
      serverIdentity: 'a' * 64,
      certificateFingerprint: 'b' * 64,
      clientId: 'client-1',
      credentialReference: 'phone_remote.credential.client-1',
      lastSeen: DateTime.utc(2026, 8, 20, 10, 30),
      favorite: true,
    );

    expect(Device.fromJson(device.toJson()), device);
    expect(device.isPaired, isTrue);
  });

  test('Device rejects invalid durable data', () {
    expect(
      () => Device.fromJson(<String, Object?>{
        'id': 'local-1',
        'serverId': 'server-1',
        'name': 'PC',
        'host': '192.168.1.2',
        'port': 70000,
        'serverIdentity': 'a' * 64,
        'favorite': false,
      }),
      throwsFormatException,
    );
  });
}
