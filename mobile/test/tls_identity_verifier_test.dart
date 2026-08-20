import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:phone_remote/services/tls_identity_verifier.dart';

void main() {
  test('rejects malformed certificate data', () {
    expect(
      () => const TlsIdentityVerifier()
          .inspect(Uint8List.fromList(<int>[1, 2, 3])),
      throwsFormatException,
    );
  });
}
