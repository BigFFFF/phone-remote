import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/models/api_models.dart';

void main() {
  test('parses authenticated status and approved apps strictly', () {
    final status = ServerStatus.fromJson(<String, Object?>{
      'ok': true,
      'serverId': 'server-1',
      'name': 'Living Room PC',
      'version': '1.0.0',
      'apiVersion': 1,
      'addresses': <Object?>['192.168.1.20'],
      'port': 8765,
      'configOk': false,
      'configError': 'Review one setting.',
      'wakeTargets': <Object?>[
        <String, Object?>{
          'mac': '00:11:22:33:44:55',
          'address': '192.168.1.20',
          'broadcast': '192.168.1.255',
        },
      ],
    });
    final app = ConfiguredApp.fromJson(<String, Object?>{
      'id': 'steam',
      'name': 'Steam',
      'available': true,
      'icon': '/api/v1/apps/steam/icon',
    });

    expect(status.serverId, 'server-1');
    expect(status.addresses, <String>['192.168.1.20']);
    expect(status.configOk, isFalse);
    expect(status.wakeTargets.single.broadcast, '192.168.1.255');
    expect(app.id, 'steam');
    expect(app.available, isTrue);
  });

  test('rejects malformed status and arbitrary app identifiers', () {
    expect(
      () => ServerStatus.fromJson(<String, Object?>{
        'serverId': 'server-1',
        'name': 'PC',
        'version': '1.0.0',
        'apiVersion': 1,
        'addresses': <Object?>['not-an-address', 12],
        'port': 8765,
        'configOk': true,
      }),
      throwsFormatException,
    );
    expect(
      () => ConfiguredApp.fromJson(<String, Object?>{
        'id': '../../cmd',
        'name': 'Unsafe',
        'available': true,
        'icon': 'default',
      }),
      throwsFormatException,
    );
  });
}
