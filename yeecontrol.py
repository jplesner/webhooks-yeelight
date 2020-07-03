#!/usr/bin/python

import socket  
import time
import fcntl
import re
import os
import errno
import struct
from time import sleep
from threading import Thread
from collections import OrderedDict

detected_bulbs = {}
bulb_idx2ip = {}
DEBUGGING = False
RUNNING = True
current_command_id = 0
MCAST_GRP = '239.255.255.250'

scan_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
fcntl.fcntl(scan_socket, fcntl.F_SETFL, os.O_NONBLOCK)
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
listen_socket.bind(("", 1982))
fcntl.fcntl(listen_socket, fcntl.F_SETFL, os.O_NONBLOCK)
mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

def debug(msg):
  if DEBUGGING:
    print(msg)

def next_cmd_id():
  global current_command_id
  current_command_id += 1
  return current_command_id
    
def send_search_broadcast():
  '''
  multicast search request to all hosts in LAN, do not wait for response
  '''
  multicase_address = (MCAST_GRP, 1982) 
  debug("send search request")
  msg = "M-SEARCH * HTTP/1.1\r\n" 
  msg = msg + "HOST: 239.255.255.250:1982\r\n"
  msg = msg + "MAN: \"ssdp:discover\"\r\n"
  msg = msg + "ST: wifi_bulb"
  scan_socket.sendto(msg.encode(), multicase_address)

def bulbs_detection_loop():
  '''
  a standalone thread broadcasting search request and listening on all responses
  '''
  debug("bulbs_detection_loop running")
  search_interval=3000
  read_interval=100
  time_elapsed=0

  while RUNNING:
    if time_elapsed%search_interval == 0:
      send_search_broadcast()

    # scanner
    while True:
      try:
        data = scan_socket.recv(2048)
      except socket.error as e:
        err = e.args[0]
        if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
            break
        else:
            print(e)
            sys.exit(1)
      handle_search_response(data.decode())

    # passive listener 
    while True:
      try:
        data, addr = listen_socket.recvfrom(2048)
      except socket.error as e:
        err = e.args[0]
        if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
            break
        else:
            print(e)
            sys.exit(1)
      handle_search_response(data.decode())

    time_elapsed+=read_interval
    sleep(read_interval/1000.0)
  scan_socket.close()
  listen_socket.close()

def get_param_value(data, param):
  '''
  match line of 'param = value'
  '''
  param_re = re.compile(param+":\s*([ -~]*)") #match all printable characters
  match = param_re.search(data)
  value=""
  if match != None:
    value = match.group(1)
    return value
    
def handle_search_response(data):
  '''
  Parse search response and extract all interested data.
  If new bulb is found, insert it into dictionary of managed bulbs. 
  '''
  location_re = re.compile("Location.*yeelight[^0-9]*([0-9]{1,3}(\.[0-9]{1,3}){3}):([0-9]*)")
  match = location_re.search(data)
  if match == None:
    debug( "invalid data received: " + data )
    return 

  host_ip = match.group(1)
  if host_ip in detected_bulbs:
    bulb_id = detected_bulbs[host_ip][0]
  else:
    bulb_id = len(detected_bulbs)+1
  host_port = match.group(3)
  model = get_param_value(data, "model")
  power = get_param_value(data, "power") 
  bright = get_param_value(data, "bright")
  rgb = get_param_value(data, "rgb")
  # use two dictionaries to store index->ip and ip->bulb map
  detected_bulbs[host_ip] = [bulb_id, model, power, bright, rgb, host_port]
  bulb_idx2ip[bulb_id] = host_ip

def any_bulbs_detected():
  if not bool(detected_bulbs):
    return False
  elif 1 not in bulb_idx2ip:
    return False
  else:
    detected_bulbs.clear()
    sleep(10.00)
    return True

def close():
  RUNNING = False
