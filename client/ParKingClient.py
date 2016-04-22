# from i2clibraries import i2c_hmc58831
import socket
from time import sleep
from time import time
from struct import pack
from datetime import datetime
import threading

class ParKingClient:
    THRESHOLD = 250
    TIME_FORMAT_STRING = '%Y-%m-%d %H:%M:%S'


    def __init__(self, service_port, host_ip, data_log_mode=False):
        # self.hmc58831 = i2c_hmc58831.i2c_hmc58831(1)
        # self.hmc58831.setContinousMode()
        # self.hmc58831.setDeclination(0,6)

        self.host_ip = host_ip
        self.service_port = service_port
        self.running = False
        self.data_log_mode = data_log_mode
        if self.data_log_mode:
            self.log_file = self.create_logs()
        else:
            self.log_file = None

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect()
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
        except socket.error as (e, message):
            if self.sock:
                self.sock.close()
            print "what the what? all things are broken: " + message
            self.tear_down()

    def read_from_sensor(self):
        return (1,2,3)

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
                    t = threading.Thread(target=self.pack_and_send(), args=z_max)
                    t.daemon = True
                    t.start()

            self.z_base_line = self.z_base_line*.95 + .05*z

    def pack_and_send(self, value):
        neow = self.get_time_stamp()
        payload = neow + ' VALUE : ' + str(value)
        encoding = 's' + str(len(payload))
        packet = pack(encoding, payload)

        self.sock.sendall(packet)

    def get_time_stamp(self):
        return datetime.fromtimestamp(time()).strftime(self.TIME_FORMAT_STRING)

    def write_to_log(self, string):
        if self.data_log_mode:
            self.log_file.write(string)
            self.log_file.flush()
