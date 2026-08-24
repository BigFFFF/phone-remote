import 'package:phone_remote/data/storage.dart';

class MemoryMetadataStorage implements MetadataStorage {
  final Map<String, String> values = <String, String>{};
  Object? writeError;

  @override
  Future<String?> read(String key) async => values[key];

  @override
  Future<void> write(String key, String value) async {
    final error = writeError;
    if (error != null) {
      throw error;
    }
    values[key] = value;
  }

  @override
  Future<void> delete(String key) async => values.remove(key);
}

class MemoryCredentialStorage implements CredentialStorage {
  final Map<String, String> values = <String, String>{};

  @override
  Future<String?> read(String reference) async => values[reference];

  @override
  Future<void> write(String reference, String credential) async =>
      values[reference] = credential;

  @override
  Future<void> delete(String reference) async => values.remove(reference);
}
