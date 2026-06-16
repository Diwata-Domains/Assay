# Context: TASK-0046

The SQLite store contains all ingested packets. A packet present in the store means verification ran and produced a result. "complete" = packet exists; "not_found" = no matching row. The outcome field maps directly from the packet.
