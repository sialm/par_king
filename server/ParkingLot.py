import sqlite3

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

    def goes_in(self):
        self.vacancy = self.vacancy - 1

    def goes_out(self):
        self.vacancy = self.vacancy + 1

    def get_vacancy(self):
        return self.vacancy



def get_lot_address_by_lot_id(lot_id):
    if lot_id is  1:
        return "123 main St, Seattle WA 98101"
    else:
        return "Address Not found"