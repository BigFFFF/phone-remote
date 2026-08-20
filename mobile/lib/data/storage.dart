import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

abstract interface class MetadataStorage {
  Future<String?> read(String key);

  Future<void> write(String key, String value);

  Future<void> delete(String key);
}

class SharedPreferencesMetadataStorage implements MetadataStorage {
  SharedPreferencesMetadataStorage([SharedPreferencesAsync? preferences])
      : _preferences = preferences ?? SharedPreferencesAsync();

  final SharedPreferencesAsync _preferences;

  @override
  Future<String?> read(String key) => _preferences.getString(key);

  @override
  Future<void> write(String key, String value) =>
      _preferences.setString(key, value);

  @override
  Future<void> delete(String key) => _preferences.remove(key);
}

abstract interface class CredentialStorage {
  Future<String?> read(String reference);

  Future<void> write(String reference, String credential);

  Future<void> delete(String reference);
}

class SecureCredentialStorage implements CredentialStorage {
  SecureCredentialStorage([FlutterSecureStorage? storage])
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  @override
  Future<String?> read(String reference) => _storage.read(key: reference);

  @override
  Future<void> write(String reference, String credential) =>
      _storage.write(key: reference, value: credential);

  @override
  Future<void> delete(String reference) => _storage.delete(key: reference);
}
