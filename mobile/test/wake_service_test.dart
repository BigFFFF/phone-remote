import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/models/device.dart';
import 'package:phone_remote/services/wake_service.dart';

void main() {
  test('builds the standard 102-byte Wake on LAN magic packet', () {
    final packet = UdpWakeService.buildMagicPacket(
      const <int>[0x00, 0x11, 0x22, 0x33, 0x44, 0x55],
    );

    expect(packet, hasLength(102));
    expect(packet.take(6), everyElement(0xff));
    for (var offset = 6; offset < packet.length; offset += 6) {
      expect(
        packet.sublist(offset, offset + 6),
        const <int>[0x00, 0x11, 0x22, 0x33, 0x44, 0x55],
      );
    }
  });

  test('prefers the saved directed broadcast and also sends limited broadcast',
      () async {
    Uint8List? sentPacket;
    List<InternetAddress>? sentTargets;
    int? sentPort;
    final service = UdpWakeService(
      sender: (packet, targets, port) async {
        sentPacket = packet;
        sentTargets = targets;
        sentPort = port;
      },
    );
    final device = _device(
      mac: '00:11:22:33:44:55',
      broadcastAddress: '192.168.1.255',
    );

    expect(
      (await service.capability(device)).availability,
      WakeAvailability.available,
    );
    await service.wake(device);

    expect(sentPacket, hasLength(102));
    expect(sentTargets?.map((target) => target.address), <String>[
      '192.168.1.255',
      '255.255.255.255',
    ]);
    expect(sentPort, 9);
  });

  test('reports a missing or malformed MAC without opening a socket', () async {
    final service = UdpWakeService(
      sender: (_, __, ___) async => fail('sender must not be called'),
    );

    final capability = await service.capability(_device(mac: 'invalid'));

    expect(capability.availability, WakeAvailability.unavailable);
    expect(() => service.wake(_device(mac: 'invalid')), throwsStateError);
  });
}

Device _device({String? mac, String? broadcastAddress}) => Device(
      id: 'pc',
      serverId: 'pc',
      name: 'PC',
      host: '192.168.1.20',
      mac: mac,
      broadcastAddress: broadcastAddress,
      serverIdentity: 'a' * 64,
      clientId: 'client',
      credentialReference: 'credential.client',
    );
