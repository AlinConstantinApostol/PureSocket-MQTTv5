import struct


def build_connect_packet(client_id: str, username: str = None, password: str = None,
                         will_topic: str = None, will_message: str = None) -> bytes:
    """
    Builds an MQTT v5 CONNECT packet manually, with optional Auth and Last Will.
    """
    protocol_name = b"MQTT"
    protocol_len = struct.pack("!H", len(protocol_name))
    protocol_level = b"\x05"

    # Base connect flags: 0x02 means Clean Start=1
    flags_int = 0x02

    # Check if we have Will Topic and Will Message
    has_will = will_topic and will_message
    if has_will:
        flags_int |= 0x04  # Set Bit 2 to 1 (Will Flag)
        # Note: We keep Will QoS at 0 (Bits 3 & 4) and Will Retain at 0 (Bit 5)

    if username:
        flags_int |= 0x80  # Set Bit 7 to 1 (Username Flag)
    if password:
        flags_int |= 0x40  # Set Bit 6 to 1 (Password Flag)

    connect_flags = bytes([flags_int])
    keep_alive = struct.pack("!H", 60)
    properties_len = b"\x00"

    variable_header = protocol_len + protocol_name + protocol_level + connect_flags + keep_alive + properties_len

    # --- Payload ---
    # 1. Client ID
    client_id_bytes = client_id.encode('utf-8')
    payload = struct.pack("!H", len(client_id_bytes)) + client_id_bytes

    # 2. Last Will (MUST appear before Username/Password if flag is set)
    if has_will:
        will_props_len = b"\x00"  # MQTT v5 requires Will Properties Length
        topic_bytes = will_topic.encode('utf-8')
        msg_bytes = will_message.encode('utf-8')

        payload += will_props_len
        payload += struct.pack("!H", len(topic_bytes)) + topic_bytes
        payload += struct.pack("!H", len(msg_bytes)) + msg_bytes

    # 3. Username
    if username:
        user_bytes = username.encode('utf-8')
        payload += struct.pack("!H", len(user_bytes)) + user_bytes

    # 4. Password
    if password:
        pass_bytes = password.encode('utf-8')
        payload += struct.pack("!H", len(pass_bytes)) + pass_bytes

    packet_type = b"\x10"
    remaining_length = len(variable_header) + len(payload)

    return packet_type + bytes([remaining_length]) + variable_header + payload

def decode_connack(data: bytes):
    """
    Decodes an MQTT v5 CONNACK packet to verify connection success.
    """
    if len(data) < 4:
        return False, "Packet too short"

    if data[0] != 0x20:
        return False, f"Unexpected packet type: {hex(data[0])}"

    reason_code = data[2]

    if reason_code == 0x00:
        return True, "Connection Success"
    else:
        return False, f"Connection Refused. Reason Code: {hex(reason_code)}"


def build_publish_packet(topic: str, message: str) -> bytes:
    """
    Builds an MQTT v5 PUBLISH packet (QoS 0) manually.
    """
    # 1. Variable Header (Topic Name + Properties Length)
    topic_bytes = topic.encode('utf-8')
    topic_len = struct.pack("!H", len(topic_bytes))  # Length prefix for the string

    # In MQTT v5, after the topic (and Packet ID if QoS > 0), we need Properties Length
    # For a simple QoS 0 publish, Properties Length is 0
    properties_len = b"\x00"
    variable_header = topic_len + topic_bytes + properties_len

    # 2. Payload (The actual message)
    payload = message.encode('utf-8')

    # 3. Fixed Header (0x30 means PUBLISH with QoS 0, no retain)
    packet_type = b"\x30"
    remaining_length = len(variable_header) + len(payload)

    # Assemble the packet
    return packet_type + bytes([remaining_length]) + variable_header + payload

def build_disconnect_packet() -> bytes:
    """
    Builds an MQTT v5 DISCONNECT packet (Reason Code 0x00 - Normal disconnection).
    """
    # 0xE0 means DISCONNECT packet type (14 << 4). 0x00 means remaining length is 0.
    return b"\xE0\x00"


def build_subscribe_packet(topic: str) -> bytes:
    """
    Builds an MQTT v5 SUBSCRIBE packet manually.
    """
    # 1. Variable Header: Packet Identifier (2 bytes) + Properties Length (1 byte)
    packet_id = struct.pack("!H", 1)  # Arbitrary packet ID = 1
    properties_len = b"\x00"
    variable_header = packet_id + properties_len

    # 2. Payload: Topic Filter Length + Topic Filter + Subscription Options
    topic_bytes = topic.encode('utf-8')
    topic_len = struct.pack("!H", len(topic_bytes))
    # Options: 0x00 means Maximum QoS 0, No Retain Handling
    options = b"\x00"
    payload = topic_len + topic_bytes + options

    # 3. Fixed Header: 0x82 (Subscribe, QoS 1 implied by protocol)
    packet_type = b"\x82"
    remaining_length = len(variable_header) + len(payload)

    return packet_type + bytes([remaining_length]) + variable_header + payload


def decode_incoming_packet(data: bytes):
    """
    Decodes incoming MQTT v5 packets (like SUBACK or PUBLISH).
    Returns a tuple: (packet_type_string, parsed_data)
    """
    if not data or len(data) < 2:
        return None, None

    packet_type = data[0] >> 4  # Get the first 4 bits

    if packet_type == 9:  # 0x90 is SUBACK
        return "SUBACK", None

    elif packet_type == 3:  # 0x30 is PUBLISH
        try:
            # Parse QoS 0 PUBLISH packet
            topic_len = struct.unpack("!H", data[2:4])[0]
            topic = data[4: 4 + topic_len].decode('utf-8')

            # In MQTT v5, after the topic comes Properties Length
            prop_len_index = 4 + topic_len
            prop_len = data[prop_len_index]

            # Payload follows the properties
            payload_index = prop_len_index + 1 + prop_len
            payload = data[payload_index:].decode('utf-8')

            return "PUBLISH", (topic, payload)
        except Exception as e:
            return "ERROR", str(e)

    return "OTHER", None