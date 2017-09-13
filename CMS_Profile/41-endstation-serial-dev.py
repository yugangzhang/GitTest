import time
#import select
import re
from ophyd import Device


#class SerialDevice():
    
#    def __init__(self, prefix='', *args, read_attrs=None, configuration_attrs=None,
#                 name='SerialDevice', parent=None, **kwargs):

        #super().__init__(prefix=prefix, *args, read_attrs=read_attrs, configuration_attrs=configuration_attrs, name=name, parent=parent, **kwargs)

        
            

            
class Agilent_34970A(Device):
    # Note: Command terminator is a newline character \n.
    # Note: On serial cable, data transmit/receive pins (pins 2 and 3 on Dsub-9 connector) must be reversed.
    # Settings as of 07/25/2017: Baud rate = 19200 bits/s, Stop bits = 1, Parity = None, Flow control = None 
    # Moxa port 9: socket = 10.11.130.53:4009
    
    def __init__(self, prefix='', *args, read_attrs=None, configuration_attrs=None,
                 name='Agilent_34970A', parent=None, **kwargs):

        super().__init__(prefix=prefix, *args, read_attrs=read_attrs, configuration_attrs=configuration_attrs, name=name, parent=parent, **kwargs)

        #self.port_number = 9
        #self.server_port = 4000 + self.port_number
        self.connect_socket()
        self.HP34901_channel = 100	# 20 channel multiplexer module card in slot 1        
        self.HP34907_channel = 300	# DIO/DAC card in slot 3

    # Essential socket interaction
    ########################################
        
    def connect_socket(self):
        
        #self.server_address= '10.11.130.51'
        self.server_address= '10.11.130.53'     # Moxa inside Endstation hutch
        #self.server_IP = '10.11.129.2'
        self.port_number = 9
        self.server_port = 4000 + self.port_number
        
        import socket
        #self.sock = socket.socket()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(self.server_address)
        self.sock.connect((self.server_address, self.server_port))
        
        self.sock.settimeout(0.5)
        
        
    def disconnect_socket(self):
        
        self.sock.close()
    
        
    def send_socket(self, msg):
        
        #self.sock.send(chr(13).encode('ascii', 'ignore')) # Carriage return
        self.sock.send(msg.encode('ascii', 'ignore'))
        #self.sock.send(msg.encode('utf-8'))


    def send_get_reply(self, msg, verbosity=3):
        
        #self.send_socket('\r')
        self.send_socket(msg)
        
        time.sleep(0.5)
        
        return self.read_socket(verbosity=verbosity)
    
        
    def read_socket(self, timeout_s=3, verbosity=3):
        
        start_time = time.time()
        terminator = chr(0x18)
    
        # Look for the response
        amount_received = 0
        amount_cutoff = 5000
        
        txt = ''
        msg_received = ''
        
        while terminator not in txt and time.time()-start_time<timeout_s and amount_received<amount_cutoff:
            try:
                data = self.sock.recv(1)
            except:
                break
                                    
            amount_received += len(data)
            txt = data.decode('ascii')
            
            msg_received += txt
            
        msg_received = msg_received.replace(terminator, '')
        
        if time.time()-start_time>timeout_s:
            if verbosity>=1:
                print('Read timeout after {:.1f} s.'.format(time.time()-start_time))
            return ''
        
        else:
            if verbosity>=2:
                print(msg_received)
            return msg_received
        

    # Commands for Agilent 34970A unit
    ########################################

    # Reset Agilent 34970A unit to factory default settings.
    def reset_Agilent34970A(self, verbosity = 3):
        self.send_socket('*RST\n')


    # Commands for HP34901 20-channel muliplexer module card
    ########################################

    # Reset HP34901 to factory default settings.
    def reset_HP34901(self, verbosity = 3):
        self.send_socket('SYSTEM:CPON {chan}\n'.format(chan=self.HP34901_channel))


    # Read DC voltage on specified channel.
    def readDCV(self, channel, verbosity = 1):
        if (channel < 1 or channel > 20):
            print('Invalid multiplexer channel number; must be 1-20.\n')
            return 0

        read_channel = int(self.HP34901_channel + channel)
        self.send_socket('INPUT:IMP:AUTO ON, (@{chan})\n'.format(chan=read_channel))    
        self.send_socket('SENSE:ZERO:AUTO ON, (@{chan})\n'.format(chan=read_channel))    
        self.send_socket('MEAS:VOLT:DC? AUTO,MAX, (@{chan})\n'.format(chan=read_channel))    
        dcv = float(self.read_socket(verbosity=1))

        if (verbosity > 1):
            print('Channel {chan} is {volts} VDC.\n'.format(chan=channel, volts=dcv))

        return dcv

    
    # Commands for HP34907 DIO/DAC card
    ########################################

    # Output specified voltage on specified DAC channel
    def setDAC(self, channel, voltage, verbosity = 1):

        if (channel < 1 or channel > 2):
            print('Invalid DAC channel number; must be 1 or 2.\n')
            return 0

        if (voltage < -12.0 or voltage > 12.0):
            print('Invalid DAC voltage value; must be within +/-12 volts.\n')
            return 0

        dac_channel = int(self.HP34907_channel + channel + 3)
        self.send_socket('SOURCE:VOLTAGE {volts}, (@{chan})\n'.format(volts=voltage, chan=dac_channel))    
        #self.send_socket('SOURCE:VOLTAGE {volts}, (@{chan})\r'.format(volts=voltage, chan=dac_channel))    

        if (verbosity > 1):
            print('DAC output channel {chan} set to {volts} VDC.\n'.format(chan=channel, volts=voltage))

        return 1


    # Query voltage setting on specified DAC channel
    def readDAC(self, channel, verbosity = 1):

        if (channel < 1 or channel > 2):
            print('Invalid DAC channel number; must be 1 or 2.\n')
            return 0

        dac_channel = int(self.HP34907_channel + channel + 3)
        self.send_socket('SOURCE:VOLTAGE? (@{chan})\n'.format(chan=dac_channel))    
        voltage = float(self.read_socket(verbosity=1))

        if (verbosity > 1):
            print('DAC output channel {chan} set to {volts} VDC.\n'.format(chan=channel, volts=voltage))

        return voltage

 
    # Write digital byte to specified DIO channel
    def writeByteDIO(self, channel, value, verbosity = 1):

        if (channel < 1 or channel > 2):
            print('Invalid DIO channel number; must be 1 or 2.\n')
            return 0

        dio_channel = int(self.HP34907_channel + channel)
        diovalue = ((value ^ 0xf) & 0xf)
        #self.send_socket('SOURCE:DIGITAL:DATA:BYTE {byte}, (@{chan})\n'.format(byte=diovalue, chan=dio_channel))    
        self.send_socket('SOURCE:DIGITAL:DATA:BYTE {byte}, (@{chan})\n'.format(byte=value, chan=dio_channel))    

        if (verbosity > 1):
            print('DIO output channel {chan} set to {val}.\n'.format(chan=channel, val=value))

        return 1


    # Read digital byte on specified DIO channel
    def readByteDIO(self, channel, verbosity = 1):

        if (channel < 1 or channel > 2):
            print('Invalid DIO channel number; must be 1 or 2.\n')
            return 0

        dio_channel = int(self.HP34907_channel + channel)
        self.send_socket('SOURCE:DIGITAL:DATA:BYTE? (@{chan})\n'.format(chan=dio_channel))    
        value = int(self.read_socket(verbosity=1))
        diovalue = ((value ^ 0xf) & 0xf)

        if (verbosity > 1):
            print('DIO output channel {chan} set to {val}.\n'.format(chan=channel, val=value))

        return value

    

class Keithley_2000(Device):
    # Note: Command terminator is a carriage-return character \r.
    # Settings as of 07/25/2017: Baud rate = 19200 bits/s, Stop bits = 1, Parity = None, Flow control = None
    # Moxa port 10: socket = 10.11.130.53:4010
    
    def __init__(self, prefix='', *args, read_attrs=None, configuration_attrs=None,
                 name='Keithley_2000', parent=None, **kwargs):

        super().__init__(prefix=prefix, *args, read_attrs=read_attrs, configuration_attrs=configuration_attrs, name=name, parent=parent, **kwargs)

        #self.port_number = 10
        #self.server_port = 4000 + self.port_number
        self.connect_socket()

    # Essential socket interaction
    ########################################
        
    def connect_socket(self):
        
        #self.server_address= '10.11.130.51'
        self.server_address= '10.11.130.53'     # Moxa inside Endstation hutch
        #self.server_IP = '10.11.129.2'
        self.port_number = 10
        self.server_port = 4000 + self.port_number
        
        import socket
        #self.sock = socket.socket()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(self.server_address)
        self.sock.connect((self.server_address, self.server_port))
        
        self.sock.settimeout(0.5)
        
        
    def disconnect_socket(self):
        
        self.sock.close()
    
        
    def send_socket(self, msg):
        
        #self.sock.send(chr(13).encode('ascii', 'ignore')) # Carriage return
        self.sock.send(msg.encode('ascii', 'ignore'))
        #self.sock.send(msg.encode('utf-8'))


    def send_get_reply(self, msg, verbosity=3):
        
        #self.send_socket('\r')
        self.send_socket(msg)
        
        time.sleep(0.5)
        
        return self.read_socket(verbosity=verbosity)
    
        
    def read_socket(self, timeout_s=3, verbosity=3):
        
        start_time = time.time()
        terminator = chr(0x18)
    
        # Look for the response
        amount_received = 0
        amount_cutoff = 5000
        
        txt = ''
        msg_received = ''
        
        while terminator not in txt and time.time()-start_time<timeout_s and amount_received<amount_cutoff:
            try:
                data = self.sock.recv(1)
            except:
                break
                                    
            amount_received += len(data)
            txt = data.decode('ascii')
            
            msg_received += txt
            
        msg_received = msg_received.replace(terminator, '')
        
        if time.time()-start_time>timeout_s:
            if verbosity>=1:
                print('Read timeout after {:.1f} s.'.format(time.time()-start_time))
            return ''
        
        else:
            if verbosity>=2:
                print(msg_received)
            return msg_received


    # Select the channel for reading 
    def selectChannel(self, channel, verbosity = 1):
         
        if (channel < 1 or channel > 10):
            print('Invalid channel number; must be between 1 and 10.\n')
            return 0

        self.send_socket(':ROUT:CLOS (@{chan})\r'.format(chan=channel))    

        if (verbosity > 1):
            print('Keithley 2000 channel set to {chan}.\n'.format(chan=channel))

        return 1


    # Read resistance on the selected channel
    def readOhm(self, channel, verbosity = 1):

        self.selectChannel(channel, verbosity=1)
        time.sleep(0.1)
        self.send_socket(':SENS:FUNC \'RES\'\r')    
        time.sleep(0.1)
        self.send_socket(':SENS:DATA?\r')    
        time.sleep(0.1)
        ohm = float(self.read_socket(verbosity=1))

        if (verbosity > 1):
            print('The resistance on channel {chan} is {res} Ohm.\n'.format(chan=channel, res=ohm))

        return ohm


    # Read DC voltage on the selected channel
    def readDCV(self, channel, verbosity = 1):

        self.selectChannel(channel, verbosity=1)
        time.sleep(0.1)
        self.send_socket(':SENS:FUNC \'VOLT:DC\'\r')    
        time.sleep(0.1)
        self.send_socket(':SENS:DATA?\r')    
        time.sleep(0.1)
        dcv = float(self.read_socket(verbosity=1))

        if (verbosity > 1):
            print('The DC voltage on channel {chan} is {volts} VDC.\n'.format(chan=channel, volts=dcv))

        return dcv


    # Read 30 kOhm thermistor on the selected channel and return T[degC] 
    def readThermister30kohm(self, channel, verbosity = 1):

        ohm = self.readOhm(channel, verbosity=1)

        coeff_a = 0.000932681
        coeff_b = 0.000221455
        coeff_c = 0.000000126

        Temp = coeff_a;
        Temp += coeff_b * numpy.log(ohm)
        Temp += coeff_c * (numpy.log(ohm))**3
        Temp = 1.0/Temp - 273.15

        if (verbosity > 1):
            print('The temperature (30k-ohm thermistor) on channel {chan} is {degC} degC.\n'.format(chan=channel, degC=Temp))

        return Temp


    # Read 100 kOhm thermistor on the selected channel and return T[degC] 
    def readThermister100kohm(self, channel, verbosity = 1):

        ohm = self.readOhm(channel, verbosity=1)

        coeff_a = 0.000827094
        coeff_b = 0.000204256
        coeff_c = 1.15042e-07

        Temp = coeff_a;
        Temp += coeff_b * numpy.log(ohm)
        Temp += coeff_c * (numpy.log(ohm))**3
        Temp = 1.0/Temp - 273.15

        if (verbosity > 1):
            print('The temperature (100k-ohm thermistor) on channel {chan} is {degC} degC.\n'.format(chan=channel, degC=Temp))

        return Temp


    # Read Pt100 RTD on the selected channel and return T[degC] 
    def readPt100(self, channel, verbosity = 1):

        ohm = self.readOhm(channel, verbosity=1)

        # Conversion formula from: 
        # http://www.mosaic-industries.com/embedded-systems/microcontroller-projects/temperature-measurement/platinum-rtd-sensors/resistance-calibration-table
        c0 = -245.19
        c1 = 2.5293
        c2 = -0.066046 
        c3 = 4.0422e-3
        c4 = -2.0697e-6 
        c5 = -0.025422 
        c6 = 1.6883e-3 
        c7 = -1.3601e-6 

        Temp = ohm * (c1 + ohm * (c2 + ohm * (c3 + c4 * ohm)))
        Temp /= 1.0 + ohm * (c5 * ohm * (c6 + c7 * ohm))
        Temp += c0

        if (verbosity > 1):
            print('The temperature (Pt100 RTD) on channel {chan} is {degC} degC.\n'.format(chan=channel, degC=Temp))

        return Temp



class TTL_control(object):
    '''
    Uses the 2 8-bit DIO channels on Agilent34970A
    Note: agilent = Agilent_34970A(), unit = Agilent DIO channel number, port 1 = bit 1, etc.
    Note: If there is an error reading or setting, try to read/write to Agilent DIO channels directly first, and it should start working.
    '''

    def __init__(self, name='TTL_control', description="", pv=None, **args):
        
        self.name=name
        self.description=description
        
        
    def readPort(self, unit, port, verbosity=2):

        if (unit < 1 or unit > 2):
            print('Invalid TTL unit number; must be 1 or 2.\n')
            return 0

        if (port < 1 or port > 8):
            print('Invalid TTL port number; must be between 1 and 8.\n')
            return 0

        value = agilent.readByteDIO(unit, verbosity=1)
        bit_pos = int(port)
        onoff = int(bin(value)[2:].zfill(8)[-bit_pos])

        if (verbosity > 1):
            print('TTL unit {uu} port {pp} is currently set to {oo}.\n'.format(uu=unit, pp=bit_pos, oo=onoff))

        return onoff


    def readPorts(self, unit, verbosity=2):

        if (unit < 1 or unit > 2):
            print('Invalid TTL unit number; must be 1 or 2.\n')
            return 0

        value = agilent.readByteDIO(unit, verbosity=1)
        bits = [] 
        for i in range(1,8+1):
            #b = self.readPort(unit, i, verbosity=verbosity)
            b = int(bin(value)[2:].zfill(8)[-i]) 
            bits.append(b)            

        if (verbosity > 1):
            print('TTL unit {uu} ports 1-8 are currently set to {ll}.\n'.format(uu=unit, ll=bits))

        return value


    def setPort(self, unit, port, onoff, verbosity=2):

        if (unit < 1 or unit > 2):
            print('Invalid TTL unit number; must be 1 or 2.\n')
            return 0

        if (port < 1 or port > 8):
            print('Invalid TTL port number; must be between 1 and 8.\n')
            return 0
        
        # check the current setting and don't do anything if already set as requested
        b = self.readPort(unit, port, verbosity=1)
        if (onoff == b):
            if (verbosity > 1):
                print('TTL unit {uu} port {pp} is already set to {oo}.\n'.format(uu=unit, pp=port, oo=onoff))
            return 0
           
        value = agilent.readByteDIO(unit, verbosity=1)
        bit_pos = int(port)
        if (onoff == 1):
            value += 2**(bit_pos-1)
        elif (onoff == 0):
            value -= 2**(bit_pos-1)
        else:
            pass
        
        agilent.writeByteDIO(unit, value, verbosity=1)
        b_new = self.readPort(unit, port, verbosity=1)
        if (b_new != onoff):
            print('ERROR: TTL unit {uu} port {pp} is still set to {oo}.\n'.format(uu=unit, pp=port, oo=b_new))
            return 0
        else:
            if (verbosity > 1):
                print('TTL unit {uu} port {pp} has been set to {oo}.\n'.format(uu=unit, pp=port, oo=b_new))
            return 1
    

    def setPortOn(self, unit, port, verbosity=2):
        
        return self.setPort(unit, port, 1, verbosity=verbosity)


    def setPortOff(self, unit, port, verbosity=2):
        
        return self.setPort(unit, port, 0, verbosity=verbosity)




#agilent = Agilent_34970A()
#keithley = Keithley_2000()
#ttl = TTL_control()
    

