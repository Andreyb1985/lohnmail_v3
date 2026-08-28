from __future__ import annotations

from typing import Any, Callable
from weakref import WeakKeyDictionary


class _BoundSignal:
    def __init__(self) -> None:
        self._callbacks: list[Callable[..., Any]] = []

    def connect(self, callback: Callable[..., Any]) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def emit(self, *args: Any) -> None:
        for callback in tuple(self._callbacks):
            callback(*args)


class Signal:
    def __init__(self, *_types: type) -> None:
        self._instances: WeakKeyDictionary[object, _BoundSignal] = WeakKeyDictionary()

    def __get__(self, instance: object | None, owner: type | None = None) -> Signal | _BoundSignal:
        if instance is None:
            return self
        signal = self._instances.get(instance)
        if signal is None:
            signal = _BoundSignal()
            self._instances[instance] = signal
        return signal


def Slot(*_types: type, **_kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorate(function: Callable[..., Any]) -> Callable[..., Any]:
        return function

    return decorate


class QObject:
    def __init__(self, _parent: object | None = None) -> None:
        pass

    def deleteLater(self) -> None:
        pass

    def moveToThread(self, _thread: object) -> None:
        pass


class QWidget:
    pass
