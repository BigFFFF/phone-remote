import 'dart:typed_data';

import 'package:asn1lib/asn1lib.dart';
import 'package:crypto/crypto.dart';

class CertificateFingerprints {
  const CertificateFingerprints({
    required this.identity,
    required this.certificate,
  });

  final String identity;
  final String certificate;
}

class TlsIdentityVerifier {
  const TlsIdentityVerifier();

  CertificateFingerprints inspect(Uint8List certificateDer) {
    try {
      final certificateFingerprint = sha256.convert(certificateDer).toString();
      final certificate = ASN1Parser(certificateDer).nextObject();
      if (certificate is! ASN1Sequence || certificate.elements.isEmpty) {
        throw const FormatException(
          'The peer did not present an X.509 certificate.',
        );
      }
      final tbsCertificate = certificate.elements.first;
      if (tbsCertificate is! ASN1Sequence || tbsCertificate.elements.isEmpty) {
        throw const FormatException('The certificate body is invalid.');
      }
      final hasExplicitVersion = tbsCertificate.elements.first.tag == 0xa0;
      final publicKeyIndex = hasExplicitVersion ? 6 : 5;
      if (tbsCertificate.elements.length <= publicKeyIndex) {
        throw const FormatException('The certificate has no public key.');
      }
      final subjectPublicKeyInfo = tbsCertificate.elements[publicKeyIndex];
      if (subjectPublicKeyInfo is! ASN1Sequence ||
          subjectPublicKeyInfo.elements.length != 2) {
        throw const FormatException('The certificate public key is invalid.');
      }
      // Hash the exact SubjectPublicKeyInfo DER from the certificate. Rebuilding
      // it is unsafe because some ASN.1 libraries do not round-trip EC points.
      final identityFingerprint =
          sha256.convert(subjectPublicKeyInfo.encodedBytes).toString();
      return CertificateFingerprints(
        identity: identityFingerprint,
        certificate: certificateFingerprint,
      );
    } on FormatException {
      rethrow;
    } catch (error) {
      throw FormatException('Unable to parse the peer certificate.', error);
    }
  }
}
