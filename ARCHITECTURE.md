# System Architecture: PureSocket-MQTTv5

This document outlines the engineering decisions, trade-offs, and architectural patterns used to build an MQTT v5 client from scratch without relying on high-level networking libraries.

## 1. Separation of Concerns (Modularity)
The project is strictly divided into three layers to ensure maintainability and testability:
* **The Application/UI Layer (`main_gui.py`):** Handles user interactions and state management.
* **The Network Layer (`mqtt_client.py`):** Manages the TCP socket lifecycle, DNS resolution, and stream state.
* **The Protocol/Serialization Layer (`mqtt_packer.py`):** A pure, stateless module dedicated to byte-level packet assembly and disassembly. 

## 2. The Network Model: Pure Sockets over TCP
Instead of using `paho-mqtt` or `asyncio`, this project interfaces directly with the OS's Berkeley Sockets API (`socket` module). 
* **Reliability:** MQTT requires a lossless, ordered stream, hence `SOCK_STREAM` (TCP) over IPv4 (`AF_INET`).
* **Non-Blocking Reads:** To implement the Publish/Subscribe pattern, the client must constantly listen for incoming packets (`PUBLISH`, `SUBACK`). To prevent the `recv()` call from blocking the entire application, a short timeout (`sock.settimeout(0.1)`) is applied during the checking phase, allowing the loop to continue if no data is present.

## 3. Concurrency: Multithreading vs Async
A Tkinter GUI runs an infinite blocking loop (`mainloop()`). If the TCP socket operations ran on the same thread, the GUI would freeze entirely.
* **Decision:** We use Python's `threading` module to spawn a `daemon=True` background worker. 
* **Execution:** The main thread handles the UI, while the background thread handles the `while True` network loop (publishing telemetry and polling for incoming messages). If the UI thread dies, the daemon thread safely terminates.

## 4. Bit-Level Protocol Implementation (MQTT v5)
Constructing MQTT packets from scratch requires strict adherence to the OASIS specification, particularly bitwise operations for control flags.

**Example: The CONNECT Packet Flags**
To support features like Authentication and Last Will and Testament (LWT) dynamically, the Connect Flags byte is constructed using bitwise OR operations:
```python
flags_int = 0x02  # Clean Start (Bit 1)

if has_will:
    flags_int |= 0x04  # Set Bit 2 to 1 (Will Flag)
if username:
    flags_int |= 0x80  # Set Bit 7 to 1 (Username Flag)
if password:
    flags_int |= 0x40  # Set Bit 6 to 1 (Password Flag)
