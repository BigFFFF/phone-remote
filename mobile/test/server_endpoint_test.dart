import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/models/server_endpoint.dart';

void main() {
  test('manual endpoint accepts host, IPv4, and an explicit port', () {
    expect(
      ServerEndpoint.parse('living-room.local'),
      const ServerEndpoint(host: 'living-room.local'),
    );
    expect(
      ServerEndpoint.parse('192.168.1.20:9443'),
      const ServerEndpoint(host: '192.168.1.20', port: 9443),
    );
    expect(
      ServerEndpoint.parse('https://[fe80::1]:8765'),
      const ServerEndpoint(host: 'fe80::1'),
    );
  });

  test('manual endpoint rejects unsafe URL components and cleartext', () {
    for (final value in <String>[
      'http://192.168.1.20',
      'https://user@example.test',
      'https://example.test/api',
      'https://example.test?token=secret',
      'https://example.test#fragment',
    ]) {
      expect(() => ServerEndpoint.parse(value), throwsFormatException);
    }
  });

  test('API URI is fixed to HTTPS and API v1', () {
    final endpoint = ServerEndpoint.parse('192.168.1.20:9443');
    expect(
      endpoint.apiUri('/info').toString(),
      'https://192.168.1.20:9443/api/v1/info',
    );
  });
}
