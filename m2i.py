#!/usr/bin/python

# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
#

__app__ = "MQTT to Insteon API"
__version__ = "0.0.1"
__author__ = "Chad S. Lauritsen"
__contact__ = "csl4jc@gmail.com"
__copyright__ = "Copyright (C) 2015 Chad S. Lauritsen"

import os
import sys
import time
import logging
import logging.handlers
import dbm
import yaml
from insteon import Insteon

import paho.mqtt.client as mqtt

class MQTTInsteonAPIGateway:
    insteon_api = None
    db = None
    mqttc = None
    config = None
    logger = None
    stdout = None
    stderr = None

    host = None
    port = None
    username = None
    password = None

    consumer_key = None 
    consumer_secret = None 
    access_key = None 
    access_secret = None 

    config_file = None

    formatter = None
    handler = None

    devices = None
    scenes = None
    houses = None


    def __init__(self, pidfile, stdin="/dev/null", stdout='/dev/null', stderr='/dev/null'):

        def resolve_path(path):
            return path if path[0] == '/' else os.path.join(os.path.dirname(os.path.realpath(__file__)), path)
        cf = file(resolve_path('m2i.yaml'), 'r')
        self.config = yaml.load(cf)
        cf.close()

        self.insteon_api = Insteon(self.config['insteon_api']['username']
            , self.config['insteon_api']['password']
            , self.config['insteon_api']['api_key'])

        self.handler = logging.handlers.RotatingFileHandler('/tmp/m2i.log', maxBytes=1024*1024, backupCount=5)
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(self.formatter)

        self.logger = logging.getLogger()
        self.logger.setLevel(self.config['general']['logging_level'])
        self.logger.addHandler(self.handler)

        # If you want to use a specific client id, use
        # mqttc = mqtt.Client("client-id")
        # but note that the client id must be unique on the broker. Leaving the client
        # id parameter empty will generate a random id for you.
        self.mqttc = mqtt.Client()
        self.mqttc.on_message = self.on_message
        self.mqttc.on_connect = self.on_connect
        self.mqttc.on_publish = self.on_publish
        self.mqttc.on_subscribe = self.on_subscribe
        # Uncomment to enable debug messages
        #mqttc.on_log = on_log
        self.username = self.config['mqtt']['username']
        self.password = self.config['mqtt']['password']
        self.host = self.config['mqtt']['host']
        self.port = self.config['mqtt']['port']

    def stop(self):
        """ Shutdown the external resources and close the db """
        self.mqttc.disconnect() 

    def on_connect(self, mqttc, obj, flags, rc):
        self.log(logging.DEBUG, "Connected to %s:%s" % (mqttc._host, mqttc._port))
        self.subscribe()

    def subscribe(self):
        self.mqttc.subscribe("/home/insteon/command/#", 0)

    def on_message(self, mqttc, obj, msg):
        self.log(logging.DEBUG, msg.topic+" "+str(msg.qos)+" "+str(msg.payload))
        if msg.topic.startswith('/home/insteon/command/device/'):
            iid = msg.topic[(msg.topic.rindex('/') + 1):]
            
            for d in self.insteon_api.devices:
                if iid == d.properties['InsteonID']:
                    try:
                        d.send_command(str(msg.payload))
                    except:
                        print 'Failed to send command %s to %s' % (msg.payload, msg.topic)
                        

    def on_publish(self, mqttc, obj, mid):
        self.log(logging.INFO, "mid: "+str(mid))

    def on_subscribe(self, mqttc, obj, mid, granted_qos):
        self.log(logging.INFO, "Subscribed: "+str(mid)+" "+str(granted_qos))

    def on_log(self, mqttc, obj, level, string):
        self.log(logging.INFO, string)

    def reload(self):
        pass

    def run(self):
        self.log(logging.INFO, 'running')
        if self.username:
            self.mqttc.username_pw_set(self.username, self.password)
        self.log(logging.DEBUG, 'Connecting to MQTT broker %s:%d' % (self.host,self.port))
        self.mqttc.connect(self.host, int(self.port), 60)

        i = 0
        rc = 0
        while i < 9:
            while rc == 0:
                rc = self.mqttc.loop_forever()
                if rc == 0:
                    i = 0
                else:
                    self.log(logging.DEBUG, "rc: "+str(rc))
                i = i + 1

        self.log(logging.DEBUG, "rc: "+str(rc))


    def log(self, level, message):
        if self.logger:
            self.logger.log(level, message)

    def resolve_path(path):
        return path if path[0] == '/' else os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

if "__main__" == __name__:

    me = MQTTInsteonAPIGateway('/tmp/m2i.pid')
    me.stdout = me.stderr = sys.stdout

    me.run()

