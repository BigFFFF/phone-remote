import 'package:flutter/material.dart';

import '../application/phone_remote_controller.dart';
import '../localization.dart';
import '../models/server_endpoint.dart';
import '../services/api_client.dart';
import 'pairing_screen.dart';
import 'remote_shell.dart';

class FindComputersScreen extends StatefulWidget {
  const FindComputersScreen({super.key, required this.controller});

  final PhoneRemoteController controller;

  @override
  State<FindComputersScreen> createState() => _FindComputersScreenState();
}

class _FindComputersScreenState extends State<FindComputersScreen> {
  bool _preparingPairing = false;

  Future<void> _discover() async {
    try {
      await widget.controller.discover();
    } on Object catch (error) {
      if (mounted) {
        _showError(error);
      }
    }
  }

  Future<void> _manualAddress() async {
    final input = await showDialog<String>(
      context: context,
      builder: (context) => const _ManualAddressDialog(),
    );
    if (input == null || !mounted) {
      return;
    }
    try {
      await _startPairing(ServerEndpoint.parse(input));
    } on Object catch (error) {
      if (mounted) {
        _showError(error);
      }
    }
  }

  Future<void> _startPairing(ServerEndpoint endpoint) async {
    if (_preparingPairing) {
      return;
    }
    setState(() => _preparingPairing = true);
    try {
      final attempt = await widget.controller.beginPairing(endpoint);
      if (!mounted) {
        return;
      }
      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => PairingScreen(
            controller: widget.controller,
            attempt: attempt,
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _preparingPairing = false);
      }
    }
  }

  void _showError(Object error) {
    final message = switch (error) {
      ApiException() => error.message,
      FormatException() => error.message,
      _ =>
        context.tr('Unable to find that PC. Check the address and try again.'),
    };
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message.toString())),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(context.tr('Find your PC'))),
      body: AnimatedBuilder(
        animation: widget.controller,
        builder: (context, _) {
          final results = widget.controller.discoveredDevices;
          return ListView(
            padding: const EdgeInsets.all(24),
            children: <Widget>[
              Icon(
                Icons.laptop_windows_rounded,
                size: 64,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: widget.controller.searching ? null : _discover,
                icon: widget.controller.searching
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.radar_rounded),
                label: Text(
                  widget.controller.searching
                      ? context.tr('Finding Computers…')
                      : context.tr('Find Computers'),
                ),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: _preparingPairing ? null : _manualAddress,
                icon: const Icon(Icons.edit_location_alt_outlined),
                label: Text(context.tr('Enter Address Manually')),
              ),
              const SizedBox(height: 12),
              TextButton.icon(
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const RemoteShell.demo(),
                    ),
                  );
                },
                icon: const Icon(Icons.play_circle_outline_rounded),
                label: Text(context.tr('Try Demo')),
              ),
              if (_preparingPairing) ...<Widget>[
                const SizedBox(height: 24),
                const LinearProgressIndicator(),
                const SizedBox(height: 8),
                Text(
                  context.tr(
                      'Creating a secure pairing session on the Windows PC…'),
                  textAlign: TextAlign.center,
                ),
              ],
              if (results.isNotEmpty) ...<Widget>[
                const SizedBox(height: 32),
                Text(context.tr('Available'),
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                for (final device in results)
                  Card(
                    child: ListTile(
                      leading: const CircleAvatar(
                        child: Icon(Icons.computer_rounded),
                      ),
                      title: Text(device.name),
                      subtitle: Text(
                        device.apiVersion == 1 && device.tls
                            ? '${device.host} • ${context.tr('Secure API v1')}'
                            : '${device.host} • ${context.tr('Update required')}',
                      ),
                      trailing: FilledButton.tonal(
                        onPressed: device.apiVersion == 1 &&
                                device.tls &&
                                !_preparingPairing
                            ? () async {
                                try {
                                  await _startPairing(
                                    ServerEndpoint(
                                      host: device.host,
                                      port: device.port,
                                    ),
                                  );
                                } on Object catch (error) {
                                  if (mounted) {
                                    _showError(error);
                                  }
                                }
                              }
                            : null,
                        child: Text(context.tr('Pair')),
                      ),
                    ),
                  ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _ManualAddressDialog extends StatefulWidget {
  const _ManualAddressDialog();

  @override
  State<_ManualAddressDialog> createState() => _ManualAddressDialogState();
}

class _ManualAddressDialogState extends State<_ManualAddressDialog> {
  final _controller = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    try {
      ServerEndpoint.parse(_controller.text);
      Navigator.of(context).pop(_controller.text.trim());
    } on FormatException catch (error) {
      setState(() => _error = error.message.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(context.tr('Enter PC address')),
      content: TextField(
        controller: _controller,
        autofocus: true,
        keyboardType: TextInputType.url,
        textInputAction: TextInputAction.done,
        decoration: InputDecoration(
          hintText: '192.168.1.20:8765',
          errorText: _error,
        ),
        onSubmitted: (_) => _submit(),
      ),
      actions: <Widget>[
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(context.tr('Cancel')),
        ),
        FilledButton(onPressed: _submit, child: Text(context.tr('Continue'))),
      ],
    );
  }
}
