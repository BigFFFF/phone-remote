import 'dart:async';

typedef PointerMoveSender = Future<void> Function(double dx, double dy);
typedef PointerMoveErrorHandler = void Function(Object error);

class PointerMoveDispatcher {
  PointerMoveDispatcher({
    required PointerMoveSender send,
    this.interval = const Duration(milliseconds: 33),
    PointerMoveErrorHandler? onError,
  })  : _send = send,
        _onError = onError;

  final PointerMoveSender _send;
  final PointerMoveErrorHandler? _onError;
  final Duration interval;

  Timer? _timer;
  double _pendingDx = 0;
  double _pendingDy = 0;
  bool _sending = false;
  bool _disposed = false;

  void add(double dx, double dy) {
    if (_disposed || (!dx.isFinite || !dy.isFinite)) {
      return;
    }
    _pendingDx += dx;
    _pendingDy += dy;
    _schedule();
  }

  void _schedule() {
    if (_disposed || _sending || _timer != null) {
      return;
    }
    _timer = Timer(interval, () {
      _timer = null;
      unawaited(_flush());
    });
  }

  Future<void> _flush() async {
    if (_disposed || _sending) {
      return;
    }
    final dx = _pendingDx;
    final dy = _pendingDy;
    _pendingDx = 0;
    _pendingDy = 0;
    if (dx == 0 && dy == 0) {
      return;
    }
    _sending = true;
    try {
      await _send(dx, dy);
    } catch (error) {
      _onError?.call(error);
    } finally {
      _sending = false;
      if (_pendingDx != 0 || _pendingDy != 0) {
        _schedule();
      }
    }
  }

  void dispose() {
    _disposed = true;
    _timer?.cancel();
    _timer = null;
    _pendingDx = 0;
    _pendingDy = 0;
  }
}
