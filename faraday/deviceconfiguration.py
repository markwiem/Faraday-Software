#!/usr/bin/env python

import time
import logging.config
import os
import sys
import json
import ConfigParser
import base64
import argparse
import shutil
import requests

from flask import Flask
from flask import request

from faraday.proxyio import faradaybasicproxyio
from faraday.proxyio import faradaycommands
from faraday.proxyio import deviceconfig

# Start logging after importing modules
relpath1 = os.path.join('etc', 'faraday')
relpath2 = os.path.join('..', 'etc', 'faraday')
setuppath = os.path.join(sys.prefix, 'etc', 'faraday')
userpath = os.path.join(os.path.expanduser('~'), '.faraday')
path = ''

for location in os.curdir, relpath1, relpath2, setuppath, userpath:
    try:
        logging.config.fileConfig(os.path.join(location, "loggingConfig.ini"))
        path = location
        break
    except ConfigParser.NoSectionError:
        pass

logger = logging.getLogger('DeviceConfiguration')

# Create Device Configuration configuration file path
deviceConfigurationConfigPath = os.path.join(path, "deviceconfiguration.ini")
faradayConfigPath = os.path.join(path, "faraday_config.ini")
logger.debug('deviceconfiguration.ini PATH: ' + deviceConfigurationConfigPath)
logger.debug('faraday_config.ini PATH: ' + faradayConfigPath)

# Load Device Configuration Configuration from deviceconfiguration.ini file
deviceConfig = ConfigParser.RawConfigParser()

# Command line input
parser = argparse.ArgumentParser(description='Device Configuration application provides a Flask server to program Faraday radios via an API')
parser.add_argument('--init-config', dest='init', action='store_true', help='Initialize Device Configuration configuration file')
parser.add_argument('--init-faraday-config', dest='initfaraday', action='store_true', help='Initialize Faraday configuration file')
parser.add_argument('--start', action='store_true', help='Start device configuration server')
parser.add_argument('--proxycallsign', help='Set Proxy Faraday callsign to connect to and program')
parser.add_argument('--proxynodeid', type=int, help='Set Proxy Faraday nodeid to connect to and program')
parser.add_argument('--faradayconfig', action='store_true', help='Display Faraday configuration file contents')

# Faraday Configuration
parser.add_argument('--callsign', help='Set Faraday radio callsign')
parser.add_argument('--nodeid', type=int, help='Set Faraday radio nodeid')
parser.add_argument('--configboot', action='store_false', help='Set Faraday radio config boot bit OFF')
parser.add_argument('--gpiop3', type=int, help='Set Faraday radio fgpio_p3')
parser.add_argument('--gpiop4', type=int, help='Set Faraday radio fgpio_p4')
parser.add_argument('--gpiop5', type=int, help='Set Faraday radio fgpio_p5')
parser.add_argument('--bootfrequency', type=float, help='Set Faraday radio boot frequency')
parser.add_argument('--bootrfpower', type=int, help='Set Faraday radio boot RF power')
parser.add_argument('--latitude', type=float, help='Set Faraday radio default latitude. Format \"ddmm.mmmm\"')
parser.add_argument('--longitude', type=float, help='Set Faraday radio default longitude. Format \"dddmm.mmmm\"')
parser.add_argument('--latitudedir', help='Set Faraday radio default latitude direction (N/S)')
parser.add_argument('--longitudedir', help='Set Faraday radio default longitude direction (E/W)')
parser.add_argument('--altitude', type=float, help='Set Faraday radio default altitude in meters. Maximum of 17999.99 Meters')
# Purposely do not allow editing of GPS altitude units
parser.add_argument('--gpsbooton', action='store_true', help='Set Faraday radio GPS boot power ON')
parser.add_argument('--gpsbootoff', action='store_true', help='Set Faraday radio GPS boot power OFF')
parser.add_argument('--gpsenabled', action='store_true', help='Set Faraday radio GPS use ON')
parser.add_argument('--gpsdisabled', action='store_true', help='Set Faraday radio GPS use OFF')
parser.add_argument('--uarttelemetryenabled', action='store_true', help='Set Faraday radio UART Telemetry ON')
parser.add_argument('--uarttelemetrydisabled', action='store_true', help='Set Faraday radio UART Telemetry OFF')
parser.add_argument('--rftelemetryenabled', action='store_true', help='Set Faraday radio RF Telemetry ON')
parser.add_argument('--rftelemetrydisabled', action='store_true', help='Set Faraday radio RF Telemetry OFF')
parser.add_argument('--uartinterval', type=int, help='Set Faraday radio UART telemetry interval in seconds')
parser.add_argument('--rfinterval', type=int, help='Set Faraday radio RF telemetry interval in seconds')

# Parse the arguments
args = parser.parse_args()


def initializeDeviceConfigurationConfig():
    '''
    Initialize device configuration configuration file from deviceconfiguration.sample.ini

    :return: None, exits program
    '''

    logger.info("Initializing Device Configuration")
    shutil.copy(os.path.join(path, "deviceconfiguration.sample.ini"), os.path.join(path, "deviceconfiguration.ini"))
    logger.info("Initialization complete")
    sys.exit(0)


def initializeFaradayConfig():
    '''
    Initialize Faraday radio configuration file from faraday_config.sample.ini

    :return: None, exits program
    '''

    logger.info("Initializing Faraday Configuration")
    shutil.copy(os.path.join(path, "faraday_config.sample.ini"), os.path.join(path, "faraday_config.ini"))
    logger.info("Initialization complete")
    sys.exit(0)


def programFaraday(deviceConfigurationConfigPath):
    '''

    :param deviceConfigurationConfigPath: Path to deviceconfiguration.ini file
    :return: None
    '''

    config = ConfigParser.RawConfigParser()
    config.read(os.path.join(path, "deviceconfiguration.ini"))

    # Variables
    local_device_callsign = config.get("DEVICES", "CALLSIGN")
    local_device_node_id = config.get("DEVICES", "NODEID")
    local_device_callsign = str(local_device_callsign).upper()

    hostname = config.get("PROXY", "HOST")
    port = config.get("PROXY", "PORT")
    cmdPort = config.get("PROXY", "CMDPORT")

    # Send POST data to Proxy to configure unit
    try:
        r = requests.post('http://{0}:{1}'.format(hostname, port),
                          params={'callsign': str(local_device_callsign), 'nodeid': int(local_device_node_id), 'port': cmdPort})
        logger.info(r.url)
        logger.info("Sent Programming Request")

    except requests.exceptions.RequestException as e:
        # Some error occurred
        logger.error(e)
        logger.error(r.text)


def displayConfig(faradayConfigPath):
    with open(faradayConfigPath, 'r') as configFile:
        print configFile.read()
        sys.exit(0)


def configureDeviceConfiguration(args, deviceConfigurationConfigPath, faradayConfigPath):
    '''
    Configure device configuration configuration file from command line

    :param args: argparse arguments
    :param deviceConfigurationConfigPath: Path to deviceconfiguration.ini file
    :return: None
    '''

    config = ConfigParser.RawConfigParser()
    config.read(deviceConfigurationConfigPath)

    fconfig = ConfigParser.RawConfigParser()
    fconfig.read(faradayConfigPath)

    if args.proxycallsign is not None:
        config.set('DEVICES', 'CALLSIGN', args.proxycallsign)
    if args.proxynodeid is not None:
        config.set('DEVICES', 'NODEID', args.proxynodeid)

    # Faraday radio configuration
    if args.callsign is not None:
        fconfig.set('BASIC', 'CALLSIGN', args.callsign)
    if args.nodeid is not None:
        fconfig.set('BASIC', 'ID', args.nodeid)
    if args.configboot:
        fconfig.set('BASIC', 'configbootbitmask', 1)
    else:
        fconfig.set('BASIC', 'configbootbitmask', 0)
    if args.gpiop3 is not None:
        fconfig.set('BASIC', 'gpio_P3', args.gpiop3)
    if args.gpiop4 is not None:
        fconfig.set('BASIC', 'gpio_p4', args.gpiop4)
    if args.gpiop5 is not None:
        fconfig.set('BASIC', 'gpio_p5', args.gpiop5)
    if args.bootfrequency is not None:
        fconfig.set('RF', 'boot_frequency_mhz', args.bootfrequency)
    if args.bootrfpower is not None:
        fconfig.set('RF', 'boot_rf_power', args.bootrfpower)
    if args.latitude is not None:
        fconfig.set('GPS', 'default_latitude', args.latitude)
    if args.longitude is not None:
        fconfig.set('GPS', 'default_longitude', args.longitude)
    if args.latitudedir is not None:
        fconfig.set('GPS', 'default_latitude_direction', args.latitudedir)
    if args.longitudedir is not None:
        fconfig.set('GPS', 'default_longitude_direction', args.longitudedir)
    if args.altitude is not None:
        fconfig.set('GPS', 'default_altitude', args.altitude)
    if args.gpsbooton:
        fconfig.set('GPS', 'gps_boot_bit', 1)
    if args.gpsbootoff:
        fconfig.set('GPS', 'gps_boot_bit', 0)
    if args.gpsenabled:
        fconfig.set('GPS', 'gps_present_bit', 1)
    if args.gpsdisabled:
        fconfig.set('GPS', 'gps_present_bit', 0)
    if args.uarttelemetryenabled:
        fconfig.set('TELEMETRY', 'uart_telemetry_boot_bit', 1)
    if args.uarttelemetrydisabled:
        fconfig.set('TELEMETRY', 'uart_telemetry_boot_bit', 0)
    if args.rftelemetryenabled:
        fconfig.set('TELEMETRY', 'rf_telemetry_boot_bit', 1)
    if args.rftelemetrydisabled:
        fconfig.set('TELEMETRY', 'rf_telemetry_boot_bit', 0)
    if args.uartinterval is not None:
        fconfig.set('TELEMETRY', 'telemetry_default_uart_interval', args.uartinterval)
    if args.rfinterval is not None:
        fconfig.set('TELEMETRY', 'telemetry_default_rf_interval', args.rfinterval)

    # Save device configuration
    with open(deviceConfigurationConfigPath, 'wb') as configfile:
        config.write(configfile)

    # Save Faraday configuration
    with open(faradayConfigPath, 'wb') as configfile:
        fconfig.write(configfile)


# Now act upon the command line arguments
# Initialize and configure Device Configuration
if args.init:
    initializeDeviceConfigurationConfig()
if args.initfaraday:
    initializeFaradayConfig()
if args.faradayconfig:
    displayConfig(faradayConfigPath)

# Check if configuration file is present
if not os.path.isfile(deviceConfigurationConfigPath):
    logger.error("Please initialize device configuration with \'--init-config\' option")
    sys.exit(0)

# Check if configuration file is present
faradayConfigPath = os.path.join(path, "faraday_config.ini")
if not os.path.isfile(faradayConfigPath):
    logger.error("Please initialize Faraday configuration with \'--init-faraday-config\' option")
    sys.exit(0)

# Configure configuration file
configureDeviceConfiguration(args, deviceConfigurationConfigPath, faradayConfigPath)

# Check if server is to be started
if not args.start:
    logger.info("Device configuration exiting!")
    logger.info("run with --start to start server application")
    sys.exit(0)

# Load configuration from deviceconfiguration.ini file
deviceConfig.read(deviceConfigurationConfigPath)

# Global Constants
UART_PORT_APP_COMMAND = 2

# Initialize proxy object
proxy = faradaybasicproxyio.proxyio()

# Initialize faraday command module
faradayCmd = faradaycommands.faraday_commands()

# Initialize Flask microframework
app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def unitconfig():
    """
    This function is called when the RESTful API GET or POST call is made to the '/' of the operating port. Querying a
    GET will command the local and queried unit's device configuration in Flash memory and return the information as a
    JSON dictionary. Issuing a POST will cause the local .INI file configuration to be loaded into the respective units
    Flash memory device configuration.

    """
    if request.method == "POST":
        try:
            print "test POST"
            # Obtain URL parameters (for local unit device callsign/ID assignment)
            callsign = request.args.get("callsign", "%")
            nodeid = request.args.get("nodeid", "%")

            # Read Faraday device configuration file
            faradayConfigPath = os.path.join(path, "faraday_config.ini")
            logger.debug('faraday_config.ini PATH: ' + faradayConfigPath)

            # Read configuration file
            faradayConfig = ConfigParser.RawConfigParser()
            faradayConfig.read(faradayConfigPath)

            # Create dictionaries of each config section
            device_basic_dict = dict()
            device_basic_dict['CONFIGBOOTBITMASK'] = faradayConfig.get("BASIC", 'CONFIGBOOTBITMASK')
            device_basic_dict['CALLSIGN'] = faradayConfig.get("BASIC", 'CALLSIGN')
            device_basic_dict['ID'] = faradayConfig.get("BASIC", 'ID')
            device_basic_dict['GPIO_P3'] = faradayConfig.get("BASIC", 'GPIO_P3')
            device_basic_dict['GPIO_P4'] = faradayConfig.get("BASIC", 'GPIO_P4')
            device_basic_dict['GPIO_P5'] = faradayConfig.get("BASIC", 'GPIO_P5')

            device_rf_dict = dict()
            device_rf_dict['BOOT_FREQUENCY_MHZ'] = faradayConfig.get("RF", 'BOOT_FREQUENCY_MHZ')
            device_rf_dict['BOOT_RF_POWER'] = faradayConfig.get("RF", 'BOOT_RF_POWER')

            device_gps_dict = dict()
            device_gps_dict['DEFAULT_LATITUDE'] = faradayConfig.get("GPS", 'DEFAULT_LATITUDE')
            device_gps_dict['DEFAULT_LATITUDE_DIRECTION'] = faradayConfig.get("GPS", 'DEFAULT_LATITUDE_DIRECTION')
            device_gps_dict['DEFAULT_LONGITUDE'] = faradayConfig.get("GPS", 'DEFAULT_LONGITUDE')
            device_gps_dict['DEFAULT_LONGITUDE_DIRECTION'] = faradayConfig.get("GPS", 'DEFAULT_LONGITUDE_DIRECTION')
            device_gps_dict['DEFAULT_ALTITUDE'] = faradayConfig.get("GPS", 'DEFAULT_ALTITUDE')
            device_gps_dict['DEFAULT_ALTITUDE_UNITS'] = faradayConfig.get("GPS", 'DEFAULT_ALTITUDE_UNITS')
            device_gps_dict['GPS_BOOT_BIT'] = faradayConfig.get("GPS", 'GPS_BOOT_BIT')
            device_gps_dict['GPS_PRESENT_BIT'] = faradayConfig.get("GPS", 'GPS_PRESENT_BIT')

            device_telemetry_dict = dict()
            device_telemetry_dict['UART_TELEMETRY_BOOT_BIT'] = faradayConfig.get("TELEMETRY", 'UART_TELEMETRY_BOOT_BIT')
            device_telemetry_dict['RF_TELEMETRY_BOOT_BIT'] = faradayConfig.get("TELEMETRY", 'RF_TELEMETRY_BOOT_BIT')
            device_telemetry_dict['TELEMETRY_DEFAULT_UART_INTERVAL'] = faradayConfig.get("TELEMETRY", 'TELEMETRY_DEFAULT_UART_INTERVAL')
            device_telemetry_dict['TELEMETRY_DEFAULT_RF_INTERVAL'] = faradayConfig.get("TELEMETRY", 'TELEMETRY_DEFAULT_RF_INTERVAL')

            # Create device configuration module object to use for programming packet creation
            device_config_object = deviceconfig.DeviceConfigClass()

            # Update the device configuration object with the fields obtained from the INI configuration files loaded
            config_bitmask = device_config_object.create_bitmask_configuration(int(device_basic_dict['CONFIGBOOTBITMASK']))
            status_basic = device_config_object.update_basic(
                config_bitmask, str(device_basic_dict['CALLSIGN']),
                int(device_basic_dict['ID']), int(device_basic_dict['GPIO_P3']),
                int(device_basic_dict['GPIO_P4']), int(device_basic_dict['GPIO_P5']))
            status_rf = device_config_object.update_rf(
                float(device_rf_dict['BOOT_FREQUENCY_MHZ']),
                int(device_rf_dict['BOOT_RF_POWER']))
            status_gps = device_config_object.update_gps(
                device_config_object.update_bitmask_gps_boot(int(device_gps_dict['GPS_PRESENT_BIT']),
                                                             int(device_gps_dict['GPS_BOOT_BIT'])),
                device_gps_dict['DEFAULT_LATITUDE'], device_gps_dict['DEFAULT_LATITUDE_DIRECTION'],
                device_gps_dict['DEFAULT_LONGITUDE'], device_gps_dict['DEFAULT_LONGITUDE_DIRECTION'],
                device_gps_dict['DEFAULT_ALTITUDE'], device_gps_dict['DEFAULT_ALTITUDE_UNITS'])
            status_telem = device_config_object.update_telemetry(device_config_object.update_bitmask_telemetry_boot(
                int(device_telemetry_dict['RF_TELEMETRY_BOOT_BIT']),
                int(device_telemetry_dict['UART_TELEMETRY_BOOT_BIT'])),
                int(device_telemetry_dict['TELEMETRY_DEFAULT_UART_INTERVAL']),
                int(device_telemetry_dict['TELEMETRY_DEFAULT_RF_INTERVAL']))

            if (status_basic and status_gps and status_rf and status_telem):
                # Create the raw device configuration packet to send to unit
                device_config_packet = device_config_object.create_config_packet()

                # Transmit device configuration to local unit as supplied by the function arguments
                proxy.POST(str(callsign), int(nodeid), UART_PORT_APP_COMMAND,
                           faradayCmd.CommandLocal(faradayCmd.CMD_DEVICECONFIG, device_config_packet))

                return '', 204  # nothing to return but successful transmission
            else:
                logger.error('Failed to create configuration packet!')
                return 'Failed to create configuration packet!', 400

        except ValueError as e:
            logger.error("ValueError: " + str(e))
            return json.dumps({"error": str(e)}), 400

        except IndexError as e:
            logger.error("IndexError: " + str(e))
            return json.dumps({"error": str(e)}), 400

        except KeyError as e:
            logger.error("KeyError: " + str(e))
            return json.dumps({"error": str(e)}), 400

    else:  # If a GET command
        """
            Provides a RESTful interface to device-configuration at URL '/'
            """
        try:
            # Obtain URL parameters
            callsign = request.args.get("callsign", "%")
            nodeid = request.args.get("nodeid", "%")

            callsign = str(callsign).upper()
            nodeid = str(nodeid)

            # Flush all old data from recieve buffer of local unit
            proxy.FlushRxPort(callsign, nodeid, proxy.CMD_UART_PORT)

            proxy.POST(str(callsign), int(nodeid), UART_PORT_APP_COMMAND,
                       faradayCmd.CommandLocalSendReadDeviceConfig())

            # Wait enough time for Faraday to respond to commanded memory read.
            time.sleep(2)

            try:
                # Retrieve the next device configuration read packet to arrive
                data = proxy.GETWait(str(callsign), str(nodeid), proxy.CMD_UART_PORT, 2)

                # Create device configuration module object
                device_config_object = deviceconfig.DeviceConfigClass()

                # Decode BASE64 JSON data packet into
                data = proxy.DecodeRawPacket(data[0]["data"])  # Get first item
                data = device_config_object.extract_config_packet(data)

                # Parse device configuration into dictionary
                parsed_config_dict = device_config_object.parse_config_packet(data)

                # Encoded dictionary data for save network transit
                pickled_parsed_config_dict = json.dumps(parsed_config_dict)
                pickled_parsed_config_dict_b64 = base64.b64encode(pickled_parsed_config_dict)

            except ValueError as e:
                print e
            except IndexError as e:
                print e
            except KeyError as e:
                print e
            except StandardError as e:
                print e

        except ValueError as e:
            logger.error("ValueError: " + str(e))
            return json.dumps({"error": str(e)}), 400
        except IndexError as e:
            logger.error("IndexError: " + str(e))
            return json.dumps({"error": str(e)}), 400
        except KeyError as e:
            logger.error("KeyError: " + str(e))
            return json.dumps({"error": str(e)}), 400

        return json.dumps({"data": pickled_parsed_config_dict_b64}, indent=1), 200, \
            {'Content-Type': 'application/json'}


def main():
    """Main function which starts telemetry worker thread + Flask server."""
    logger.info('Starting device configuration server')

    # Start the flask server on localhost:8001
    telemetryhost = deviceConfig.get("FLASK", "HOST")
    telemetryport = deviceConfig.getint("FLASK", "PORT")

    app.run(host=telemetryhost, port=telemetryport, threaded=True)


if __name__ == '__main__':
    main()
