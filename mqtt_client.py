import socket
# Import specific functions from our packer module
from mqtt_packer import build_connect_packet, decode_connack, build_publish_packet, build_subscribe_packet, decode_incoming_packet

class MyMQTTClient:
    def __init__(self, broker_ip, broker_port):
        # We exclusively use the socket module for the communication stack
        # AF_INET = IPv4, SOCK_STREAM = TCP (MQTT requires a reliable stream)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.broker_address = (broker_ip, broker_port)
        # Set a timeout so the application doesn't freeze indefinitely
        self.sock.settimeout(5.0)

    def connect(self, client_id, username=None, password=None, will_topic=None, will_message=None):
        print(f"Attempting to connect to {self.broker_address}...")
        try:
            # 1. Establish the TCP connection
            self.sock.connect(self.broker_address)

            # 2. Build and send the raw MQTT CONNECT packet (now with Auth & Last Will)
            connect_pkt = build_connect_packet(client_id, username, password, will_topic, will_message)
            self.sock.send(connect_pkt)
            print("CONNECT packet sent successfully.")

            # 3. Wait for the broker's acknowledgment (CONNACK packet)
            response = self.sock.recv(1024)
            if response:
                # Folosim decoder-ul nostru din mqtt_packer
                from mqtt_packer import decode_connack
                success, status = decode_connack(response)
                print(f"Status: {status}")
                return success
            else:
                print("Broker closed the connection.")
                return False

        except socket.error as e:
            print(f"Network error occurred: {e}")
            return False

    def publish(self, topic, message):
        """
        Sends a PUBLISH packet over the established socket.
        """
        try:
            # Build the raw MQTT PUBLISH packet
            publish_pkt = build_publish_packet(topic, message)
            # Send the packet over the TCP stream
            self.sock.send(publish_pkt)
            print(f"Published message: '{message}' to topic: '{topic}'")
        except socket.error as e:
            print(f"Failed to publish: {e}")

    def subscribe(self, topic):
        """
        Sends a SUBSCRIBE packet to the broker.
        """
        try:
            sub_pkt = build_subscribe_packet(topic)
            self.sock.send(sub_pkt)
            print(f"Subscribed to topic: '{topic}'")
        except socket.error as e:
            print(f"Failed to subscribe: {e}")

    def check_messages(self):
        """
        Briefly checks the socket for incoming packets without blocking.
        """
        try:
            # Set a very short timeout so the GUI loop doesn't freeze
            self.sock.settimeout(0.1)
            response = self.sock.recv(1024)
            self.sock.settimeout(5.0)  # Restore standard timeout

            if response:
                pkt_type, parsed_data = decode_incoming_packet(response)
                return pkt_type, parsed_data
        except socket.timeout:
            # No data received within 0.1s, restore timeout and move on
            self.sock.settimeout(5.0)
            return None, None
        except socket.error:
            return None, None

        return None, None


if __name__ == "__main__":
    import time
    import psutil  # Required for reading actual CPU/RAM metrics
    from mqtt_packer import build_disconnect_packet  # Import our new packet

    try:
        broker_host = socket.gethostbyname("broker.emqx.io")
        client = MyMQTTClient(broker_host, 1883)

        unique_id = f"Student_Iasi_{int(time.time())}"
        print(f"Generated unique Client ID: {unique_id}")

        if client.connect(unique_id):
            print("--- Ready to send data (Press Ctrl+C to stop) ---")

            topic_cpu = "iasi/student/monitor/cpu"
            topic_ram = "iasi/student/monitor/ram"

            try:
                # Periodic publishing loop
                while True:
                    # Gather real system data
                    cpu_percent = psutil.cpu_percent(interval=None)
                    ram_info = psutil.virtual_memory()

                    cpu_msg = f"CPU Usage: {cpu_percent}%"
                    ram_msg = f"RAM Usage: {ram_info.percent}%"
                    # Publish the telemetry data
                    client.publish(topic_cpu, cpu_msg)
                    client.publish(topic_ram, ram_msg)

                    # Wait for 3 seconds before sending again
                    time.sleep(3)

            except KeyboardInterrupt:
                # Catch Ctrl+C to exit gracefully
                print("\nInitiating graceful shutdown...")

                # Send the official MQTT DISCONNECT packet
                disconnect_pkt = build_disconnect_packet()
                client.sock.send(disconnect_pkt)
                print("DISCONNECT packet sent. Goodbye!")

            finally:
                client.sock.close()

    except socket.gaierror:
        print("Failed to resolve the broker's hostname. Check your internet connection.")