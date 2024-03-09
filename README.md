# A tiny Event System for Python

Example:
``` python
from event import Event, TypedEvent

my_event = Event()
my_typed_event = TypedEvent(str, float)

def receiver(arg1, arg2):
    print(arg1, arg2)

def typed_receiver(arg1: str, arg2: float):
    print(arg1, arg2)

if __name__ == "__main__":
    my_event.connect(receiver)
    my_event.emit("Hi", 8)
    my_typed_event.connect(typed_receiver)
    my_typed_event.emit("Bye", 9.0)
```


