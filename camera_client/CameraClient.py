# from i2clibraries import i2c_hmc58831
from socket import socket
from socket import AF_INET
from socket import SOCK_STREAM
from socket import error as socket_error
from time import sleep
from time import time
from os import getpid
from os import remove
from struct import pack
from random import randint
import ParKingPacket
import config
from datetime import datetime
from threading import Thread
from i2clibraries import i2c_hmc5883l
import RPi.GPIO as GPIO            # import RPi.GPIO module
import subprocess

class CameraClient:
    THRESHOLD = 10
    TIME_FORMAT_STRING = '%Y-%m-%d %H:%M:%S'

#######################################################################################################################
#                           SETUP METHODS
#######################################################################################################################

    def __init__(self, service_port, host_ip, spots_available, data_log_mode=False):
        '''
        This will create a ParKingClient
        :param service_port:
        :param host
        :ip:
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

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        self.write_to_log('creating sensor 1')
        self.sensor_1 = i2c_hmc5883l.i2c_hmc5883l(1)
        self.sensor_1.setContinuousMode()
        self.sensor_1.setDeclination(0,6)
        self.write_to_log('sensor one created')

        sleep(2)

        (x, y, z) = self.read_from_sensor_1()
        self.z_base_line_1 = z
        self.last_z_signal_1 = 0


    def create_logs(self):
        """
        Creates a unique log file per session
        :return: log file
        """
        try:
            file_name = 'log_file'
            log_file = open(file_name, 'w')
            return log_file
        except Exception as e:
            print('Log file error, shutting down.')
            self.tear_down()

    def tear_down(self):
        """
        Called upon exit, this should tear down the existing resources that are not managed by daemons
        :return:
        """
        GPIO.cleanup()
        self.write_to_log('teardown started')
        if self.sock:
            close_packet = ParKingPacket.pack_close_packet(config.UNIQUE_ID)
            self.write_to_log('closing connection with server')
            self.sock.sendall(close_packet)
            self.write_to_log('closing listening socket')
            self.sock.close()
        if self.log_file:
            self.write_to_log('closing log file')
            self.log_file.close()

    def connect(self):
        try:
            self.write_to_log('opening socket')
            self.sock.connect((self.host_ip, self.service_port))
        except socket_error as e:
            print('Could not create socket, tearing down.')
            self.tear_down()
        self.write_to_log('socket opened!')

    def read_from_sensor_1(self):
        (x,y,z) = self.sensor_1.getAxes()
        if (z is None):
            z = -4095
        z = z + 4096
        return (x,y,z)

#######################################################################################################################
#                           RUN METHODS
#######################################################################################################################

    def run(self):
        self.write_to_log('Running')
        self.running = True
        self.write_to_log('Beginning sensor calibration')
        for i in range(100):
            # calibrate sensor
            (x,y,z_1) = self.read_from_sensor_1()
            self.z_base_line_1 = self.z_base_line_1*.95 + .05*z_1
            sleep(0.05)
        self.write_to_log('in_lane calibration complete.')
        while self.running:
            sleep(.5)
            (x,y,z_1) = self.read_from_sensor_1()
            z_val_1 = abs(z_1 - self.z_base_line_1)
            z_max_1 = z_val_1
            self.write_to_log('z : ' + str(z_val_1))

            while z_val_1 > self.THRESHOLD:
                sleep(0.5)
                (x,y,z_1) = self.read_from_sensor_1()
                z_val_1 = abs(z_1 - self.z_base_line_1)
                z_max_1 = max(z_val_1, z_max_1)
                self.write_to_log('z ++++ : ' + str(z_val_1))

                if z_val_1 < self.THRESHOLD:
                    self.write_to_log('car detected')
                    self.write_to_log('z_max : ' + str(z_max_1))
                    t = Thread(target=self.capture_and_send_image, args=())
                    t.daemon = True
                    t.start()

            self.z_base_line_1 = self.z_base_line_1*.95 + .05*z_1


    def keep_alive(self):
        while True:
            self.send_alive_packet()
            sleep(config.ALIVE_SLEEP)

    def capture_and_send_image(self):
        unique_file_name = str(randint)
        #self.log_file('Capturing image to file ' + unique_file_name)
        subprocess.Popen(['raspistill', '-o', unique_file_name, '-t', '500'])
        sleep(6)
        self.send_file(unique_file_name)
        self.log_file('removing image ' + unique_file_name)
        remove(unique_file_name)


#######################################################################################################################
#                           NETWORK METHODS
#######################################################################################################################

    def send_file(self, file_name):
        try:
            self.write_to_log('opening image socket')
            image_socket = socket(AF_INET, SOCK_STREAM)
            image_socket.connect((self.host_ip, self.service_port))
        except socket_error as e:
            print('Could not create image socket, tearing down.')
            self.tear_down()
        self.write_to_log('image socket opened!')
        uid = pack('!I', config.UNIQUE_ID)
        image_socket.sendall(uid)
        f = open(file_name,'r')
        #self.write_to_log('opened image : ' + file_name)
        l = f.read(1024)
        while (l):
            self.write_to_log('sending image : ' + file_name)
            image_socket.send(l)
            l = f.read(1024)
        self.write_to_log('sent image ' + file_name)
        f.close()
        image_socket.close()

    def send_init_packet(self, spots_available):
        self.write_to_log('sending init packet')
        packet = ParKingPacket.pack_init_packet(config.UNIQUE_ID, config.CAPACITY, spots_available)
        self.sock.sendall(packet)
        self.write_to_log('init packet send')

    def send_alive_packet(self):
        packet = ParKingPacket.pack_alive_packet(config.UNIQUE_ID)
        self.sock.sendall(packet)

#######################################################################################################################
#                           LOGGING METHODS
#######################################################################################################################

    def get_time_stamp(self):
        return datetime.fromtimestamp(time()).strftime(self.TIME_FORMAT_STRING)

    def write_to_log(self, message):
        message = self.get_time_stamp() + ' ' + message + '\n'
        if self.data_log_mode:
            self.log_file.write(message)
            self.log_file.flush()
