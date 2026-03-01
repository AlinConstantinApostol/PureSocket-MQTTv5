import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import psutil
import socket
from mqtt_client import MyMQTTClient
from mqtt_packer import build_disconnect_packet


class PureSocketGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PureSocket MQTTv5 - Hardware Monitor")
        # Am marit puțin fereastra ca să încapă căsuțele noi
        self.root.geometry("500x600")

        self.client = None
        self.is_publishing = False

        # --- UI Elements ---
        config_frame = tk.LabelFrame(root, text="Broker Configuration", padx=10, pady=10)
        config_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(config_frame, text="Broker Address:").grid(row=0, column=0, sticky="w")
        self.entry_broker = tk.Entry(config_frame, width=30)
        self.entry_broker.insert(0, "broker.emqx.io")
        self.entry_broker.grid(row=0, column=1, pady=2)

        tk.Label(config_frame, text="Port:").grid(row=1, column=0, sticky="w")
        self.entry_port = tk.Entry(config_frame, width=10)
        self.entry_port.insert(0, "1883")
        self.entry_port.grid(row=1, column=1, sticky="w", pady=2)

        tk.Label(config_frame, text="Client ID:").grid(row=2, column=0, sticky="w")
        self.entry_client_id = tk.Entry(config_frame, width=30)
        self.entry_client_id.insert(0, f"Student_Iasi_{int(time.time())}")
        self.entry_client_id.grid(row=2, column=1, pady=2)

        # --- NOILE CÂMPURI PENTRU AUTENTIFICARE ---
        tk.Label(config_frame, text="Username (Optional):").grid(row=3, column=0, sticky="w")
        self.entry_user = tk.Entry(config_frame, width=30)
        self.entry_user.grid(row=3, column=1, pady=2)

        tk.Label(config_frame, text="Password (Optional):").grid(row=4, column=0, sticky="w")
        self.entry_pass = tk.Entry(config_frame, width=30, show="*")  # Ascunde textul cu *
        self.entry_pass.grid(row=4, column=1, pady=2)

        tk.Label(config_frame, text="Will Topic (Optional):").grid(row=5, column=0, sticky="w")
        self.entry_will_topic = tk.Entry(config_frame, width=30)
        self.entry_will_topic.insert(0, "iasi/student/monitor/alerts")
        self.entry_will_topic.grid(row=5, column=1, pady=2)

        tk.Label(config_frame, text="Will Message:").grid(row=6, column=0, sticky="w")
        self.entry_will_msg = tk.Entry(config_frame, width=30)
        self.entry_will_msg.insert(0, "⚠️ OFFLINE UNEXPECTEDLY!")
        self.entry_will_msg.grid(row=6, column=1, pady=2)

        # 3. Control Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)

        self.btn_connect = tk.Button(btn_frame, text="Connect & Start", bg="green", fg="white", width=15,
                                     command=self.start_connection)
        self.btn_connect.grid(row=0, column=0, padx=5)

        self.btn_disconnect = tk.Button(btn_frame, text="Stop & Disconnect", bg="red", fg="white", width=15,
                                        command=self.stop_connection, state=tk.DISABLED)
        self.btn_disconnect.grid(row=0, column=1, padx=5)

        # 4. Console Output Area
        tk.Label(root, text="Telemetry & Logs:").pack(anchor="w", padx=10)
        self.console = scrolledtext.ScrolledText(root, width=55, height=18, state='disabled', bg="#1e1e1e",
                                                 fg="#00ff00")
        self.console.pack(padx=10, pady=5)

    def log(self, message):
        """Helper to print messages directly into the GUI console."""
        self.console.config(state='normal')
        self.console.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.console.see(tk.END)
        self.console.config(state='disabled')

    def start_connection(self):
        broker_address = self.entry_broker.get()
        port = int(self.entry_port.get())
        client_id = self.entry_client_id.get()
        username = self.entry_user.get() if self.entry_user.get() else None
        password = self.entry_pass.get() if self.entry_pass.get() else None

        will_topic = self.entry_will_topic.get() if self.entry_will_topic.get() else None
        will_msg = self.entry_will_msg.get() if self.entry_will_msg.get() else None

        self.btn_connect.config(state=tk.DISABLED)
        self.btn_disconnect.config(state=tk.NORMAL)
        self.is_publishing = True
        self.log(f"Resolving {broker_address}...")

        threading.Thread(target=self.network_worker,
                         args=(broker_address, port, client_id, username, password, will_topic, will_msg),
                         daemon=True).start()

    def network_worker(self, broker_address, port, client_id, username, password, will_topic, will_msg):
        try:
            ip = socket.gethostbyname(broker_address)
            self.client = MyMQTTClient(ip, port)

            if self.client.connect(client_id, username, password, will_topic, will_msg):
                self.log("Status: Connection Success!")

                # --- NOU: Ne abonăm pentru a asculta și alte instanțe ---
                subscribe_topic = "iasi/student/monitor/#"
                self.client.subscribe(subscribe_topic)
                self.log(f"Listening on: {subscribe_topic}")

                topic_cpu = "iasi/student/monitor/cpu"
                topic_ram = "iasi/student/monitor/ram"

                last_publish_time = 0

                while self.is_publishing:
                    # 1. Listen for incoming messages (Non-blocking)
                    pkt_type, parsed_data = self.client.check_messages()
                    if pkt_type == "SUBACK":
                        self.log("Broker confirmed subscription (SUBACK).")
                    elif pkt_type == "PUBLISH":
                        recv_topic, recv_msg = parsed_data
                        self.log(f"📥 IN ({recv_topic}): {recv_msg}")

                    # 2. Publish our own telemetry every 3 seconds
                    current_time = time.time()
                    if current_time - last_publish_time >= 3.0:
                        cpu_percent = psutil.cpu_percent(interval=None)
                        ram_info = psutil.virtual_memory()

                        cpu_msg = f"CPU: {cpu_percent}% | ID: {client_id[-4:]}"
                        ram_msg = f"RAM: {ram_info.percent}% | ID: {client_id[-4:]}"

                        self.client.publish(topic_cpu, cpu_msg)
                        self.client.publish(topic_ram, ram_msg)


                        last_publish_time = current_time

                    time.sleep(0.01)
            else:
                self.log("Failed to connect to broker.")
                self.reset_buttons()

        except socket.error as e:
            self.log(f"Network Error: {e}")
            self.reset_buttons()

    def stop_connection(self):
        """Called when the Disconnect button is pressed."""
        self.is_publishing = False
        self.log("Initiating graceful shutdown...")

        if self.client and self.client.sock:
            try:
                disconnect_pkt = build_disconnect_packet()
                self.client.sock.send(disconnect_pkt)
                self.log("DISCONNECT packet sent. Goodbye!")
                self.client.sock.close()
            except socket.error:
                pass

        self.reset_buttons()

    def reset_buttons(self):
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = PureSocketGUI(root)
    # If user closes window, ensure socket is closed
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop_connection(), root.destroy()))
    root.mainloop()