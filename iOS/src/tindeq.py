import cb
import time
import struct
import numpy as np


class TindeqProgressor(object):
    response_codes = {
        'cmd_resp': 0, 'weight_measure': 1, 'low_pwr': 4
    }
    cmds = dict(
        TARE_SCALE=0x64,
        START_WEIGHT_MEAS=0x65,
        STOP_WEIGHT_MEAS=0x66,
        START_PEAK_RFD_MEAS=0x67,
        START_PEAK_RFD_MEAS_SERIES=0x68,
        ADD_CALIB_POINT=0x69,
        SAVE_CALIB=0x6a,
        GET_APP_VERSION=0x6b,
        GET_ERR_INFO=0x6c,
        CLR_ERR_INFO=0x6d,
        SLEEP=0x6e,
        GET_BATT_VLTG=0x6f
    )

    service_uuid = '7e4e1701-1ea6-40c9-9dcc-13d34ffead57'
    write_uuid = '7e4e1703-1ea6-40c9-9dcc-13d34ffead57'
    notify_uuid = '7e4e1702-1ea6-40c9-9dcc-13d34ffead57'

    def __init__(self, parent):
        """
        Uses Bluetooth 4 (LE) to communicate with Tindeq Progressor

        Send bytes to write UUID to control the device. Current weight or
        rate of force is reported on the notify UUID, so use callbacks to do
        something when you receive info on this UUID.

        Parameters
        ----------
        parent: object
            An owning class that implements callbacks specifying
            what to do when receiving weight notifications
        """
        self.peripheral = None
        self.write_characteristic = None
        self.read_characteristic = None
        self.info_struct = struct.Struct('<bb')
        self.data_struct = struct.Struct('<fl')
        self.ready = False
        self._tare_value = 0.0
        self.parent = parent

    def log(self, msg):
        # ask for forgiveness, not permission
        try:
            # first attempt to log to msgbox in parent if there
            self.parent.msgbox.text = msg
        except:
            # if this fails, print to screen
            print(msg)

    def did_discover_peripheral(self, p):
        '''called whenever a new peripheral is found'''
        if (p.name and 'progressor' in p.name.lower() and self.peripheral is None):
            self.peripheral = p
            self.log('connecting to progressor')
            cb.connect_peripheral(p)

    def did_connect_peripheral(self, p):
        self.log('connected; discovering services')
        p.discover_services()

    def did_fail_to_connect_peripheral(self, p, err):
        self.log('failed to connect: %s' % (err,))

    def did_disconnect_peripheral(self, p, err):
        self.log('disconnected: %s' % (err,))
        self.peripheral = None

    def did_discover_services(self, p, err):
        for s in p.services:
            # 2 services, the tindeq one and the firmware update
            if s.uuid.lower() == self.service_uuid:
                self.log('found service')
                p.discover_characteristics(s)

    def did_discover_characteristics(self, s, err):
        for c in s.characteristics:
            if c.uuid.lower() == self.notify_uuid:
                self.log('found notify')
                self.read_characteristic = c
            elif c.uuid.lower() == self.write_uuid:
                self.log('found write')
                self.write_characteristic = c
        # notify parent that we can start
        self.ready = True

    def did_update_value(self, c, err):
        '''called whenever a notify service sends a msg'''
        self.last_val = c.value
        kind, size = self.info_struct.unpack(c.value[:2])
        if kind == self.response_codes['weight_measure']:
            # data sent in bulk packets
            for weight, useconds in self.data_struct.iter_unpack(c.value[2:]):
                now = useconds/1.0e6
                if hasattr(self.parent, 'log_force_sample'):
                    self.parent.log_force_sample(now, weight - self._tare_value)
        elif kind == self.response_codes['cmd_resp']:
            self.cmd_response(c.value)

    def cmd_response(self, value):
        try:
            if self.last_cmd == 'get_app':
                self.log(f"FW version : {value[2:].decode('utf-8')}")
            elif self.last_cmd == 'get_batt':
                vdd, = struct.unpack("<I", value[2:])
                self.log(f"Battery level = {vdd} [mV]")
            elif self.last_cmd == 'get_err':
                try:
                    print("Crashlog : {0}".format(value[2:].decode("utf-8")))
                except UnicodeDecodeError:
                    pass
            self.last_cmd = None

        except Exception as err:
            self.log(err)

    def pack(self, cmd):
        return cmd.to_bytes(2, byteorder='little')

    def _send_cmd(self, cmd_key):
        if self.peripheral is None:
            return

        cmd = self.pack(self.cmds[cmd_key])
        try:
            self.peripheral.write_characteristic_value(
                self.write_characteristic, cmd, False)
        except Exception as err:
            self.log(f'failed to send cmd {cmd_key}: {str(err)}')

    def get_fw_info(self):
        self.last_cmd = 'get_app'
        self._send_cmd('GET_APP_VERSION')

    def get_batt(self):
        self.last_cmd = 'get_batt'
        self._send_cmd('GET_BATT_VLTG')

    def get_err(self):
        self.last_cmd = 'get_err'
        self._send_cmd('GET_ERR_INFO')

    def clear_err(self):
        self.last_cmd = None
        self._send_cmd('CLR_ERR_INFO')

    def tare(self):
        self.last_cmd = None
        self._send_cmd('TARE_SCALE')

    def enable_notifications(self):
        # enable notifications
        try:
            self.peripheral.set_notify_value(
                self.read_characteristic, True
            )
         except Exception as err:
            self.log('failed to start notifications' + str(err))

    def disable_notifications(self):
        # enable notifications
        try:
            self.peripheral.set_notify_value(
                self.read_characteristic, False
            )
         except Exception as err:
            self.log('failed to start notifications' + str(err))

    def start_logging_weight(self):
        self.last_cmd = None
        self._send_cmd('START_WEIGHT_MEAS')

    def end_logging_weight(self):
        self.last_cmd = None
        self._send_cmd('STOP_WEIGHT_MEAS')

    def sleep(self):
        self.last_cmd = None
        self._send_cmd('SLEEP')
        self.peripheral = None

    def soft_tare(self):
        _saved_parent = self.parent
        self.parent = SampleAverage()
        self.start_logging_weight()
        time.sleep(1)
        self.stop_logging_weight()
        self._tare_value = self.parent.mean
        self.parent = _saved_parent

class SampleAverage:
    def __init__(self):
        self.weights = []

    def log_force_sample(self, time, weight):
        self.weights.append(weight)

    @property
    def mean(self):
        return np.mean(self.weights)



if __name__ == '__main__':

    import matplotlib.pyplot as plt

    class Wrapper:
        def __init__(self):
            self.wsamples = []
            self.times = []

        def log_force_sample(self, now, sample):
            print(f"{now}: {sample} kg")
            self.wsamples.append(sample)
            self.times.append(now)

    wrap = Wrapper()
    delegate = TindeqProgressor(wrap)
    print('scanning for peripherals')
    cb.set_central_delegate(delegate)
    cb.scan_for_peripherals()

    while not delegate.ready:
        time.sleep(3)
    delegate.enable_notifications()
    delegate.get_fw_info()
    time.sleep(0.5)
    delegate.get_batt()
    time.sleep(1)
    delegate.soft_tare()
    time.sleep(1)

    print('go')
    startT = time.time()
    delegate.start_logging_weight()
    try:
        while time.time() - startT < 5:
            pass
    except KeyboardInterrupt:
        cb.reset()
    finally:
        delegate.end_logging_weight()
        cb.reset()
        delegate.sleep()
    time.sleep(0.5)

    print(f'mean = {np.mean(wrap.wsamples)}')
    mean = np.mean(wrap.wsamples)
    prec = 100*np.std(wrap.wsamples)/mean
    print(f'accuracy = {prec}%')
    plt.plot(wrap.times, wrap.wsamples)
    plt.show()
