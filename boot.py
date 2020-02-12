from network import WLAN, STA_IF
from network import mDNS
import time
import usocket as socket
import ustruct as struct
from ubinascii import hexlify
import time
from machine import Pin, ADC, deepsleep, PWM, Timer
from board import LED
import machine
import random


wlan = WLAN(STA_IF)
wlan.active(True)

wlan.connect('Home', '1234windsor', 5000)

while not wlan.isconnected():
    print("Waiting for wlan connection")
    time.sleep(1)

print("WiFi connected at", wlan.ifconfig()[0])

# Advertise as 'hostname', alternative to IP address
try:
    hostname = 'megacontroller' # Would this be our personal ip address
    mdns = mDNS(wlan)
    mdns.start(hostname, "MicroPython REPL")
    mdns.addService('_repl', '_tcp', 23, hostname)
    print("Advertised locally as {}.local".format(hostname))
except OSError:
    print("Failed starting mDNS server - already started?")

# start telnet server for remote login
from network import telnet

print("start telnet server")

# Change

telnet.start(user='micro', password='python')

# fetch NTP time
from machine import RTC

print("inquire RTC time")
rtc = RTC()
rtc.ntp_sync(server="pool.ntp.org")

timeout = 10
for _ in range(timeout):
    if rtc.synced():
        break
    print("Waiting for rtc time")
    time.sleep(1)

if rtc.synced():
    print(time.strftime("%c", time.localtime()))
else:
    print("could not get NTP time")




d = Pin(LED, mode = Pin.OUT)
analog_pin = ADC(Pin(33)) # corresponds to pin A9 ADC pin
analog_pin.atten(ADC.ATTN_11DB)

changed = 0 # Initialize time between consecutive claps
count = 0

finished = False

while not finished:

    t_end_sample = time.time() + 0.2
    peak_to_peak = 0
    signal_max = 0
    signal_min = 4095

    while time.time() < t_end_sample:

        recording = analog_pin.read()
        if recording < 4095:
            if recording > signal_max:
                signal_max = recording
            elif recording < signal_min:
                signal_min = recording

        now = time.monotonic()

    peak_to_peak = signal_max - signal_min
    volts = (peak_to_peak * 3.3) / 4095


    if volts >= 1:

        # Turn LED off

        if count == 0:
            changed = time.time() + 5
            count += 1
            print('First clap')

        elif time.time() < changed: #This is if there is another consecutive clap within 3 seconds
            count += 1
            print('consecutive')
        else:
            count = 0

    if count == 3:
        finished = True # Exit loop
        print('finished')







random.seed(2)

SigPin1 = Pin(25, mode=Pin.OUT)  # Corresponds to A1. Pin A0 is broken now.
SigPin2 = Pin(4, mode=Pin.OUT)  # Pin A5
SigPin3 = Pin(5, mode=Pin.OUT)  # Pin A16
SigPin4 = Pin(18, mode=Pin.OUT)  # Pin A17
SigPin5 = Pin(19, mode=Pin.OUT)  # Pin A18
SigPin6 = Pin(16, mode=Pin.OUT)  # Pin A19
SigPin7 = Pin(17, mode=Pin.OUT)  # Pin A20
SigPin8 = Pin(21, mode=Pin.OUT)  # Pin A21

PWM1 = machine.PWM(SigPin1)  # This is representative of the bottom motor
PWM2 = machine.PWM(SigPin2)  # This is representative of the middle motor
PWM3 = machine.PWM(SigPin3)  # This is representative of the hips
PWM4 = machine.PWM(SigPin4)  # This is representative of the head
PWM5 = machine.PWM(SigPin5)  # This is representative of the left arm
PWM6 = machine.PWM(SigPin6)  # This is representative of the right arm
PWM7 = machine.PWM(SigPin7)  # This is representative of the left elbow
PWM8 = machine.PWM(SigPin8)  # This is representative of the right elbow

PWM1.freq(50)
PWM2.freq(50)
PWM3.freq(50)
PWM4.freq(50)
PWM5.freq(50)
PWM6.freq(50)
PWM7.freq(50)
PWM8.freq(50)

PWM1.duty(7.5)
PWM2.duty(7.5)
PWM3.duty(7.5)
PWM4.duty(7.5)
PWM5.duty(7.5)
PWM6.duty(7.5)
PWM7.duty(7.5)
PWM8.duty(7.5)


class MQTTException(Exception):
    pass

class MQTTClient:

    def __init__(self, client_id, server, port=0, user=None, password=None, keepalive=0,
                 ssl=False, ssl_params={}):
        if port == 0:
            port = 8883 if ssl else 1883
        self.client_id = client_id
        self.sock = None
        self.server = server
        self.port = port
        self.ssl = ssl
        self.ssl_params = ssl_params
        self.pid = 0
        self.cb = None
        self.user = user
        self.pswd = password
        self.keepalive = keepalive
        self.lw_topic = None
        self.lw_msg = None
        self.lw_qos = 0
        self.lw_retain = False
        self.msg = b''


    def _send_str(self, s):
        self.sock.write(struct.pack("!H", len(s)))
        self.sock.write(s)

    def _recv_len(self):
        n = 0
        sh = 0
        while 1:
            b = self.sock.read(1)[0]
            n |= (b & 0x7f) << sh
            if not b & 0x80:
                return n
            sh += 7

    def set_callback(self, f):
        self.cb = f

    def set_last_will(self, topic, msg, retain=False, qos=0):
        assert 0 <= qos <= 2
        assert topic
        self.lw_topic = topic
        self.lw_msg = msg
        self.lw_qos = qos
        self.lw_retain = retain

    def connect(self, clean_session=True):
        self.sock = socket.socket()
        addr = socket.getaddrinfo(self.server, self.port)[0][-1]
        self.sock.connect(addr)
        if self.ssl:
            import ussl
            self.sock = ussl.wrap_socket(self.sock, **self.ssl_params)
        premsg = bytearray(b"\x10\0\0\0\0\0")
        msg = bytearray(b"\x04MQTT\x04\x02\0\0")

        sz = 10 + 2 + len(self.client_id)
        msg[6] = clean_session << 1
        if self.user is not None:
            sz += 2 + len(self.user) + 2 + len(self.pswd)
            msg[6] |= 0xC0
        if self.keepalive:
            assert self.keepalive < 65536
            msg[7] |= self.keepalive >> 8
            msg[8] |= self.keepalive & 0x00FF
        if self.lw_topic:
            sz += 2 + len(self.lw_topic) + 2 + len(self.lw_msg)
            msg[6] |= 0x4 | (self.lw_qos & 0x1) << 3 | (self.lw_qos & 0x2) << 3
            msg[6] |= self.lw_retain << 5

        i = 1
        while sz > 0x7f:
            premsg[i] = (sz & 0x7f) | 0x80
            sz >>= 7
            i += 1
        premsg[i] = sz

        self.sock.write(premsg, i + 2)
        self.sock.write(msg)
        #print(hex(len(msg)), hexlify(msg, ":"))
        self._send_str(self.client_id)
        if self.lw_topic:
            self._send_str(self.lw_topic)
            self._send_str(self.lw_msg)
        if self.user is not None:
            self._send_str(self.user)
            self._send_str(self.pswd)
        resp = self.sock.read(4)
        assert resp[0] == 0x20 and resp[1] == 0x02
        if resp[3] != 0:
            raise MQTTException(resp[3])
        return resp[2] & 1

    def disconnect(self):
        self.sock.write(b"\xe0\0")
        self.sock.close()

    def ping(self):
        self.sock.write(b"\xc0\0")

    def publish(self, topic, msg, retain=False, qos=0):
        pkt = bytearray(b"\x30\0\0\0")
        pkt[0] |= qos << 1 | retain
        sz = 2 + len(topic) + len(msg)
        if qos > 0:
            sz += 2
        assert sz < 2097152
        i = 1
        while sz > 0x7f:
            pkt[i] = (sz & 0x7f) | 0x80
            sz >>= 7
            i += 1
        pkt[i] = sz
        #print(hex(len(pkt)), hexlify(pkt, ":"))
        self.sock.write(pkt, i + 1)
        self._send_str(topic)
        if qos > 0:
            self.pid += 1
            pid = self.pid
            struct.pack_into("!H", pkt, 0, pid)
            self.sock.write(pkt, 2)
        self.sock.write(msg)
        if qos == 1:
            while 1:
                op = self.wait_msg()
                if op == 0x40:
                    sz = self.sock.read(1)
                    assert sz == b"\x02"
                    rcv_pid = self.sock.read(2)
                    rcv_pid = rcv_pid[0] << 8 | rcv_pid[1]
                    if pid == rcv_pid:
                        return
        elif qos == 2:
            assert 0

    def subscribe(self, topic, qos=0):
        #assert self.cb is not None, "Subscribe callback is not set"
        pkt = bytearray(b"\x82\0\0\0")
        self.pid += 1
        struct.pack_into("!BH", pkt, 1, 2 + 2 + len(topic) + 1, self.pid)
        #print(hex(len(pkt)), hexlify(pkt, ":"))
        self.sock.write(pkt)
        self._send_str(topic)
        self.sock.write(qos.to_bytes(1, "little"))
        while 1:
            op = self.wait_msg()
            if op == 0x90:
                resp = self.sock.read(4)
                #print(resp)
                assert resp[1] == pkt[2] and resp[2] == pkt[3]
                if resp[3] == 0x80:
                    raise MQTTException(resp[3])
                return

    # Wait for a single incoming MQTT message and process it.
    # Subscribed messages are delivered to a callback previously
    # set by .set_callback() method. Other (internal) MQTT
    # messages processed internally.
    def wait_msg(self):
        res = self.sock.read(1)
        self.sock.setblocking(True)
        if res is None:
            return None
        if res == b"":
            raise OSError(-1)
        if res == b"\xd0":  # PINGRESP
            sz = self.sock.read(1)[0]
            assert sz == 0
            return None
        op = res[0]
        #if op & 0xf0 != 0x30:
        #    return op
        sz = self._recv_len()
        topic_len = self.sock.read(2)
        topic_len = (topic_len[0] << 8) | topic_len[1]
        topic = self.sock.read(topic_len)
        sz -= topic_len + 2
        if op & 6:
            pid = self.sock.read(2)
            pid = pid[0] << 8 | pid[1]
            sz -= 2
        msg = self.sock.read(sz)
        self.cb(topic, msg)
        if op & 6 == 2:
            pkt = bytearray(b"\x40\x02\0\0")
            struct.pack_into("!H", pkt, 2, pid)
            self.sock.write(pkt)
        elif op & 6 == 4:
            assert 0





    # Checks whether a pending message from server is available.
    # If not, returns immediately with None. Otherwise, does
    # the same processing as wait_msg.
    def check_msg(self):
        self.sock.setblocking(False)
        return self.wait_msg()



# Rad

def freestyle(t):

    time.sleep(6.5)
    t_end = time.time() + t

    while time.time() < t_end:

        PWM1.duty(random.uniform(4, 11))
        PWM2.duty(random.uniform(4, 11))
        PWM3.duty(random.uniform(4, 11))
        PWM4.duty(random.uniform(4, 11))
        PWM5.duty(random.uniform(4, 11))
        PWM6.duty(random.uniform(4, 11))
        PWM7.duty(random.uniform(4, 11))
        PWM8.duty(random.uniform(4, 11))
        time.sleep(1.091)

    # End routine
    # Home position
    PWM1.duty(7.5)
    PWM2.duty(7.5)
    PWM3.duty(7.5)
    PWM4.duty(7.5)
    PWM5.duty(7.5)
    PWM6.duty(7.5)
    PWM7.duty(7.5)
    PWM8.duty(7.5)
    time.sleep(1)
    # Motors off
    PWM1.duty(0)
    PWM2.duty(0)
    PWM3.duty(0)
    PWM4.duty(0)
    PWM5.duty(0)
    PWM6.duty(0)
    PWM7.duty(0)
    PWM8.duty(0)


# Moves butt in a variety of different ways


def shake_it():

    time.sleep(2)

    PWM1.duty(7.5)
    PWM2.duty(7.5)
    # time.sleep(2)
    # PWM2.duty(3)

    PWM3.duty(7.5)
    PWM4.duty(7.5)
    PWM5.duty(7.5)
    PWM6.duty(7.5)
    PWM7.duty(7.5)
    PWM8.duty(7.5)
    time.sleep(1)

    t_end = time.time() + 3
    while time.time() < t_end:
        PWM5.duty(10)
        PWM6.duty(5)
        time.sleep(0.5)
        PWM5.duty(5)
        PWM6.duty(10)
        time.sleep(0.5)


    t_end = time.time() + 5
    while time.time() < t_end:
        PWM2.duty(3)
        PWM5.duty(10)
        PWM6.duty(5)
        time.sleep(0.5)
        PWM2.duty(5)
        PWM5.duty(5)
        PWM6.duty(10)
        time.sleep(0.5)

    PWM1.duty(7.5)
    PWM2.duty(7.5)
    PWM3.duty(7.5)
    PWM4.duty(7.5)
    PWM5.duty(7.5)
    PWM6.duty(7.5)
    PWM7.duty(7.5)
    PWM8.duty(7.5)
    time.sleep(1)

    PWM2.duty(3)



    t_end = time.time() + 5
    while time.time() < t_end:
        # This sets elbows to opposite movements
        PWM8.duty(12)
        PWM7.duty(12)
        PWM4.duty(12)
        PWM1.duty(7)
        time.sleep(0.5)
        PWM8.duty(3)
        PWM7.duty(3)
        PWM4.duty(3)
        PWM1.duty(8.7)
        time.sleep(0.5)

    PWM1.duty(7.5)
    PWM2.duty(7.5)
    PWM3.duty(7.5)
    PWM4.duty(7.5)
    PWM5.duty(7.5)
    PWM6.duty(7.5)
    PWM7.duty(7.5)
    PWM8.duty(7.5)
    time.sleep(1)
    # Motors off
    PWM1.duty(0)
    PWM2.duty(0)
    PWM3.duty(0)
    PWM4.duty(0)
    PWM5.duty(0)
    PWM6.duty(0)
    PWM7.duty(0)
    PWM8.duty(0)


def say_hi():
    # Home position
    PWM1.duty(7.5)
    PWM2.duty(7.5)
    PWM3.duty(7.5)
    PWM4.duty(7.5)
    PWM5.duty(7.5)
    PWM6.duty(7.5)
    PWM7.duty(7.5)
    PWM8.duty(7.5)

    # Begin routine
    # Arms down
    PWM5.duty(5)
    PWM6.duty(11)
    time.sleep(1)
    # Turn left
    PWM3.duty(9)
    PWM4.duty(9)
    time.sleep(.5)
    # Wave right arm twice
    PWM6.duty(4)
    time.sleep(0.5)
    PWM6.duty(6)
    time.sleep(0.5)
    PWM6.duty(4)
    time.sleep(0.5)
    PWM6.duty(6)
    time.sleep(0.5)
    PWM6.duty(5)
    time.sleep(0.5)
    # Right arm down
    PWM6.duty(11)
    time.sleep(0.5)
    # Turn right
    PWM3.duty(6)
    PWM4.duty(6)
    time.sleep(.5)
    # Wave left arm twice
    PWM5.duty(11)
    time.sleep(0.5)
    PWM5.duty(9)
    time.sleep(0.5)
    PWM5.duty(11)
    time.sleep(0.5)
    PWM5.duty(9)
    time.sleep(0.5)
    PWM5.duty(11)
    time.sleep(0.5)
    # Left arm down
    PWM5.duty(5)
    time.sleep(0.5)
    # Return to center
    PWM3.duty(7.5)
    PWM4.duty(7.5)
    time.sleep(3)

    # End routine
    # Home position
    PWM1.duty(7.5)
    PWM2.duty(7.5)
    PWM3.duty(7.5)
    PWM4.duty(7.5)
    PWM5.duty(7.5)
    PWM6.duty(7.5)
    PWM7.duty(7.5)
    PWM8.duty(7.5)
    time.sleep(1)
    # Motors off
    PWM1.duty(0)
    PWM2.duty(0)
    PWM3.duty(0)
    PWM4.duty(0)
    PWM5.duty(0)
    PWM6.duty(0)
    PWM7.duty(0)
    PWM8.duty(0)


def bow():

    PWM1.duty(7.5)
    PWM2.duty(7.5)
    PWM3.duty(7.5)
    PWM4.duty(7.5)
    PWM5.duty(7.5)
    PWM6.duty(7.5)
    PWM7.duty(7.5)
    PWM8.duty(7.5)

    # Begin routine
    # Arms down
    PWM5.duty(5)
    PWM6.duty(11)
    time.sleep(1)
    # Bow once
    PWM2.duty(4)
    time.sleep(1.5)
    PWM2.duty(7.5)
    time.sleep(1)
    # Bow twice
    PWM2.duty(4)
    time.sleep(1.5)
    PWM2.duty(7.5)
    time.sleep(1)

    # End routine
    # Home position
    PWM1.duty(7.5)
    PWM2.duty(7.5)
    PWM3.duty(7.5)
    PWM4.duty(7.5)
    PWM5.duty(7.5)
    PWM6.duty(7.5)
    PWM7.duty(7.5)
    PWM8.duty(7.5)
    time.sleep(1)
    # Motors off
    PWM1.duty(0)
    PWM2.duty(0)
    PWM3.duty(0)
    PWM4.duty(0)
    PWM5.duty(0)
    PWM6.duty(0)
    PWM7.duty(0)
    PWM8.duty(0)


def sub_cb(topic, msg):
    x = msg.decode('UTF-8')
    if "shake" in x:

        shake_it()
        print('shake worked')

    elif "Freestyle" in x:

        freestyle(int(x[10:]))
        print("worked")
        print(int(x[10:]))

    elif "wave" in x:

        say_hi()
        print('wave worked')

    elif "bow" in x:

        bow()
        print('bow worked')



myMqttClient = "ANYTHING"
adafruitIoUrl = "io.adafruit.com"
adafruitUsername = "dehmoubedr7811"
adafruitAioKey = "80106bfc54ec4539b9b6b5397278181c"
c = MQTTClient(myMqttClient, adafruitIoUrl, 0, adafruitUsername, adafruitAioKey)


# Wake up send that IOT signal is received


c.set_callback(sub_cb)
c.connect()

c.subscribe("dehmoubedr7811/feeds/testfeed")


while True:
    c.check_msg()
    time.sleep(1)

