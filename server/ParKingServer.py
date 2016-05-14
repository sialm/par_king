import socket
import threading
from time import time
from datetime import datetime
from struct import error
import sys
from struct import unpack
import ParKingPacket
from ParkingLot import ParkingLot
import sqlite3

class ParKingServer:
    TIME_FORMAT_STRING = '%Y-%m-%d %H:%M:%S'

    ####################################################################################################################
    #                                               Set up / Tear down                                                 #
    ####################################################################################################################
    def __init__(self, service_port, data_log_mode = False):
        """
        Creates a new proxy service on the designated port.
        :param service_port:
        :param data_log_mode: if not defined will default to no log file
        :return: proxy service
        """
        self.data_log_mode = data_log_mode
        self.running = False
        self.parking_lots = []
        if self.data_log_mode:
            self.log_file = self.create_logs()
        else:
            self.log_file = None
        self.service_port = service_port
        self.connection = sqlite3.connect('Parking.db')
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # allow socket to be reused for quick recalls
        self.listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.this_host_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1][0]
        except IndexError:
            # no WAN available, only connected to localhost
            self.this_host_ip = '127.0.0.1'

    def start_listening(self):
        """
        This will create the listening socket that the proxy will accept incoming traffic on
        :return:
        """
        try:
            self.write_to_log('Creating listening socket on port ' + str(self.service_port))
            self.listening_socket.bind((self.this_host_ip, self.service_port))
            self.listening_socket.listen(8)
            print(self.get_timestamp_string() + ' - Server listening on ' + self.this_host_ip + ':' + str(self.service_port))
            print('socket creation successful.')
            self.running = True
            self.accept_requests()
        except Exception as e:
            self.write_to_log(e.message)
            self.tear_down()

    def create_logs(self):
        """
        Creates a unique log file per session
        :return: log file
        """
        try:
            file_name = 'log_file_' + self.get_timestamp_string()
            log_file = open(file_name, 'w')
            return log_file
        except Exception as e:
            self.tear_down()

    def tear_down(self):
        """
        Called upon exit, this should tear down the existing resources that are not managed by daemons
        :return:
        """
        self.write_to_log('teardown started')
        self.running = False
        if self.listening_socket:
            self.write_to_log('closing listening socket')
            self.listening_socket.close()
        if self.connection:
            self.write_to_log('closing database connection')
            self.connection.close()
        if self.log_file:
            self.write_to_log('closing log file')
            self.log_file.close()


    ####################################################################################################################
    #                                               Main Loop                                                          #
    ####################################################################################################################

    def accept_requests(self):
        """
        This is the main loop that will sit and listen on the port. In the event there is an error on this level the
        main loop will exit and do a tear down
        :return:
        """
        while True:
            try:
                client_socket, client_addr = self.listening_socket.accept()
                print('connection made to : ' + str(client_addr))
                t = threading.Thread(target=self.handle_client_traffic, args=(client_socket, client_addr,))
                t.daemon = True
                t.start()
            except Exception as e:
                self.write_to_log('Unexpected error encountered. Tearing down')
                self.write_to_log(e.message)
                self.tear_down()
                return

    ####################################################################################################################
    #                                               Helper Methods                                                     #
    ####################################################################################################################


    def write_to_log(self, message):
        """
        Writes a message to the log file with a time stamp.
        :param message:
        :return:
        """
        if not self.data_log_mode:
            return

        try:
            log_string = '[%s] : %s \n' % (self.get_timestamp_string(), message)
            self.log_file.write(log_string)
            self.log_file.flush()
        except ValueError as e:
            sys.stderr(e.message)

    def get_timestamp_string(self):
        """
        :return: timestamp for line output as defined in Project 1 protocol
        """
        return datetime.fromtimestamp(time()).strftime(self.TIME_FORMAT_STRING)

    ####################################################################################################################
    #                                               Methods that do stuff                                              #
    ####################################################################################################################

    def handle_client_traffic(self, client_socket, client_addr):
        """
        This method will handle incoming traffic from a given client.
        :param client_socket:
        :param client_addr:
        :return:
        """
        data = client_socket.recv(4096)
        packet = ParKingPacket.unpack_packet(data)

        if packet[0] is not ParKingPacket.MESSAGE_TYPE_INIT:
            self.write_to_log('Something is borken!!! Expeceted INIT got : ' . str(packet))
            client_socket.close()
            return

        parking_lot = ParkingLot(packet[1], packet[2], packet[3])

        while self.running:

            client_socket.settimeout(300)
            # set the timeout on the socket so that if there is no activity for 5 mintues we assume that the lot has lost
            # connectivity and cannot be reached
            try:
                data = client_socket.recv(4096)
                print(str(data))
            except socket.timeout :
                client_socket.close()
                parking_lot.tear_down()
                self.write_to_log('client died!!! WHAT THE WHAT?!')
                return

            self.write_to_log('accepted something from client')

            try:
                (message_type, lot_id, capacity, vacancies) = ParKingPacket.unpack_packet(data)
            except error as e:
                print('struct.error : ' + e.message)
                print('unpacking packet : ' + data)
            print("**********************************************")
            if message_type is ParKingPacket.MESSAGE_TYPE_ALIVE:
                print('ITS ALIVE!!!')
                continue
            elif message_type is ParKingPacket.MESSAGE_TYPE_IN:
                t = threading.Thread(target=parking_lot.goes_in, args=())
                t.daemon = True
                t.start()
                print('GOES INS')
            elif message_type is ParKingPacket.MESSAGE_TYPE_OUT:
                t = threading.Thread(target=parking_lot.goes_out, args=())
                t.daemon = True
                t.start()
                print("GOES OUTS")
            else:
                print("Unrecognized message type : " . str(message_type))