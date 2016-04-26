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
from json import encoder
import config
from i2clibraries import i2c_hmc5883l

class ParKingClient:
    START_CONNECTION = 1
    ALIVE = 2
    INCOMING = 3
    OUTGOING = 4
    SHUTTING_DOWN = 5

    THRESHOLD = 4
    TIME_FORMAT_STRING = '%Y-%m-%d %H:%M:%S'

    def __init__(self, service_port, host_ip, data_log_mode=False):
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
        self.sensor = i2c_hmc5883l.i2c_hmc5883l(1)
        self.sensor.setContinuousMode()
        self.sensor.setDeclination(0,6)
        sleep(2)
        (x, y, z) = self.read_from_sensor()
        self.z_base_line = z
        self.last_z_signal = 0

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

    def read_from_sensor(self):
        vals = self.sensor.getAxes()
        return vals

    def run(self):
        self.running = True

        for i in range(100):
            (x,y,z) = self.read_from_sensor()
            self.z_base_line = self.z_base_line*.95 + .05*z
            sleep(0.05)

        while self.running:
            sleep(0.05)
            (x,y,z) = self.read_from_sensor()
            z_val = z - self.z_base_line
            z_max = z_val
            while z_val > self.THRESHOLD:
                sleep(0.05)
                (x,y,z) = self.read_from_sensor()
                z_val = z - self.z_base_line
                z_max = max(z_val, z_max)

                if z_val < self.THRESHOLD:
                    t = Thread(target=self.pack_and_send, args=(z_max, ))
                    t.daemon = True
                    t.start()

            self.z_base_line = self.z_base_line*.95 + .05*z

    def pack_and_send(self, value):
        right_meow = self.get_time_stamp()
        payload = right_meow + ' VALUE : ' + str(value)
        print('payload : ' + payload)
        encoding = '!' + str(len(payload)) + 's'
        payload = payload.encode('utf-8')
        packet = pack(encoding, payload)
        self.sock.sendall(packet)

    def get_time_stamp(self):
        return datetime.fromtimestamp(time()).strftime(self.TIME_FORMAT_STRING)

    def write_to_log(self, string):
        if self.data_log_mode:
            self.log_file.write(string)
            self.log_file.flush()
