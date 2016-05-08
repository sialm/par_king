from struct import pack
from struct import unpack


ENCODING = '!HLLL'
PADDING = 0
MESSAGE_TYPE_INIT = 1
MESSAGE_TYPE_IN = 2
MESSAGE_TYPE_OUT = 3
MESSAGE_TYPE_ALIVE = 4
MESSAGE_TYPE_RESPONSE = 5
MESSAGE_TYPE_ERROR = 6


def pack_init_packet(lot_id, capacity, vacancies):
    """
    packs the init packet as defined by the par king protocol
    :param int lot_id:
    :param int capacity:
    :param int vacancies:
    :return:
    """
    packet = pack(ENCODING, MESSAGE_TYPE_INIT, lot_id, capacity, vacancies)
    return packet


def pack_in_packet(lot_id, z_value):
    """
    packs the in packet as defined by the par king protocol
    :param int lot_id:
    :param int|float  z_value:
    :return:
    """
    packet = pack(ENCODING, MESSAGE_TYPE_IN, lot_id, z_value, PADDING)
    return packet


def pack_out_packet(lot_id, z_value):
    """
    packs the out packet as defined by the par king protocol
    :param int lot_id:
    :param int|float z_value
    :return:
    """
    packet = pack(ENCODING, MESSAGE_TYPE_OUT, lot_id, z_value, PADDING)
    return packet


def pack_alive_packet(lot_id):
    """
    packs the alive packet as defined by the par king protocol
    :param int lot_id:
    :return:
    """
    packet = pack(ENCODING, MESSAGE_TYPE_ALIVE, lot_id, PADDING, PADDING)
    return packet


def pack_response_packet(available_spaces, error_code=None):
    """
    packs the response packet from the server
    :param int available_spaces:
    :param int error_code:
    :return:
    """
    packet = pack(ENCODING, MESSAGE_TYPE_RESPONSE, available_spaces, error_code)
    return packet


def unpack_packet(packet):
    """
    unpacks a packet as defined by the par king protocol
    :param packet:
    :return: tuple (message_type, lot_id, capacity|padding, vacancies|padding)
    """
    packet = unpack(ENCODING, packet)
    return packet
