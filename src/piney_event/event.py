import weakref
import inspect
import logging
from abc import ABC, abstractmethod
from typing import Callable, List, NamedTuple, Optional, Union


_log = logging.getLogger(__name__)


class EventManager(ABC):
    @abstractmethod
    def setup(self, event: "Event") -> None:
        raise NotImplementedError

    @abstractmethod
    def emit(self, event: "Event", *args, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, event: "Event") -> None:
        raise NotImplementedError

    def _do_emit(self, event: "Event", *args) -> None:
        event.emit(*args, managed=False)


class Event:
    class ConnectFlags:
        CONNECT_ONE_SHOT: int = (1 << 0)
        CONNECT_DIRECT: int = (1 << 1)

    class Connection(NamedTuple):
        callback: Callable
        flags: int

    default_manager: Optional[EventManager] = None

    def __init__(self, catch_error: bool = True, manager: Union[EventManager, bool] = True) -> None:
        self.receivers: List[Event.Connection] = []
        self.catch_error: bool = catch_error
        self.log_warn_function: Optional[Callable] = _log.warning
        # Alias `disconnect` to `erase`
        self.disconnect: Callable = self.erase

        if isinstance(manager, bool):
            if manager:
                self.manager: Optional[EventManager] = Event.default_manager
            else:
                self.manager: Optional[EventManager] = None
        else:
            self.manager = manager

        if self.manager is not None:
            self.manager.setup(self)
    
    def __del__(self) -> None:
        if self.manager is not None:
            self.manager.delete(self)

    def connect(self, callback: Callable, flags: int = 0x0) -> None:
        """
        :param callback: A callable that will be called with parameters when event is emitted
        :param flags: An integer bitmask of `Event.ConnectFlags`. For multiple flags, use the `|` operator on all desired values.
        :flag CONNECT_ONE_SHOT: Will disconnect the callback upon the first emit.
        """
        if not callable(callback):
            raise TypeError("Tried to connect non-callable to event!")

        if inspect.ismethod(callback):
            self.receivers.append(Event.Connection(weakref.WeakMethod(callback), flags))
        else:
            self.receivers.append(Event.Connection(weakref.ref(callback), flags))
    
    def erase(self, callback: Callable) -> None:
        """
        Removes the connection to `callback`
        :param callback: The callable that will be erased
        """

        for i in range(len(self.receivers)):
            if self.receivers[i].callback() == callback:
                del self.receivers[i]
                i -= 1
                continue
    
    def clear(self) -> None:
        """
        Erase all callbacks
        """
        self.receivers.clear()
    
    def emit(self, *args, **kwargs) -> None:
        """
        :param args: arguments to be emitted
        """

        if self.manager is None:
            managed = False
        else:
            if "managed" in kwargs.keys():
                managed = kwargs["managed"]
            else:
                managed = True

            if managed:
                self.manager.emit(self, *args, *kwargs)
                return

        for i in range(len(self.receivers)):
            connection = self.receivers[i]
            self.send(connection, *args)
            
    def send(self, connection: Connection, *args) -> bool:
        callback = connection.callback()
        if callback is None:
            del connection
            return False

        signature = inspect.signature(callback)
        num_args = len(args)
        num_params = len(signature.parameters)
        will_cause_error: bool = num_params != num_args

        if self.catch_error:
            if will_cause_error:
                if self.log_warn_function is not None:
                    self.log_warn_function(f"Failed to emit signal | Wrong argument count {num_args}, expected {num_params} | Provided arguments: {args}. Signature: {signature}")
            else:
                callback(*args)
        else:
            callback(*args)
            
        if connection.flags & Event.ConnectFlags.CONNECT_ONE_SHOT:
            del connection
            return False
        
        return True


class TypedEvent(Event):
    """
    Subclass of `Event` with strong-typed parameters
    """
    def __init__(self, *param_types) -> None:
        super().__init__()
        self.param_types = param_types

    def emit(self, *args) -> None:
        emit_types = tuple([type(param) for param in args])
        if emit_types != self.param_types:
            raise TypeError(f"TypedEvent emit expected argument types '{self.param_types}', but got `{emit_types} instead.`")

        super().emit(*args)
    
    def connect(self, callback: Callable, flags: int = 0x0) -> None:
        signature = inspect.signature(callback)
        callback_args = signature.parameters
        l = len(callback_args)
        for p in callback_args:
            if p == 'self':
                l -= 1

        if l != len(self.param_types):
            raise TypeError(f"TypedEvent connect expected argument count of {len(self.param_types)}, but target has {l}. Target signature: `{signature}`")

        super().connect(callback, flags)

def test_default():
    class TestObj():
        def test_cb(self, s: str):
            print(s)

    def test_global_cb(s: str):
        print(s)
    
    e = TypedEvent(str)
    to = TestObj()
    e.connect(to.test_cb, Event.ConnectFlags.CONNECT_ONE_SHOT)
    e.emit("This is working.")
    e.emit("This is not working.")
    e.connect(to.test_cb)
    e.emit("This is working.")
    e.emit("This is working.")
    e.disconnect(to.test_cb)
    e.emit("This is not working.")

    e.connect(test_global_cb, Event.ConnectFlags.CONNECT_ONE_SHOT)
    e.emit("This is working.")
    e.emit("This is not working.")
    e.connect(test_global_cb)
    e.emit("This is working.")
    e.emit("This is working.")
    e.disconnect(test_global_cb)
    e.emit("This is not working.")

    eut = Event()
    eut.connect(to.test_cb)
    eut.emit(1, 5)

    try:
        eut.catch_error = False
        eut.connect(to.test_cb)
        eut.emit(1, 5)
    except TypeError as e:
        print(e)

if __name__ == "__main__":
    test_default()
