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
import ParKingPacket
from i2clibraries import i2c_hmc5883l
import RPi.GPIO as GPIO            # import RPi.GPIO module


# 16 is the GPIO pin


class ParKingClient:
    MUX_PIN = 23

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

        GPIO.setmode(GPIO.BCM)             # choose BCM or BOARD
        GPIO.setup(self.MUX_PIN, GPIO.OUT)           # set GPIO24 as an output
        GPIO.output(self.MUX_PIN, 0)

        self.write_to_log('creating sensor 1')
        self.sensor_1 = i2c_hmc5883l.i2c_hmc5883l(1)
        self.sensor_1.setContinuousMode()
        self.sensor_1.setDeclination(0,6)
        self.write_to_log('sensor one created')

        GPIO.output(self.MUX_PIN, 1)
        self.write_to_log('creating sensor 2')
        self.sensor_2 = i2c_hmc5883l.i2c_hmc5883l(0)
        self.sensor_2.setContinuousMode()
        self.sensor_2.setDeclination(0,6)
        self.write_to_log('sensor two created')

        sleep(2)

        (x, y, z) = self.read_from_sensor_1()
        self.z_base_line_1 = z
        self.last_z_signal_1 = 0

        if not config.ONE_SENSOR:
            (x, y, z) = self.read_from_sensor_2()
            self.z_base_line_2 = z
            self.last_z_signal_2 = 0

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
        vals = self.sensor_1.getAxes()
        if (vals[2] is None):
            vals[2] = -4095
        self.write_to_log('sensor 1 : ' + str(vals))
        return vals

    def read_from_sensor_2(self):
        vals = self.sensor_2.getAxes()
        if (vals[2] is None):
            vals[2] = -4095
        self.write_to_log('sensor 1 : ' + str(vals))
        return vals

#######################################################################################################################
#                           RUN METHODS
#######################################################################################################################

    def run(self):
        self.write_to_log('Running')
        self.running = True
        if config.ONE_SENSOR:
            self.run_in_lane()
        elif (config.SENSOR_CONFIG is config.ONE_LANE):
            self.run_one_lane()
        elif (config.SENSOR_CONFIG is config.TWO_LANE):
            goes_in_thread = Thread(target=self.run_in_lane, args=())
            goes_in_thread.daemon = True
            goes_in_thread.start()
            goes_out_thread = Thread(target=self.run_out_lane, args=())
            goes_out_thread.daemon = True
            goes_out_thread.start()

    def run_in_lane(self):
        self.write_to_log('run_in_lane.')
        for i in range(100):
            # calibrate sensor
            (x,y,z_1) = self.read_from_sensor_1()
            self.z_base_line_1 = self.z_base_line_1*.95 + .05*z_1
            sleep(0.05)
        self.write_to_log('in_lane calibration complete.')
        while self.running:
            self.write_to_log('in lane : nothing doing')
            sleep(0.05)
            (x,y,z_1) = self.read_from_sensor_1()
            z_val_1 = z_1 - self.z_base_line_1
            z_max_1 = z_val_1

            self.write_to_log('z_max_1:' + str(z_max_1))
            while z_val_1 > self.THRESHOLD:
                self.write_to_log('in lane : threshold passed')

                sleep(0.05)
                (x,y,z_1) = self.read_from_sensor_1()
                z_val_1 = z_1 - self.z_base_line_1
                z_max_1 = max(z_val_1, z_max_1)

                if z_val_1 < self.THRESHOLD:
                    self.write_to_log('in lane : sending goes outs packet')

                    t = Thread(target=self.send_goes_in_packet, args=(z_max_1, ))
                    t.daemon = True
                    t.start()

            self.z_base_line_1 = self.z_base_line_1*.95 + .05*z_1

    def run_out_lane(self):
        self.write_to_log('run_out_lane.')
        for i in range(100):
        # calibrate sensor
            (x,y,z_2) = self.read_from_sensor_2()
            self.z_base_line_2 = self.z_base_line_1*.95 + .05*z_2
            sleep(0.05)
        self.write_to_log('out_lane calibration complete.')
        while self.running:
            self.write_to_log('out lane: nothing doing')

            sleep(0.05)
            (x,y,z_2) = self.read_from_sensor_2()
            z_val_2 = z_2 - self.z_base_line_2
            z_max_2 = z_val_2

            while z_val_2 > self.THRESHOLD:
                self.write_to_log('out lane: threshold passed')

                sleep(0.05)
                (x,y,z_2) = self.read_from_sensor_2()
                z_val_2 = z_2 - self.z_base_line_2
                z_max_2 = max(z_val_2, z_max_2)

                if z_val_2 < self.THRESHOLD:
                    self.write_to_log('out lane: sending goes outs packet')
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
            print('z_1 : ' + str(type(z_1)))
            print('val : ' + str(z_1))
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
        self.send_goes_in_packet(z_val_1)

    def goes_out_helper(self, z_val_2):
        # TODO mik fix me
        self.send_goes_out_packet(z_val_2)

    def keep_alive(self):
        while True:
            self.send_alive_packet()
            sleep(config.ALIVE_SLEEP)

#######################################################################################################################
#                           NETWORK METHODS
#######################################################################################################################

    def send_init_packet(self, spots_available):
        self.write_to_log('sending init packet')
        packet = ParKingPacket.pack_init_packet(config.UNIQUE_ID, config.CAPACITY, spots_available)
        self.sock.sendall(packet)
        self.write_to_log('init packet send')

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

    def write_to_log(self, message):
        message = self.get_time_stamp() + ' ' + message + '\n'
        if self.data_log_mode:
            self.log_file.write(message)
            self.log_file.flush()
