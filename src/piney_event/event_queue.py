import event
from piney_event.event import EventManager, Event
from typing import List, NamedTuple


class EventQueue(EventManager):
    class EmitObj(NamedTuple):
        event: Event
        args: tuple
        receivers: List[Event.Connection]

    def __init__(self):
        self.events: List[Event] = []
        self.emit_queue: List[EventQueue.EmitObj] = []

    def execute_all(self) -> None:
        self.execute(self.queued_count())

    def execute(self, num_emits: int = 1) -> None:
        for _ in range(num_emits):
            if self.empty():
                return
            emit_obj = self.emit_queue.pop(0)

            for connection in emit_obj.receivers:
                emit_obj.event.send(connection, *emit_obj.args)

    def queued_count(self) -> int:
        return len(self.emit_queue)

    def empty(self) -> bool:
        return len(self.emit_queue) == 0

    def setup(self, event: Event) -> None:
        self.events.append(event)

    def emit(self, event: Event, *args, **kwargs) -> None:
        self.emit_queue.append(EventQueue.EmitObj(
            event, args,
            [c for c in event.receivers if c.flags & Event.ConnectFlags.CONNECT_DIRECT == 0]
        ))

    def delete(self, event: Event) -> None:
        self.events.remove(event)


def test_queue():
    class TestObj():
        def test_cb(self, s: str):
            print(s)

    event_queue = EventQueue()
    Event.default_manager = event_queue

    e = Event()
    to = TestObj()

    e.connect(to.test_cb)
    e.emit("1")
    e.emit("2")
    e.emit("3")
    e.emit("4")

    e.disconnect(to.test_cb)
    e.emit("5")

    event_queue.execute_all()


if __name__ == "__main__":
    test_queue()
