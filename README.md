# PureSocket-MQTTv5 🔌

> A lightweight, highly-customized MQTT v5 client built entirely from scratch using Python 3 and the Berkeley Sockets API. 

This project demonstrates a deep, low-level understanding of network protocols by strictly avoiding high-level communication libraries (like `paho-mqtt`). Every byte sent over the TCP stream is manually serialized and deserialized according to the OASIS MQTT v5.0 specification.

## 🎯 Technical Highlights & Constraints
Developed as an advanced Computer Networks academic project, the core constraint was to use **only the standard `socket` and `struct` modules** for network communication. 

This required manual implementation of:
* TCP Handshaking and Socket Lifecycle Management.
* Bit-level packet construction (Bit-shifting for Connect Flags, QoS, etc.).
* Non-blocking socket reads for asynchronous Publish/Subscribe architecture.
* Multi-threading to keep the GUI responsive while handling the network loop.

## ✨ Features Implemented
* **MQTT v5 Protocol Support:**
  * `CONNECT` & `CONNACK` (with protocol validation).
  * **Authentication:** Username and Password support via Connect Flags.
  * **Last Will and Testament (LWT):** Graceful degradation alerts if the client drops unexpectedly.
  * `PUBLISH` (QoS 0) & `SUBSCRIBE` / `SUBACK`.
  * `DISCONNECT`: Graceful shutdown implementation.
* **Hardware Telemetry:** Dynamically reads CPU and RAM usage via `psutil` and publishes it periodically.
* **Asynchronous GUI:** A Tkinter-based dashboard for broker configuration, real-time telemetry logging, and cross-client monitoring.

## 🗂️ Repository Structure

```text
PureSocket-MQTTv5/
├── src/
│   ├── mqtt_packer.py    # The "Factory" - Bit-level serialization & parsing of MQTT packets
│   ├── mqtt_client.py    # The "Brain" - TCP Socket lifecycle, routing, and threading
│   └── main_gui.py       # The "Face" - Tkinter async dashboard
├── docs/                 # Academic requirements and architecture documentation
├── requirements.txt      # Python dependencies (psutil)
└── README.md             # You are here
