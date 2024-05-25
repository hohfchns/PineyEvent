import weakref
import inspect

class Event:
    def __init__(self) -> None:
        self.receivers: list = []
        self.ignore_error = True
        # Alias `disconnect` to `erase`
        self.disconnect = self.erase
    
    def connect(self, callback) -> None:
        """
        :param callback: - A callable that will be called with parameters when event is emitted
        """
        if not callable(callback):
            raise TypeError("Tried to connect non-callable to event!")

        if inspect.ismethod(callback):
            self.receivers.append(weakref.WeakMethod(callback))
        else:
            self.receivers.append(weakref.ref(callback))
    
    def erase(self, callback) -> None:
        """
        Removes the connection to `callback`
        :param callback: - The callable that will be erased
        """

        self.receivers.remove(callback)
    
    def clear(self) -> None:
        """
        Erase all callbacks
        """
        self.receivers.clear()
    
    def emit(self, *args) -> None:
        """
        :param args: - arguments to be emitted
        """
        for i in range(len(self.receivers)):
            callback = self.receivers[i]()
            if callback is None:
                del self.receivers[i]
                i -= 1
                continue

            if self.ignore_error:
                try:
                    callback(*args)
                except TypeError:
                        pass
            else:
                callback(*args)

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
    
    def connect(self, callback) -> None:
        callback_args = inspect.signature(callback).parameters
        l = len(callback_args)
        for p in callback_args:
            if p == 'self':
                l -= 1

        if l != len(self.param_types):
            raise TypeError(f"TypedEvent connect expected argument count of {len(self.param_types)}, but target has {l}. Target params: `{callback.__code__.co_varnames}`")

        super().connect(callback)

if __name__ == "__main__":
    class TestObj():
        def test_cb(self, s: str):
            print(s)
    
    e = TypedEvent(str)
    to = TestObj()
    e.connect(to.test_cb)
    e.emit("This is working.")

