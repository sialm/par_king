import sqlite3
import ParKingPacket
from datetime import datetime

class ParkingLot:
    def __init__(self, lot_id, capacity, vacancy):
        '''

        :param lot_id: must be set below
        :param capacity: number of spots in garage
        :param vacancy: number of vacant spots
        :return:
        '''
        self.lot_id = lot_id
        self.capacity = capacity
        self.vacancy = vacancy
        self.address = get_lot_address_by_lot_id(lot_id)
        self.conn = sqlite3.connect('Parking.db')

    def tear_down(self):
        if self.conn:
            self.conn.close()

    def goes_in(self):
        self.vacancy = self.vacancy - 1
        self.conn.cursor().execute(self.get_data_base_string_for_direction(ParKingPacket.MESSAGE_TYPE_IN))
        self.conn.commit()

    def goes_out(self):
        self.vacancy = self.vacancy + 1
        self.conn.cursor().execute(self.get_data_base_string_for_direction(ParKingPacket.MESSAGE_TYPE_OUT))
        self.conn.commit()

    def get_vacancy(self):
        return self.vacancy

    def get_data_base_string_for_direction(self, direction):
        now = datetime.now()
        return 'INSERT INTO traffic VALUES (\'' + str(self.lot_id) + '\' , \'' + str(direction) + '\', \'' + str(now) + '\')'


def get_lot_address_by_lot_id(lot_id):
    if lot_id is  1:
        return "123 main St, Seattle WA 98101"
    else:
        return "Address Not found"