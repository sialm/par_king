from struct import pack
from struct import unpack


class ParKingPacket:
    ENCODING = '!HLLL'
    PADDING = 0
    MESSAGE_TYPE_INIT = 1
    MESSAGE_TYPE_IN = 2
    MESSAGE_TYPE_OUT = 3
    MESSAGE_TYPE_ALIVE = 4

    def pack_init_packet(self, lot_id, capacity, vacancies):
        """
        packs the init packet as defined by the par king protocol
        :param lot_id:
        :param capacity:
        :param vacancies:
        :return:
        """
        packet = pack(self.ENCODING, self.MESSAGE_TYPE_INIT, lot_id, capacity, vacancies)
        return packet

    def pack_in_packet(self, lot_id, z_value):
        """
        packs the in packet as defined by the par king protocol
        :param lot_id:
        :param z_value:
        :return:
        """
        packet = pack(self.ENCODING, self.MESSAGE_TYPE_IN, lot_id, z_value, self.PADDING)
        return packet

    def pack_out_packet(self, lot_id, z_value):
        """
        packs the out packet as defined by the par king protocol
        :param lot_id:
        :param z_value
        :return:
        """
        packet = pack(self.ENCODING, self.MESSAGE_TYPE_OUT, lot_id, z_value, self.PADDING)
        return packet

    def pack_alive_packet(self, lot_id):
        """
        packs the alive packet as defined by the par king protocol
        :param lot_id:
        :return:
        """
        packet = pack(self.ENCODING, self.MESSAGE_TYPE_ALIVE, lot_id, self.PADDING, self.PADDING)
        return packet

    def unpack_packet(self, packet):
        """
        unpacks a packet as defined by the par king protocol
        :param packet:
        :return: tuple (message_type, lot_id, capacity|padding, vacancies|padding)
        """
        packet = unpack(self.ENCODING, packet)
        return packet
