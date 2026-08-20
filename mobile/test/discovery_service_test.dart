import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/services/discovery_service.dart';

void main() {
  test('merges duplicate mDNS results by stable server ID', () {
    final merged = DiscoveryMerger.merge(<DiscoveredDevice>[
      const DiscoveredDevice(
        serverId: 'server-1',
        name: 'Living Room PC',
        host: '192.168.1.10',
        port: 8765,
        apiVersion: 1,
        tls: true,
        identityHint: 'aaaaaaaaaaaaaaaa',
      ),
      const DiscoveredDevice(
        serverId: 'server-1',
        name: 'Living Room PC',
        host: '192.168.1.11',
        port: 8765,
        apiVersion: 1,
        tls: true,
      ),
      const DiscoveredDevice(
        serverId: 'server-2',
        name: 'Office PC',
        host: '192.168.1.12',
        port: 8765,
        apiVersion: 1,
        tls: true,
      ),
    ]);

    expect(merged, hasLength(2));
    final livingRoom = merged.singleWhere(
      (device) => device.serverId == 'server-1',
    );
    expect(livingRoom.host, '192.168.1.11');
    expect(livingRoom.identityHint, 'aaaaaaaaaaaaaaaa');
  });
}
