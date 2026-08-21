import 'dart:io';
import 'dart:typed_data';

import '../models/device.dart';

enum WakeAvailability { available, unavailable }

class WakeCapability {
  const WakeCapability.available()
      : availability = WakeAvailability.available,
        unavailableReason = null;

  const WakeCapability.unavailable(this.unavailableReason)
      : availability = WakeAvailability.unavailable;

  final WakeAvailability availability;
  final String? unavailableReason;
}

abstract interface class WakeService {
  Future<WakeCapability> capability(Device device);

  Future<void> wake(Device device);
}

class UnavailableWakeService implements WakeService {
  const UnavailableWakeService(this.reason);

  final String reason;

  @override
  Future<WakeCapability> capability(Device device) async =>
      WakeCapability.unavailable(reason);

  @override
  Future<void> wake(Device device) {
    throw StateError(reason);
  }
}

typedef WakeDatagramSender = Future<void> Function(
  Uint8List packet,
  List<InternetAddress> targets,
  int port,
);
typedef WakeDelay = Future<void> Function(Duration duration);

class UdpWakeService implements WakeService {
  UdpWakeService({
    WakeDatagramSender? sender,
    this.port = 9,
    this.repetitions = 3,
    this.repetitionInterval = const Duration(milliseconds: 80),
    WakeDelay? delay,
  })  : assert(repetitions > 0),
        _sender = sender ?? _sendDatagram,
        _delay = delay ?? Future<void>.delayed;

  final WakeDatagramSender _sender;
  final WakeDelay _delay;
  final int port;
  final int repetitions;
  final Duration repetitionInterval;

  @override
  Future<WakeCapability> capability(Device device) async {
    if (_parseMac(device.mac) == null) {
      return const WakeCapability.unavailable(
        'This PC does not have a valid saved MAC address.',
      );
    }
    return const WakeCapability.available();
  }

  @override
  Future<void> wake(Device device) async {
    final mac = _parseMac(device.mac);
    if (mac == null) {
      throw StateError('This PC does not have a valid saved MAC address.');
    }
    final targets = <InternetAddress>[];
    final directed = _ipv4(device.broadcastAddress);
    if (directed != null) {
      targets.add(directed);
    }
    final limited = InternetAddress('255.255.255.255');
    if (targets.every((target) => target.address != limited.address)) {
      targets.add(limited);
    }
    final packet = buildMagicPacket(mac);
    for (var repetition = 0; repetition < repetitions; repetition += 1) {
      await _sender(packet, targets, port);
      if (repetition + 1 < repetitions) {
        await _delay(repetitionInterval);
      }
    }
  }

  static Uint8List buildMagicPacket(List<int> mac) {
    if (mac.length != 6 || mac.any((part) => part < 0 || part > 255)) {
      throw const FormatException('A MAC address must contain six bytes.');
    }
    final packet = Uint8List(6 + (16 * mac.length));
    packet.fillRange(0, 6, 0xff);
    for (var repetition = 0; repetition < 16; repetition += 1) {
      packet.setRange(6 + (repetition * 6), 12 + (repetition * 6), mac);
    }
    return packet;
  }

  static List<int>? _parseMac(String? value) {
    if (value == null) {
      return null;
    }
    final normalized = value.replaceAll(RegExp(r'[^a-fA-F0-9]'), '');
    if (!RegExp(r'^[a-fA-F0-9]{12}$').hasMatch(normalized)) {
      return null;
    }
    return <int>[
      for (var index = 0; index < 12; index += 2)
        int.parse(normalized.substring(index, index + 2), radix: 16),
    ];
  }

  static InternetAddress? _ipv4(String? value) {
    if (value == null) {
      return null;
    }
    final address = InternetAddress.tryParse(value);
    return address?.type == InternetAddressType.IPv4 ? address : null;
  }

  static Future<void> _sendDatagram(
    Uint8List packet,
    List<InternetAddress> targets,
    int port,
  ) async {
    final socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
    try {
      socket.broadcastEnabled = true;
      for (final target in targets) {
        socket.send(packet, target, port);
      }
    } finally {
      socket.close();
    }
  }
}
