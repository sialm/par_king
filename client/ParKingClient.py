# from i2clibraries import i2c_hmc58831
from socket import socket
from socket import AF_INET
from socket import SOCK_STREAM
from socket import error as socket_error
from time import sleep
from time import time
from struct import pack
from datetime import datetime
from threading import Thread
import config
from ParKingPacket import ParKingPacket
from i2clibraries import i2c_hmc5883l

class ParKingClient:
    START_CONNECTION = 1
    ALIVE = 2
    INCOMING = 3
    OUTGOING = 4
    SHUTTING_DOWN = 5

    THRESHOLD = 4
    TIME_FORMAT_STRING = '%Y-%m-%d %H:%M:%S'

#######################################################################################################################
#                           SETUP METHODS
#######################################################################################################################

    def __init__(self, service_port, host_ip, spots_available, data_log_mode=False):
        '''
        This will create a ParKingClient
        :param service_port:
        :param host_ip:
        :param data_log_mode:
        :return:
        '''
        self.data_log_mode = data_log_mode
        if self.data_log_mode:
            self.log_file = self.create_logs()
        else:
            self.log_file = None
        self.host_ip = host_ip
        self.service_port = service_port
        self.running = False

        self.sock = socket(AF_INET, SOCK_STREAM)
        self.connect()
        self.send_init_packet(spots_available)

        alive_thread = Thread(target=self.keep_alive, args=())
        alive_thread.daemon = True
        alive_thread.start()

        self.sensor_1 = i2c_hmc5883l.i2c_hmc5883l(1)
        self.sensor_1.setContinuousMode()
        self.sensor_1.setDeclination(0,6)
        self.sensor_2 = i2c_hmc5883l.i2c_hmc5883l(2)
        self.sensor_2.setContinuousMode()
        self.sensor_2.setDeclination(0,6)
        sleep(2)

        (x, y, z) = self.read_from_sensor_1()
        self.z_base_line_1 = z
        self.last_z_signal_1 = 0
        (x, y, z) = self.read_from_sensor_2()
        self.z_base_line_2 = z
        self.last_z_signal_2 = 0

    def create_logs(self):
        """
        Creates a unique log file per session
        :return: log file
        """
        try:
            file_name = 'log_file_' + self.get_time_stamp()
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
        if self.sock:
            self.write_to_log('closing listening socket')
            self.sock.close()
        if self.log_file:
            self.write_to_log('closing log file')
            self.log_file.close()


    def connect(self):
        try:
            self.sock.connect((self.host_ip, self.service_port))
        except socket_error as e:
            if self.sock:
                self.sock.close()
            print("what the what? all things are broken: " + e.message)
            self.tear_down()

    def read_from_sensor_1(self):
        vals = self.sensor_1.getAxes()
        return vals

    def read_from_sensor_2(self):
        vals = self.sensor_2.getAxes()
        return vals

#######################################################################################################################
#                           RUN METHODS
#######################################################################################################################

    def run(self):
        self.running = True

        if (config.SENSOR_CONFIG is config.ONE_LANE):
            self.run_one_lane()
        elif (config.SENSOR_CONFIG is config.TWO_LANE):
            goes_in_thread = Thread(target=self.run_in_lane, args=())
            goes_in_thread.daemon = True
            goes_in_thread.start()
            goes_out_thread = Thread(target=self.run_out_lane, args=())
            goes_out_thread.daemon = True
            goes_out_thread.start()

    def run_in_lane(self):
        for i in range(100):
            # calibrate sensor
            (x,y,z_1) = self.read_from_sensor_1()
            self.z_base_line_1 = self.z_base_line_1*.95 + .05*z_1
            sleep(0.05)

        while self.running:
            sleep(0.05)
            (x,y,z_1) = self.read_from_sensor_1()
            z_val_1 = z_1 - self.z_base_line_1
            z_max_1 = z_val_1

            while z_val_1 > self.THRESHOLD:
                sleep(0.05)
                (x,y,z_1) = self.read_from_sensor_1()
                z_val_1 = z_1 - self.z_base_line_1
                z_max_1 = max(z_val_1, z_max_1)

                if z_val_1 < self.THRESHOLD:
                    t = Thread(target=self.send_goes_in_packet, args=(z_max_1, ))
                    t.daemon = True
                    t.start()

            self.z_base_line_1 = self.z_base_line_1*.95 + .05*z_1

    def run_out_lane(self):
        for i in range(100):
        # calibrate sensor
            (x,y,z_2) = self.read_from_sensor_2()
            self.z_base_line_2 = self.z_base_line_1*.95 + .05*z_2
            sleep(0.05)

        while self.running:
            sleep(0.05)
            (x,y,z_2) = self.read_from_sensor_2()
            z_val_2 = z_2 - self.z_base_line_2
            z_max_2 = z_val_2

            while z_val_2 > self.THRESHOLD:
                sleep(0.05)
                (x,y,z_2) = self.read_from_sensor_2()
                z_val_2 = z_2 - self.z_base_line_2
                z_max_2 = max(z_val_2, z_max_2)

                if z_val_2 < self.THRESHOLD:
                    t = Thread(target=self.send_goes_out_packet, args=(z_max_2, ))
                    t.daemon = True
                    t.start()

            self.z_base_line_2 = self.z_base_line_2*.95 + .05*z_2

    def run_one_lane(self):
        (x,y,z_1) = self.read_from_sensor_1()
        (x,y,z_2) = self.read_from_sensor_2()
        self.z_base_line_1 = self.z_base_line_1*.95 + .05*z_1
        self.z_base_line_2 = self.z_base_line_2*.95 + .05*z_2
        sleep(0.05)
        while self.running:
            sleep(0.05)
            (x,y,z_1) = self.read_from_sensor_1()
            (x,y,z_2) = self.read_from_sensor_2()
            z_val_1 = z_1 - self.z_base_line_1
            z_val_2 = z_2 - self.z_base_line_2
            z_max_1 = z_val_1
            z_max_2 = z_val_2

            if z_val_1 > self.THRESHOLD:
                self.goes_in_helper(z_val_1)
            elif z_val_2 > self.THRESHOLD:
                self.goes_out_helper(z_val_2)
                
    def goes_in_helper(self, z_val_1):
        # TODO mik fix me
        print 'Mik fix me'

    def goes_out_helper(self, z_val_2):
        # TODO mik fix me
        print 'Mik fix me'

    def keep_alive(self):
        while True:
            self.send_alive_packet()
            sleep(config.ALIVE_SLEEP)

#######################################################################################################################
#                           NETWORK METHODS
#######################################################################################################################

    def send_init_packet(self, spots_available):
        packet = ParKingPacket.pack_init_packet(config.UNIQUE_ID, config.CAPACITY, spots_available)
        self.sock.sendall(packet)

    def send_goes_out_packet(self, z_value):
        packet = ParKingPacket.pack_out_packet(config.UNIQUE_ID, z_value)
        self.sock.sendall(packet)

    def send_goes_in_packet(self, z_value):
        packet = ParKingPacket.pack_in_packet(config.UNIQUE_ID, z_value)
        self.sock.sendall(packet)

    def send_alive_packet(self):
        packet = ParKingPacket.pack_alive_packet(config.UNIQUE_ID)
        self.sock.sendall(packet)

#######################################################################################################################
#                           LOGGING METHODS
#######################################################################################################################

    def get_time_stamp(self):
        return datetime.fromtimestamp(time()).strftime(self.TIME_FORMAT_STRING)

    def write_to_log(self, string):
        if self.data_log_mode:
            self.log_file.write(string)
            self.log_file.flush()
