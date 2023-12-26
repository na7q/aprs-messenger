import socket
import tkinter as tk
import tkinter.messagebox as messagebox
from datetime import datetime
import threading
import queue
import json
import os
import sys
import webbrowser
from tkinter import messagebox, font
import aprslib
import time
import errno
from tkinter import ttk

#Default Font Family: Segoe UI
#Default Font Size: 9
#Default Font Weight: normal

FONT_TYPE = 'Segoe UI'
FONT_SIZE = 10
FONT_WEIGHT = 'normal'

KISS_FEND = 0xC0  # Frame start/end marker
KISS_FESC = 0xDB  # Escape character
KISS_TFEND = 0xDC  # If after an escape, means there was an 0xC0 in the source message
KISS_TFESC = 0xDD  # If after an escape, means there was an 0xDB in the source message

# Define global constants for retry_interval and max_retries
TIMER_START = 45  # Initial retry interval in seconds
RETRY_INTERVAL = 90  # Initial retry interval in seconds. Doubles each time.
MAX_RETRIES = 3 #number of retries after the first message

# Define frame_buffer globally
frame_buffer = []

# Settings file path
SETTINGS_FILE = "settings.conf"

print("Current Working Directory:", os.getcwd())

received_acks = {}

TOCALL_DATA = {
    "BEACON": {"vendor": "APRS", "model": "Generic"},
    "ID": {"vendor": "APRS", "model": "Generic"},
    "AP1WWX": {"vendor": "TAPR", "model": "T-238+", "class": "wx"},
    "AP4R??": {"vendor": "Open Source", "model": "APRS4R", "class": "software"},
    "APAEP1": {"vendor": "Paraguay Space Agency (AEP)", "model": "EIRUAPRSDIGIS&FV1", "class": "satellite"},
    "APAF??": {"model": "AFilter"},
    "APAG??": {"model": "AGate"},
    "APAGW": {"vendor": "SV2AGW", "model": "AGWtracker", "class": "software", "os": "Windows"},
    "APAGW?": {"vendor": "SV2AGW", "model": "AGWtracker", "class": "software", "os": "Windows"},
    "APAH??": {"model": "AHub"},
    "APAM??": {"vendor": "Altus Metrum", "model": "AltOS", "class": "tracker"},
    "APAND?": {"vendor": "Open Source", "model": "APRSdroid", "os": "Android", "class": "app"},
    "APAT51": {"vendor": "Anytone", "model": "AT-D578", "class": "rig"},
    "APAT81": {"vendor": "Anytone", "model": "AT-D878", "class": "ht"},
    "APAT??": {"vendor": "Anytone"},
    "APATAR": {"vendor": "TA7W/OH2UDS Baris Dinc and TA6AEU", "model": "ATA-R APRS Digipeater", "class": "digi"},
    "APAVT5": {"vendor": "SainSonic", "model": "AP510", "class": "tracker"},
    "APAW??": {"vendor": "SV2AGW", "model": "AGWPE", "class": "software", "os": "Windows"},
    "APAX??": {"model": "AFilterX"},
    "APB2MF": {"vendor": "Mike, DL2MF", "model": "MF2APRS Radiosonde tracking tool", "class": "software", "os": "Windows"},
    "APBK??": {"vendor": "PY5BK", "model": "Bravo Tracker", "class": "tracker"},
    "APBL??": {"vendor": "BigRedBee", "model": "BeeLine GPS", "class": "tracker"},
    "APBM??": {"vendor": "R3ABM", "model": "BrandMeister DMR"},
    "APBPQ??": {"vendor": "John Wiseman, G8BPQ", "model": "BPQ32", "class": "software", "os": "Windows"},
    "APBSD?": {"vendor": "hambsd.org", "model": "HamBSD"},
    "APBT62": {"vendor": "BTech", "model": "DMR 6x2"},
    "APC???": {"vendor": "Rob Wittner, KZ5RW", "model": "APRS/CE", "class": "app"},
    "APCDS0": {"vendor": "ZS6LMG", "model": "cell tracker", "class": "tracker"},
    "APCLEY": {"vendor": "ZS6EY", "model": "EYTraker", "class": "tracker"},
    "APCLEZ": {"vendor": "ZS6EY", "model": "Telit EZ10 GSM application", "class": "tracker"},
    "APCLUB": {"model": "Brazil APRS network"},
    "APCLWX": {"vendor": "ZS6EY", "model": "EYWeather", "class": "wx"},
    "APCN??": {"vendor": "DG5OAW", "model": "carNET"},
    "APCSMS": {"vendor": "USNA", "model": "Cosmos"},
    "APCSS": {"vendor": "AMSAT", "model": "CubeSatSim CubeSat Simulator"},
    "APCTLK": {"vendor": "Open Source", "model": "Codec2Talkie", "class": "app"},
    "APCWP8": {"vendor": "GM7HHB", "model": "WinphoneAPRS", "class": "app"},
    "APDF??": {"model": "Automatic DF units"},
    "APDG??": {"vendor": "Jonathan, G4KLX", "model": "ircDDB Gateway", "class": "dstar"},
    "APDI??": {"vendor": "Bela, HA5DI", "model": "DIXPRS", "class": "software"},
    "APDNO?": {"vendor": "DO3SWW", "model": "APRSduino", "class": "tracker", "os": "embedded"},
    "APDPRS": {"vendor": "unknown", "model": "D-Star APDPRS", "class": "dstar"},
    "APDR??": {"vendor": "Open Source", "model": "APRSdroid", "os": "Android", "class": "app"},
    "APDS??": {"vendor": "SP9UOB", "model": "dsDIGI", "os": "embedded"},
    "APDST?": {"vendor": "SP9UOB", "model": "dsTracker", "os": "embedded"},
    "APDT??": {"vendor": "unknown", "model": "APRStouch Tone (DTMF)"},
    "APDU??": {"vendor": "JA7UDE", "model": "U2APRS", "class": "app", "os": "Android"},
    "APDV??": {"vendor": "OE6PLD", "model": "SSTV with APRS", "class": "software"},
    "APDW??": {"vendor": "WB2OSZ", "model": "DireWolf"},
    "APDnnn": {"vendor": "Open Source", "model": "aprsd", "class": "software", "os": "Linux/Unix"},
    "APE2A?": {"vendor": "NoseyNick, VA3NNW", "model": "Email-2-APRS gateway", "class": "software", "os": "Linux/Unix"},
    "APE???": {"model": "Telemetry devices"},
    "APECAN": {"vendor": "KT5TK/DL7AD", "model": "Pecan Pico APRS Balloon Tracker", "class": "tracker"},
    "APELK?": {"vendor": "WB8ELK", "model": "Balloon tracker", "class": "tracker"},
    "APERS?": {"vendor": "Jason, KG7YKZ", "model": "Runner tracking", "class": "tracker"},
    "APERXQ": {"vendor": "PE1RXQ", "model": "PE1RXQ APRS Tracker", "class": "tracker"},
    "APESP?": {"vendor": "LY3PH", "model": "APRS-ESP", "os": "embedded"},
    "APFG??": {"vendor": "KP4DJT", "model": "Flood Gage", "class": "software"},
    "APFI??": {"vendor": "aprs.fi", "class": "app"},
    "APFII?": {"model": "iPhone/iPad app", "vendor": "aprs.fi", "os": "ios", "class": "app"},
    "APGBLN": {"vendor": "NW5W", "model": "GoBalloon", "class": "tracker"},
    "APGO??": {"vendor": "AA3NJ", "model": "APRS-Go", "class": "app"},
    "APHAX?": {"vendor": "PY2UEP", "model": "SM2APRS SondeMonitor", "class": "software", "os": "Windows"},
    "APHBL?": {"vendor": "KF7EEL", "model": "HBLink D-APRS Gateway", "class": "software"},
    "APHH?": {"vendor": "Steven D. Bragg, KA9MVA", "model": "HamHud", "class": "tracker"},
    "APHK??": {"vendor": "LA1BR", "model": "Digipeater/tracker"},
    "APHMEY": {"vendor": "Tapio Heiskanen, OH2TH", "model": "APRS-IS Client for Athom Homey", "contact": "oh2th@iki.fi"},
    "APHPIA": {"vendor": "HP3ICC", "model": "Arduino APRS"},
    "APHPIB": {"vendor": "HP3ICC", "model": "Python APRS Beacon"},
    "APHPIW": {"vendor": "HP3ICC", "model": "Python APRS WX"},
    "APHT??": {"vendor": "IU0AAC", "model": "HMTracker", "class": "tracker"},
    "APHW??": {"vendor": "HamWAN"},
    "API282": {"vendor": "Icom", "model": "IC-2820", "class": "dstar"},
    "API31": {"vendor": "Icom", "model": "IC-31", "class": "dstar"},
    "API410": {"vendor": "Icom", "model": "IC-4100", "class": "dstar"},
    "API51": {"vendor": "Icom", "model": "IC-51", "class": "dstar"},
    "API510": {"vendor": "Icom", "model": "IC-5100", "class": "dstar"},
    "API710": {"vendor": "Icom", "model": "IC-7100", "class": "dstar"},
    "API80": {"vendor": "Icom", "model": "IC-80", "class": "dstar"},
    "API880": {"vendor": "Icom", "model": "IC-880", "class": "dstar"},
    "API910": {"vendor": "Icom", "model": "IC-9100", "class": "dstar"},
    "API92": {"vendor": "Icom", "model": "IC-92", "class": "dstar"},
    "API970": {"vendor": "Icom", "model": "IC-9700", "class": "dstar"},
    "API???": {"vendor": "Icom", "model": "unknown", "class": "dstar"},
    "APIC??": {"vendor": "HA9MCQ", "model": "PICiGATE"},
    "APIE??": {"vendor": "W7KMV", "model": "PiAPRS"},
    "APIN??": {"vendor": "AB0WV", "model": "PinPoint"},
    "APIZCI": {"vendor": "TA7W/OH2UDS and TA6AEU", "model": "hymTR IZCI Tracker", "class": "tracker", "os": "embedded"},
    "APJ8??": {"vendor": "KN4CRD", "model": "JS8Call", "class": "software"},
    "APJA??": {"vendor": "K4HG & AE5PL", "model": "JavAPRS"},
    "APJE??": {"vendor": "Gregg Wonderly, W5GGW", "model": "JeAPRS"},
    "APJI??": {"vendor": "Peter Loveall, AE5PL", "model": "jAPRSIgate", "class": "software"},
    "APJID2": {"vendor": "Peter Loveall, AE5PL", "model": "D-Star APJID2", "class": "dstar"},
    "APJS??": {"vendor": "Peter Loveall, AE5PL", "model": "javAPRSSrvr"},
    "APJY??": {"vendor": "KA2DDO", "model": "YAAC", "class": "software"},
    "APK003": {"vendor": "Kenwood", "model": "TH-D72", "class": "ht"},
    "APK004": {"vendor": "Kenwood", "model": "TH-D74", "class": "ht"},
    "APK005": {"vendor": "Kenwood", "model": "TH-D75", "class": "ht"},
    "APK0??": {"vendor": "Kenwood", "model": "TH-D7", "class": "ht"},
    "APK1??": {"vendor": "Kenwood", "model": "TM-D700", "class": "rig"},
    "APKHTW": {"vendor": "Kip, W3SN", "model": "Tempest Weather Bridge", "class": "wx", "os": "embedded", "contact": "w3sn@moxracing.33mail.com"},
    "APKRAM": {"vendor": "kramstuff.com", "model": "Ham Tracker", "class": "app", "os": "ios"},
    "APLC??": {"vendor": "DL3DCW", "model": "APRScube"},
    "APLDI?": {"vendor": "David, OK2DDS", "model": "LoRa IGate/Digipeater", "class": "digi"},
    "APLDM?": {"vendor": "David, OK2DDS", "model": "LoRa Meteostation", "class": "wx"},
    "APLETK": {"vendor": "DL5TKL", "model": "T-Echo", "class": "tracker", "os": "embedded", "contact": "cfr34k-git@tkolb.de"},
    "APLG??": {"vendor": "OE5BPA", "model": "LoRa Gateway/Digipeater", "class": "digi"},
    "APLIG?": {"vendor": "TA2MUN/TA9OHC", "model": "LightAPRS Tracker", "class": "tracker"},
    "APLM??": {"vendor": "WA0TQG", "class": "software"},
    "APLO??": {"vendor": "SQ9MDD", "model": "LoRa KISS TNC/Tracker", "class": "tracker"},
    "APLP0?": {"vendor": "SQ9P", "model": "fajne digi", "class": "digi", "os": "embedded", "contact": "sq9p.peter@gmail.com"},
    "APLP1?": {"vendor": "SQ9P", "model": "LORA/FSK/AFSK fajny tracker", "class": "tracker", "os": "embedded", "contact": "sq9p.peter@gmail.com"},
    "APLRG?": {"vendor": "Ricardo, CD2RXU", "model": "ESP32 LoRa iGate", "class": "igate", "os": "embedded", "contact": "richonguzman@gmail.com"},
    "APLRT?": {"vendor": "Ricardo, CD2RXU", "model": "ESP32 LoRa Tracker", "class": "tracker", "os": "embedded", "contact": "richonguzman@gmail.com"},
    "APLS??": {"vendor": "SARIMESH", "model": "SARIMESH", "class": "software"},
    "APLT??": {"vendor": "OE5BPA", "model": "LoRa Tracker", "class": "tracker"},
    "APLU0?": {"vendor": "SP9UP", "model": "ESP32/SX12xx LoRa iGate / Digi", "class": "digi", "os": "embedded", "contact": "wajdzik.m@gmail.com"},
    "APLU1?": {"vendor": "SP9UP", "model": "ESP32/SX12xx LoRa Tracker", "class": "tracker", "os": "embedded", "contact": "wajdzik.m@gmail.com"},
    "APMG??": {"vendor": "Alex, AB0TJ", "model": "PiCrumbs and MiniGate", "class": "software"},
    "APMI01": {"vendor": "Microsat", "os": "embedded", "model": "WX3in1"},
    "APMI02": {"vendor": "Microsat", "os": "embedded", "model": "WXEth"},
    "APMI03": {"vendor": "Microsat", "os": "embedded", "model": "PLXDigi"},
    "APMI04": {"vendor": "Microsat", "os": "embedded", "model": "WX3in1 Mini"},
    "APMI05": {"vendor": "Microsat", "os": "embedded", "model": "PLXTracker"},
    "APMI06": {"vendor": "Microsat", "os": "embedded", "model": "WX3in1 Plus 2.0"},
    "APMI??": {"vendor": "Microsat", "os": "embedded"},
    "APMON?": {"vendor": "Amon Schumann, DL9AS", "model": "APRS Balloon Tracker", "class": "tracker", "os": "embedded"},
    "APMPAD": {"vendor": "DF1JSL", "model": "Multi-Purpose APRS Daemon", "class": "service", "contact": "joerg.schultze.lutter@gmail.com", "features": ["messaging"]},
    "APMQ??": {"vendor": "WB2OSZ", "model": "Ham Radio of Things"},
    "APMT??": {"vendor": "LZ1PPL", "model": "Micro APRS Tracker", "class": "tracker"},
    "APN102": {"vendor": "Gregg Wonderly, W5GGW", "model": "APRSNow", "class": "app", "os": "ipad"},
    "APN2??": {"vendor": "VE4KLM", "model": "NOSaprs for JNOS 2.0"},
    "APN3??": {"vendor": "Kantronics", "model": "KPC-3"},
    "APN9??": {"vendor": "Kantronics", "model": "KPC-9612"},
    "APNCM": {"vendor": "Keith Kaiser, WA0TJT", "model": "Net Control Manager", "class": "software", "os": "browser", "contact": "wa0tjt@gmail.com"},
    "APND??": {"vendor": "PE1MEW", "model": "DIGI_NED"},
    "APNIC4": {"vendor": "SQ5EKU", "model": "BidaTrak", "class": "tracker", "os": "embedded"},
    "APNJS?": {"vendor": "Julien Sansonnens, HB9HRD", "model": "Web messaging service", "class": "service", "contact": "julien.owls@gmail.com", "features": ["messaging"]},
    "APNK01": {"vendor": "Kenwood", "model": "TM-D700", "class": "rig", "features": ["messaging"]},
    "APNK80": {"vendor": "Kantronics", "model": "KAM"},
    "APNKMP": {"vendor": "Kantronics", "model": "KAM+"},
    "APNKMX": {"vendor": "Kantronics", "model": "KAM-XL"},
    "APNM??": {"vendor": "MFJ", "model": "TNC"},
    "APNP??": {"vendor": "PacComm", "model": "TNC"},
    "APNT??": {"vendor": "SV2AGW", "model": "TNT TNC as a digipeater", "class": "digi"},
    "APNU??": {"vendor": "IW3FQG", "model": "UIdigi", "class": "digi"},
    "APNV0??": {"vendor": "SQ8L", "model": "VP-Digi", "os": "embedded"},
    "APNV1??": {"vendor": "SQ8L", "model": "VP-Node", "os": "embedded"},
    "APNV??": {"vendor": "SQ8L"},
    "APNW??": {"vendor": "SQ3FYK", "model": "WX3in1", "os": "embedded"},
    "APNX??": {"vendor": "K6DBG", "model": "TNC-X"},
    "APOA??": {"vendor": "OpenAPRS", "model": "app", "class": "app", "os": "ios"},
    "APOCSG": {"vendor": "N0AGI", "model": "POCSAG"},
    "APOG7?": {"vendor": "OpenGD77", "model": "OpenGD77", "os": "embedded", "contact": "Roger VK3KYY/G4KYF"},
    "APOLU?": {"vendor": "AMSAT-LU", "model": "Oscar", "class": "satellite"},
    "APOPYT": {"vendor": "Mike, NA7Q", "model": "NA7Q Messenger", "class": "software", "contact": "mike.ph4@gmail.com"},
    "APOSAT": {"vendor": "Mike, NA7Q", "model": "Open Source Satellite Gateway", "class": "service", "contact": "mike.ph4@gmail.com"},
    "APOSMS": {"vendor": "Mike, NA7Q", "model": "Open Source SMS Gateway", "class": "service", "contact": "mike.ph4@gmail.com", "features": ["messaging"]},
    "APOT??": {"vendor": "Argent Data Systems", "model": "OpenTracker", "class": "tracker"},
    "APOVU?": {"vendor": "K J Somaiya Institute", "model": "BeliefSat"},
    "APOZ??": {"vendor": "OZ1EKD, OZ7HVO", "model": "KissOZ", "class": "tracker"},
    "APP6??": {"model": "APRSlib"},
    "APPCO?": {"vendor": "RadCommSoft, LLC", "model": "PicoAPRSTracker", "class": "tracker", "os": "embedded", "contact": "ab4mw@radcommsoft.com"},
    "APPIC?": {"vendor": "DB1NTO", "model": "PicoAPRS", "class": "tracker"},
    "APPM??": {"vendor": "DL1MX", "model": "rtl-sdr Python iGate", "class": "software"},
    "APPRIS": {"vendor": "DF1JSL", "model": "Apprise APRS plugin", "class": "service", "contact": "joerg.schultze.lutter@gmail.com", "features": ["messaging"]},
    "APPT??": {"vendor": "JF6LZE", "model": "KetaiTracker", "class": "tracker"},
    "APQTH?": {"vendor": "Weston Bustraan, W8WJB", "model": "QTH.app", "class": "software", "os": "macOS", "features": ["messaging"]},
    "APR2MF": {"vendor": "Mike, DL2MF", "model": "MF2wxAPRS Tinkerforge gateway", "class": "wx", "os": "Windows"},
    "APR8??": {"vendor": "Bob Bruninga, WB4APR", "model": "APRSdos", "class": "software"},
    "APRARX": {"vendor": "Open Source", "model": "radiosonde_auto_rx", "class": "software", "os": "Linux/Unix"},
    "APRFG?": {"vendor": "RF.Guru", "contact": "info@rf.guru"},
    "APRFGB": {"vendor": "RF.Guru", "model": "APRS LoRa Pager", "os": "embedded", "contact": "info@rf.guru"},
    "APRFGD": {"vendor": "RF.Guru", "model": "APRS Digipeater", "class": "digi", "os": "embedded", "contact": "info@rf.guru"},
    "APRFGH": {"vendor": "RF.Guru", "model": "Hotspot", "class": "rig", "os": "embedded", "contact": "info@rf.guru"},
    "APRFGI": {"vendor": "RF.Guru", "model": "LoRa APRS iGate", "class": "igate", "os": "embedded", "contact": "info@rf.guru"},
    "APRFGL": {"vendor": "RF.Guru", "model": "Lora APRS Digipeater", "class": "digi", "os": "embedded", "contact": "info@rf.guru"},
    "APRFGM": {"vendor": "RF.Guru", "model": "Mobile Radio", "class": "rig", "os": "embedded", "contact": "info@rf.guru"},
    "APRFGP": {"vendor": "RF.Guru", "model": "Portable Radio", "class": "ht", "os": "embedded", "contact": "info@rf.guru"},
    "APRFGR": {"vendor": "RF.Guru", "model": "Repeater", "class": "rig", "os": "embedded", "contact": "info@rf.guru"},
    "APRFGT": {"vendor": "RF.Guru", "model": "LoRa APRS Tracker", "class": "tracker", "os": "embedded", "contact": "info@rf.guru"},
    "APRFGW": {"vendor": "RF.Guru", "model": "LoRa APRS Weather Station", "class": "wx", "os": "embedded", "contact": "info@rf.guru"},
    "APRG??": {"vendor": "OH2GVE", "model": "aprsg", "class": "software", "os": "Linux/Unix"},
    "APRHH?": {"vendor": "Steven D. Bragg, KA9MVA", "model": "HamHud", "class": "tracker"},
    "APRNOW": {"vendor": "Gregg Wonderly, W5GGW", "model": "APRSNow", "class": "app", "os": "ipad"},
    "APRPR?": {"vendor": "Robert DM4RW, Peter DL6MAA", "model": "Teensy RPR TNC", "class": "tracker", "os": "embedded", "contact": "dm4rw@skywaves.de"},
    "APRRDZ": {"model": "rdzTTGOsonde", "vendor": "DL9RDZ", "class": "tracker"},
    "APRRF?": {"vendor": "Jean-Francois Huet F1EVM", "model": "Tracker for RRF", "class": "tracker", "os": "embedded", "contact": "f1evm@f1evm.fr", "features": ["messaging"]},
    "APRRT?": {"vendor": "RPC Electronics", "model": "RTrak", "class": "tracker"},
    "APRS": {"vendor": "Unknown", "model": "Unknown"},
    "APRX??": {"vendor": "Kenneth W. Finnegan, W6KWF", "model": "Aprx", "class": "igate", "os": "Linux/Unix"},
    "APS???": {"vendor": "Brent Hildebrand, KH2Z", "model": "APRS+SA", "class": "software"},
    "APSAR": {"vendor": "ZL4FOX", "model": "SARTrack", "class": "software", "os": "Windows"},
    "APSC??": {"vendor": "OH2MQK, OH7LZB", "model": "aprsc", "class": "software"},
    "APSF??": {"vendor": "F5OPV, SFCP_LABS", "model": "embedded APRS devices", "os": "embedded"},
    "APSFLG": {"vendor": "F5OPV, SFCP_LABS", "model": "LoRa/APRS Gateway", "class": "digi", "os": "embedded"},
    "APSFRP": {"vendor": "F5OPV, SFCP_LABS", "model": "VHF/UHF Repeater", "os": "embedded"},
    "APSFTL": {"vendor": "F5OPV, SFCP_LABS", "model": "LoRa/APRS Telemetry Reporter", "os": "embedded"},
    "APSFWX": {"vendor": "F5OPV, SFCP_LABS", "model": "embedded Weather Station", "class": "wx", "os": "embedded"},
    "APSK63": {"vendor": "Chris Moulding, G4HYG", "model": "APRS Messenger", "class": "software", "os": "Windows"},
    "APSMS?": {"vendor": "Paul Dufresne", "model": "SMS gateway", "class": "software"},
    "APSRF?": {"vendor": "SoftRF", "model": "Ham Edition", "class": "tracker", "os": "embedded"},
    "APSTM?": {"vendor": "W7QO", "model": "Balloon tracker", "class": "tracker"},
    "APSTPO": {"vendor": "N0AGI", "model": "Satellite Tracking and Operations", "class": "software"},
    "APT2??": {"vendor": "Byonics", "model": "TinyTrak2", "class": "tracker"},
    "APT3??": {"vendor": "Byonics", "model": "TinyTrak3", "class": "tracker"},
    "APT4??": {"vendor": "Byonics", "model": "TinyTrak4", "class": "tracker"},
    "APTB??": {"vendor": "BG5HHP", "model": "TinyAPRS"},
    "APTCHE": {"vendor": "PU3IKE", "model": "TcheTracker, Tcheduino", "class": "tracker"},
    "APTCMA": {"vendor": "Cleber, PU1CMA", "model": "CAPI Tracker", "class": "tracker"},
    "APTEMP": {"vendor": "KL7AF", "model": "APRS-Tempest Weather Gateway", "class": "wx", "os": "Linux/Unix", "contact": "kl7af@foghaven.net"},
    "APTKJ?": {"vendor": "W9JAJ", "model": "ATTiny APRS Tracker", "os": "embedded"},
    "APTNG?": {"vendor": "Filip YU1TTN", "model": "Tango Tracker", "class": "tracker"},
    "APTPN?": {"vendor": "KN4ORB", "model": "TARPN Packet Node Tracker", "class": "tracker"},
    "APTR??": {"vendor": "Motorola", "model": "MotoTRBO"},
    "APTT?": {"vendor": "Byonics", "model": "TinyTrak", "class": "tracker"},
    "APTW??": {"vendor": "Byonics", "model": "WXTrak", "class": "wx"},
    "APU1??": {"vendor": "Roger Barker, G4IDE", "model": "UI-View16", "class": "software", "os": "Windows"},
    "APU2?": {"vendor": "Roger Barker, G4IDE", "model": "UI-View32", "class": "software", "os": "Windows"},
    "APUDR?": {"vendor": "NW Digital Radio", "model": "UDR"},
    "APVE??": {"vendor": "unknown", "model": "EchoLink"},
    "APVM??": {"vendor": "Digital Radio China Club", "model": "DRCC-DVM", "class": "igate"},
    "APVR??": {"vendor": "unknown", "model": "IRLP"},
    "APW9??": {"vendor": "Mile Strk, 9A9Y", "model": "WX Katarina", "class": "wx", "os": "embedded", "features": ["messaging"]},
    "APWA??": {"vendor": "KJ4ERJ", "model": "APRSISCE", "class": "software", "os": "Android"},
    "APWEE?": {"vendor": "Tom Keffer and Matthew Wall", "model": "WeeWX Weather Software", "class": "software", "os": "Linux/Unix"},
    "APWM??": {"vendor": "KJ4ERJ", "model": "APRSISCE", "class": "software", "os": "Windows Mobile", "features": ["messaging", "item-in-msg"]},
    "APWW??": {"vendor": "KJ4ERJ", "model": "APRSIS32", "class": "software", "os": "Windows", "features": ["messaging", "item-in-msg"]},
    "APWnnn": {"vendor": "Sproul Brothers", "model": "WinAPRS", "class": "software", "os": "Windows"},
    "APX???": {"vendor": "Open Source", "model": "Xastir", "class": "software", "os": "Linux/Unix"},
    "APXR??": {"vendor": "G8PZT", "model": "Xrouter"},
    "APY01D": {"vendor": "Yaesu", "model": "FT1D", "class": "ht"},
    "APY02D": {"vendor": "Yaesu", "model": "FT2D", "class": "ht"},
    "APY05D": {"vendor": "Yaesu", "model": "FT5D", "class": "ht"},
    "APY300": {"vendor": "Yaesu", "model": "FTM-300D", "class": "rig"},
    "APY400": {"vendor": "Yaesu", "model": "FTM-400", "class": "rig"},
    "APYS??": {"vendor": "W2GMD", "model": "Python APRS", "class": "software"},
    "APZ18": {"vendor": "IW3FQG", "model": "UIdigi", "class": "digi"},
    "APZ186": {"vendor": "IW3FQG", "model": "UIdigi", "class": "digi"},
    "APZ19": {"vendor": "IW3FQG", "model": "UIdigi", "class": "digi"},
    "APZ247": {"model": "UPRS", "vendor": "NR0Q"},
    "APZG??": {"vendor": "OH2GVE", "model": "aprsg", "class": "software", "os": "Linux/Unix"},
    "APZMAJ": {"vendor": "M1MAJ", "model": "DeLorme inReach Tracker"},
    "APZMDR": {"vendor": "Open Source", "model": "HaMDR", "class": "tracker", "os": "embedded"},
    "APZTKP": {"vendor": "Nick Hanks, N0LP", "model": "TrackPoint", "class": "tracker", "os": "embedded"},
    "APZWKR": {"vendor": "GM1WKR", "model": "NetSked", "class": "software"},
    "APnnnD": {"vendor": "Painter Engineering", "model": "uSmartDigi D-Gate", "class": "dstar"},
    "APnnnU": {"vendor": "Painter Engineering", "model": "uSmartDigi Digipeater", "class": "digi"},
    "PSKAPR": {"vendor": "Open Source", "model": "PSKmail", "class": "software"},
}


COMMENT_DATA = {
    "_ ": {"vendor": "Yaesu", "model": "VX-8", "class": "ht"},
    "_\"": {"vendor": "Yaesu", "model": "FTM-350", "class": "rig"},
    "_#": {"vendor": "Yaesu", "model": "VX-8G", "class": "ht"},
    "_$": {"vendor": "Yaesu", "model": "FT1D", "class": "ht"},
    "_(": {"vendor": "Yaesu", "model": "FT2D", "class": "ht"},
    "_0": {"vendor": "Yaesu", "model": "FT3D", "class": "ht"},
    "_3": {"vendor": "Yaesu", "model": "FT5D", "class": "ht"},
    "_1": {"vendor": "Yaesu", "model": "FTM-300D", "class": "rig"},
    "_)": {"vendor": "Yaesu", "model": "FTM-100D", "class": "rig"},
    "_%": {"vendor": "Yaesu", "model": "FTM-400DR", "class": "rig"},
    "_4": {"vendor": "Yaesu", "model": "FTM-500DR   ", "class": "rig"},    
    "(5": {"vendor": "Anytone", "model": "D578UV", "class": "ht"},
    "(8": {"vendor": "Anytone", "model": "D878UV", "class": "ht"},
    "|3": {"vendor": "Byonics", "model": "TinyTrak3", "class": "tracker"},
    "|4": {"vendor": "Byonics", "model": "TinyTrak4", "class": "tracker"},
    "^v": {"vendor": "HinzTec", "model": "anyfrog"},
    "*v": {"vendor": "KissOZ", "model": "Tracker", "class": "tracker"},
}


#Implementation for ack check with Message Retries #TODO
def process_ack_id(from_callsign, ack_id):
    print("Received ACK from {}: {}".format(from_callsign, ack_id))
    received_acks.setdefault(from_callsign, set()).add(ack_id)

def send_ack_message(sender, message_id):
    ack_message = 'ack{}'.format(message_id)
    sender_length = len(sender)
    spaces_after_sender = ' ' * max(0, 9 - sender_length)
    ack_packet_format = ':{}{}:{}'.format(sender, spaces_after_sender, ack_message)
    print(ack_packet_format)
    return ack_packet_format
    
def send_rej_message(sender, message_id):
    rej_message = 'rej{}'.format(message_id)
    sender_length = len(sender)
    spaces_after_sender = ' ' * max(0, 9 - sender_length)
    rej_packet_format = ':{}{}:{}'.format(sender, spaces_after_sender, rej_message)
    rej_packet = rej_packet_format.encode()
    print("Sent REJ to {}: {}".format(sender, rej_message))
    print("Outgoing REJ packet: {}".format(rej_packet.decode()))
    return rej_packet

def format_aprs_packet(callsign, message):
    sender_length = len(callsign)
    spaces_after_sender = ' ' * max(0, 9 - sender_length) #1,9 - Changed 9-16
    aprs_packet_format = ':{}{}:{}'.format(callsign, spaces_after_sender, message)
    return aprs_packet_format

def process_tocall(tocall, comment):
    print("Input:", tocall)

    # Check for exact match in TOCALL_DATA
    if tocall in TOCALL_DATA:
        print("Exact match found.")
        return TOCALL_DATA[tocall].get("model", tocall)

    # Find the key with the maximum length of matching portion in TOCALL_DATA
    best_match_tocall = max(
        (key for key in TOCALL_DATA if key.count("?") > 0 and len(key) == len(tocall) and tocall.startswith(key[:-key.count("?")])),
        key=lambda key: len(key[:-key.count("?")]),
        default=None
    )

    if best_match_tocall:
        print(f"Best match found with key in TOCALL_DATA: {best_match_tocall}")
        return TOCALL_DATA[best_match_tocall].get("model", tocall)

    # Check for matches in TOCALL_DATA based on the suffixes in comment
    for suffix in COMMENT_DATA:
        if comment.endswith(suffix):
            print(f"Match found in TOCALL_DATA for suffix: {suffix}")
            return COMMENT_DATA[suffix].get("model", tocall)

    print("No match found. Returning the original input.")
    return tocall  # Return the original tocall when no model is found


# Encode KISS Call SSID Destination
def encode_address(address, final):
    try:
        if "-" not in address:
            address = address + "-0"  # default to SSID 0
        call, ssid = address.split('-')
        call = call.ljust(6)  # pad with spaces
        encoded_call = [ord(x) << 1 for x in call[:6]]
        encoded_ssid = (int(ssid) << 1) | 0b01100000 | (0b00000001 if final else 0)
        return encoded_call + [encoded_ssid]
    except ValueError as e:
        print("Error encoding address:", e)

# Encode KISS Frame
def encode_ui_frame(source, destination, message, path1, path2=None):
    # Convert "None" string to actual None
    path1 = None if path1 == "None" else path1
    
    src_addr_final = (path1 is None) and (path2 is None)
    src_addr = encode_address(source.upper(), src_addr_final)
    dest_addr = encode_address(destination.upper(), False)

    path = [] if path1 is None else encode_address(path1.upper(), not path2)
    path2 = [] if path2 is None else encode_address(path2.upper(), True)

    c_byte = [0x03]
    pid = [0xF0]
    msg = [ord(c) for c in message]

    packet = dest_addr + src_addr + path + path2 + c_byte + pid + msg

    packet_escaped = []
    for x in packet:
        if x == KISS_FEND:
            packet_escaped.append(KISS_FESC)
            packet_escaped.append(KISS_TFEND)
        elif x == KISS_FESC:
            packet_escaped.append(KISS_FESC)
            packet_escaped.append(KISS_TFESC)
        else:
            packet_escaped.append(x)

    kiss_cmd = 0x00
    kiss_frame = [KISS_FEND, kiss_cmd] + packet_escaped + [KISS_FEND]
    kiss_frame = bytes(kiss_frame)
    return kiss_frame  # Make sure to return the encoded frame

def decode_address(encoded_data):
    call = "".join([chr(byte >> 1) for byte in encoded_data[:6]]).rstrip()
    ssid = (encoded_data[6] >> 1) & 0b00001111

    if ssid == 0:
        address = call
    else:
        address = f"{call}-{ssid}"

    return address

def decode_kiss_frame(kiss_frame):
    decoded_packet = []
    is_escaping = False

    for byte in kiss_frame:
        if is_escaping:
            if byte == KISS_TFEND:
                decoded_packet.append(KISS_FEND)
            elif byte == KISS_TFESC:
                decoded_packet.append(KISS_FESC)
            else:
                # Invalid escape sequence, ignore or handle as needed
                pass
            is_escaping = False
        else:
            if byte == KISS_FEND:
                if 0x03 in decoded_packet:
                    c_index = decoded_packet.index(0x03)
                    if c_index + 1 < len(decoded_packet):
                        pid = decoded_packet[c_index + 1]
                        ax25_data = bytes(decoded_packet[c_index + 2:])

                        if ax25_data and ax25_data[-1] == 0x0A:
                            ax25_data = ax25_data[:-1] + bytes([0x0D])

                        dest_addr_encoded = decoded_packet[1:8]
                        src_addr_encoded = decoded_packet[8:15]
                        src_addr = decode_address(src_addr_encoded)
                        dest_addr = decode_address(dest_addr_encoded)

                        paths_start = 15
                        paths_end = decoded_packet.index(0x03)
                        paths = decoded_packet[paths_start:paths_end]

                        if paths:
                            path_addresses = []
                            path_addresses_with_asterisk = []
                            for i in range(0, len(paths), 7):
                                path_chunk = paths[i:i+7]
                                path_address = decode_address(path_chunk)

                                if path_chunk[-1] in [0xE0, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9]:
                                    path_address_with_asterisk = f"{path_address}*"
                                else:
                                    path_address_with_asterisk = path_address

                                path_addresses.append(path_address)
                                path_addresses_with_asterisk.append(path_address_with_asterisk)

                            path_addresses_str = ','.join(path_addresses_with_asterisk)
                        else:
                            path_addresses_str = ""

                        if path_addresses_str:
                            packet = f"{src_addr}>{dest_addr},{path_addresses_str}:{ax25_data.decode('ascii', errors='ignore')}"
                        else:
                            packet = f"{src_addr}>{dest_addr}:{ax25_data.decode('ascii', errors='ignore')}"

                        formatted_time = datetime.now().strftime("%H:%M:%S")
                        print(f"{formatted_time}: {packet}")
                        return packet  # Return the decoded packet here

            elif byte == KISS_FESC:
                is_escaping = True
            else:
                decoded_packet.append(byte)

    return None  # Return None if no valid frame is found

class PacketRadioApp:
    def __init__(self, root):
        self.root = root
        root.title("NA7Q Messenger")
    
        self.socket = None

        # Dark theme colors
        bg_color = "#121212"  # Dark gray background
        text_color = "#33FF00"  # White text
        # Create a Font object with your desired font specifications
        custom_font = font.Font(family=FONT_TYPE, size=FONT_SIZE, weight=FONT_WEIGHT)

        formatted_time = datetime.now().strftime("%H:%M:%S")

        self.displayed_message_ids = set()

        self.previous_tos = {}  # Now it's an instance variable


        # Add the following variable to your class
        self.has_unacknowledged_messages = False

        self.message_id = 0  # Add this line to initialize message ID

        # Create a dictionary to store last heard stations and their timestamps
        self.last_heard_stations = {}

        # Keep track of sent messages and their retry count
        self.sent_messages = {}
        
        # Create a StringVar for the message entry
        self.message_var = tk.StringVar()

        # Use StringVar to set default values
        self.callsign_var = tk.StringVar(value="")
        self.tocall_var = tk.StringVar(value="")
        
        # Add the following lines to define self.message_var
        self.message_var = tk.StringVar(value="")  # or provide a default value if needed
        self.to_var = tk.StringVar(value="")  # or provide a default value if needed
        self.server_ip_var = tk.StringVar(value="")
        self.server_port_var = tk.StringVar(value="")
        self.digi_path_var = tk.StringVar(value="")
        self.beacon_var = tk.StringVar(value="")
        self.beacon_interval_var = tk.StringVar(value="")


        # Load settings from file
        self.settings = self.load_settings()

        # Use loaded settings for ip and port
        ip = self.settings.get("server_ip")
        port = self.settings.get("server_port")  
        
        # Create a "Last Heard" window (without making it visible)
        self.last_heard_window = tk.Toplevel(self.root)
        self.last_heard_window.title("Last Heard")
        self.last_heard_window.withdraw()  # Hide the window initially     
        
        # Bind the protocol to handle the window close event
        self.last_heard_window.protocol("WM_DELETE_WINDOW", self.on_last_heard_window_close)

        # Create a Text widget to display decoded packets
        self.text_widget = tk.Text(root, wrap="char", height=18, width=120)  # word wrap
        self.text_widget.grid(row=0, column=3, padx=10, pady=10, rowspan=5, sticky="nsew")

        # Create a "Messages" Text Display
        self.messages_text_widget = tk.Text(root, wrap="char", height=7, width=120)
        self.messages_text_widget.grid(row=9, column=3, padx=10, pady=10, rowspan=5, sticky="nsew")

        # Create a Text widget to display last heard stations
        self.last_heard_text_widget = tk.Text(self.last_heard_window, wrap="char", height=10, width=30)
        self.last_heard_text_widget.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

        # Allow the Text widget to control the size of the Toplevel window
        #self.last_heard_window.pack_propagate(True)
        self.last_heard_window.geometry("275x200")  # Set your desired width and height

        # Configure the background and text color for the text widgets
        self.text_widget.configure(font=custom_font, bg=bg_color, fg=text_color)
        self.messages_text_widget.configure(font=custom_font, bg=bg_color, fg=text_color)
        self.last_heard_text_widget.configure(font=custom_font, bg=bg_color, fg=text_color)

        # Configure row and column resizing the entire GUI
        for i in range(10):  # Assuming the widgets are in rows 0-9
            root.grid_rowconfigure(i, weight=1)  # Make rows expandable
            root.grid_columnconfigure(3, weight=1)  # Make column 3 expandable

        previous_tos = {}  # Add your actual previously used values


        #to label
        self.to_label = tk.Label(root, text="To:")
        self.to_label.grid(row=19, column=1, pady=5, padx=5, sticky="e")

        # Add this line to create a trace on the StringVar
        self.to_var.trace_add("write", lambda *args: self.to_var.set(self.to_var.get().upper()))

        #callsign to entry
        self.to_entry = tk.Entry(root, width=13, textvariable=self.to_var)  # Set textvariable
        self.to_entry.grid(row=19, column=3, pady=5, padx=5, sticky="w")  # Center the entry widget
        # Create a Combobox widget
        self.to_combobox = ttk.Combobox(root, values=previous_tos, textvariable=self.to_var)
        # Set the default value to an empty string
        self.to_combobox.set("")
        # Place the Combobox widget in the desired location
        self.to_combobox.grid(row=19, column=3, pady=5, padx=5, sticky="w")

        # Bind a callback function to handle selection changes
        self.to_combobox.bind("<<ComboboxSelected>>", self.on_to_combobox_selected)

 




        #message label
        self.message_label = tk.Label(root, text="Msg:")
        self.message_label.grid(row=20, column=1, pady=5, padx=5, sticky="e")

        #Message entry
        self.message_entry = tk.Entry(root, width=160, textvariable=self.message_var)  # Set textvariable
        self.message_entry.grid(row=20, column=3, pady=5, padx=5, sticky="w", columnspan=2)  # Center the entry widget

        # Bind the callback function to both entry widgets
        self.message_entry.bind("<KeyRelease>", self.check_message_entry)
        self.to_entry.bind("<KeyRelease>", self.check_message_entry)

        # Bind the <Tab> key to the callback function
        self.to_entry.bind("<Tab>", self.focus_message_entry)

        # Create a "Send Message" button
        self.send_message_button = tk.Button(root, text="Send Message", command=self.send_message, state=tk.DISABLED)
        self.send_message_button.grid(row=20, column=4, pady=5, padx=5, sticky="w")  # Center the button

        # Bind the <Tab> key to the callback function
        self.message_entry.bind("<Tab>", self.focus_send_button)
        # Bind the <Return> key to the callback function
        self.message_entry.bind("<Return>", self.send_message_on_enter)

        # Create a "Cancel Retry" button
        self.cancel_retry_button = tk.Button(root, text="Abort Retries", command=self.cancel_retry_timer)
        self.cancel_retry_button.grid(row=19, column=4, pady=5, padx=5, sticky="w")  # Center the button

        # Disable the button initially (assuming self.message_id is set appropriately)
        self.cancel_retry_button['state'] = 'disabled'

        # Add a trace on the StringVar to check when its value changes
        self.message_var.trace_add("write", self.check_message_entry)

        # Use StringVar to set default values
        self.callsign_var = tk.StringVar(value=self.settings.get("callsign", ""))
        self.tocall_var = tk.StringVar(value=self.settings.get("tocall", ""))
        self.server_ip_var = tk.StringVar(value=self.settings.get("server_ip", ""))
        self.server_port_var = tk.StringVar(value=self.settings.get("server_port", ""))
        self.digi_path_var = tk.StringVar(value=self.settings.get("digi_path", ""))
        self.beacon_var = tk.StringVar(value=self.settings.get("beacon", ""))
        self.beacon_interval_var = tk.StringVar(value=self.settings.get("beacon_interval", ""))


        # Create an Exit button and place it at coordinates (x=10, y=10)
        self.exit_button = tk.Button(root, width=10, text="Exit", command=self.exit_app)
        self.exit_button.grid(row=0, column=4, pady=5, padx=5, sticky="w")  # Center the button

        #self.exit_button.place(x=1030, y=10)



        # Create a "Send Beacon" button
        self.send_beacon_button = tk.Button(root, text="Send Beacon", command=self.send_beacon)
        self.send_beacon_button.grid(row=3, column=4, pady=5, padx=5, sticky="w")

        # Create a queue to communicate between threads
        self.queue = queue.Queue()

        # Start the thread to connect to the server
        self.connect_thread = threading.Thread(target=self.connect_to_server)
        self.connect_thread.daemon = True
        self.connect_thread.start()

        # Set up a callback to update the GUI
        self.root.after(100, self.update_gui)

        # Create a menu bar
        self.menu_bar = tk.Menu(root)
        root.config(menu=self.menu_bar)

        # Create a File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.exit_app)

        # Create a Settings menu
        settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Configure", command=self.configure_settings)

        # Create a Last Heard menu
        last_heard_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Last Heard", command=self.show_last_heard_window)

        # Create an About menu
        about_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="About", command=self.show_about)
    
        self.send_beacon_auto()

    def focus_message_entry(self, event):
        # Change the focus to the message_entry widget
        self.message_entry.focus_set()

    # Callback function to handle selection changes in the Combobox
    def on_to_combobox_selected(self, event):
        selected_to = self.to_combobox.get()

    # Add the following method to your class
    def send_message_on_enter(self, event):
        # Callback function to send a message when the Enter key is pressed
        if self.message_var.get().strip():
            # Only send the message if the message entry is not empty
            self.send_message()
        
    def connect_to_server(self):
        formatted_time = datetime.now().strftime("%H:%M:%S")
        ip = self.settings.get("server_ip")
        port = int(self.settings.get("server_port"))


        while True:
            try:
                formatted_time = datetime.now().strftime("%H:%M:%S")

                # Initialize the socket and connect to the TNC
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.settings.get("server_ip", ip), int(self.settings.get("server_port", port))))
                print("Connected to TNC")

                self.root.after(0, lambda: self.display_packet(formatted_time, "Connected."))


                # Create a queue to communicate between threads
                self.queue = queue.Queue()

                # Set up a callback to update the GUI
                self.root.after(100, self.update_gui)

                self.receive_data()


                # If the connection was successful, break out of the loop
                break

            except socket.error as e:
                if e.errno == errno.ECONNREFUSED:
                    print("Connection to TNC refused. Retrying in 10 seconds...")
                    self.root.after(0, lambda: self.display_packet(formatted_time, "Connection to TNC refused. Retrying..."))

                    time.sleep(10)  # Wait for 10 seconds before attempting to reconnect
                else:
                    print("Socket error:", str(e))
                    time.sleep(1)  # Wait for a while before attempting to reconnect

            except Exception as e:
                print("Error connecting to TNC: {}".format(e))
                time.sleep(1)  # Wait for a while before attempting to reconnect

            
    # TNC KISS Frames Received from RF
    def receive_data(self):
        frame_buffer = []

        while True:
            try:
                # Receive data with a timeout of 1 second
                data = self.socket.recv(1024)
                
                if not data:
                    # No data received within the timeout period
                    print("No data received. Rechecking or performing other actions...")
                    # Optionally, you can add a delay before rechecking
                    time.sleep(1)
                    continue  # Continue the loop without processing an empty frame

                for byte in data:
                    frame_buffer.append(byte)
                    if len(frame_buffer) > 1 and byte == KISS_FEND:
                        hex_data = ' '.join([hex(b)[2:].zfill(2) for b in frame_buffer])
                        formatted_time = datetime.now().strftime("%H:%M:%S")
                        decoded_packet = decode_kiss_frame(frame_buffer)
                        if decoded_packet:
                            self.parse_packet(decoded_packet)
                            self.check_for_immediate_ack(decoded_packet)
                        frame_buffer = []

            except Exception as e:
                print(f"Error in receive_frames: {str(e)}")
                self.connect_to_server()  # Reconnect to the server
                print("Reestablished connection to TNC.")
                frame_buffer = []  # Reset the frame_buffer after reconnecting


    def on_last_heard_window_close(self):
        # Callback function to withdraw the "Last Heard" window when it's closed
        self.last_heard_window.withdraw()


    def update_last_heard(self, from_callsign, tocall, message_text):
        # Update the last heard stations dictionary with the current timestamp
        
       # Call the process_tocall function with the tocall argument
        tocall = process_tocall(tocall, message_text)
        
        formatted_time = datetime.now().strftime("%H:%M:%S")

        # Check if the callsign is already in the dictionary
        if from_callsign in self.last_heard_stations:
            # Remove the existing entry
            del self.last_heard_stations[from_callsign]

        self.last_heard_stations[from_callsign] = (formatted_time, tocall)

        # Update the display in the "Last Heard" window
        self.update_last_heard_display()

    def update_last_heard_display(self):
        self.last_heard_text_widget.config(state="normal")

        # Clear the existing content in the Text widget
        self.last_heard_text_widget.delete(1.0, tk.END)

        # Display the last heard stations and their timestamps
        for callsign, (timestamp, tocall) in self.last_heard_stations.items():
            entry = f"{timestamp}: {callsign} [{tocall}]\n"
            self.last_heard_text_widget.insert(tk.END, entry)
     
        # Disable editing and scroll to the bottom
        self.last_heard_text_widget.config(state="disabled")
        self.last_heard_text_widget.see(tk.END)

    def show_last_heard_window(self):
        # Show the "Last Heard" window
        self.last_heard_window.deiconify()
        self.last_heard_window.lift()

    def focus_send_button(self, event):
        # Callback function to set focus on the "Send Message" button
        self.send_message_button.focus_set()
        return "break"  # Prevent the default behavior of the <Tab> key

    def restart_app(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def configure_settings(self):
        # Create a Toplevel window for settings
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")

        # Create labels and entry widgets for settings
        callsign_label = tk.Label(settings_window, text="CALLSIGN")
        callsign_label.grid(row=0, column=0, pady=5, padx=5, sticky="e")

        tocall_label = tk.Label(settings_window, text="TOCALL")
        tocall_label.grid(row=1, column=0, pady=5, padx=5, sticky="e")

        ip_label = tk.Label(settings_window, text="Server IP")
        ip_label.grid(row=2, column=0, pady=5, padx=5, sticky="e")

        port_label = tk.Label(settings_window, text="Server Port")
        port_label.grid(row=3, column=0, pady=5, padx=5, sticky="e")

        # New label and entry for digi_path
        digi_path_label = tk.Label(settings_window, text="Digi Path 1")
        digi_path_label.grid(row=4, column=0, pady=5, padx=5, sticky="e")

        beacon_label = tk.Label(settings_window, text="Beacon")
        beacon_label.grid(row=5, column=0, pady=5, padx=5, sticky="e")

        beacon_interval_label = tk.Label(settings_window, text="Beacon Interval")
        beacon_interval_label.grid(row=6, column=0, pady=5, padx=5, sticky="e")


        callsign_var = tk.StringVar(value=self.callsign_var.get())
        tocall_var = tk.StringVar(value=self.tocall_var.get())
        ip_var = tk.StringVar(value=self.settings.get("server_ip", ""))
        port_var = tk.StringVar(value=self.settings.get("server_port", ""))
        digi_path_var = tk.StringVar(value=self.settings.get("digi_path", ""))
        beacon_var = tk.StringVar(value=self.settings.get("beacon", ""))
        beacon_interval_var = tk.StringVar(value=self.settings.get("beacon_interval", ""))

        callsign_var.trace_add("write", lambda *args: callsign_var.set(callsign_var.get().upper()))
        tocall_var.trace_add("write", lambda *args: tocall_var.set(tocall_var.get().upper()))
        # Add this line to create a trace on the StringVar
        beacon_interval_var.trace_add("write", lambda *args: beacon_interval_var.set(''.join(c for c in beacon_interval_var.get() if c.isdigit())))
        digi_path_var.trace_add("write", lambda *args: digi_path_var.set(digi_path_var.get().upper()))


        callsign_entry = tk.Entry(settings_window, width=30, textvariable=callsign_var)
        callsign_entry.grid(row=0, column=1, pady=5, padx=5, sticky="w")

        tocall_entry = tk.Entry(settings_window, width=30, textvariable=tocall_var)
        tocall_entry.grid(row=1, column=1, pady=5, padx=5, sticky="w")
        
        #Disable TOCALL ENTRY
        tocall_entry.config(state="disabled")  # Set the state only for this entry

        ip_entry = tk.Entry(settings_window, width=30, textvariable=ip_var)
        ip_entry.grid(row=2, column=1, pady=5, padx=5, sticky="w")

        port_entry = tk.Entry(settings_window, width=30, textvariable=port_var)
        port_entry.grid(row=3, column=1, pady=5, padx=5, sticky="w")

        digi_path_entry = tk.Entry(settings_window, width=30, textvariable=digi_path_var)
        digi_path_entry.grid(row=4, column=1, pady=5, padx=5, sticky="w")

        beacon_entry = tk.Entry(settings_window, width=30, textvariable=beacon_var)
        beacon_entry.grid(row=5, column=1, pady=5, padx=5, sticky="w")

        beacon_interval_entry = tk.Entry(settings_window, width=30, textvariable=beacon_interval_var)
        beacon_interval_entry.grid(row=6, column=1, pady=5, padx=5, sticky="w")


        # Create a Save button to save the settings to a file
        save_button = tk.Button(settings_window, text="Save", command=lambda: self.save_settings(callsign_var.get(), tocall_var.get(), ip_var.get(), port_var.get(), digi_path_var.get(), beacon_var.get(), beacon_interval_var.get(), settings_window))
        save_button.grid(row=8, column=1, pady=10)

    def save_settings(self, callsign, tocall, server_ip, server_port, digi_path, beacon, beacon_interval, settings_window):
        # Convert inputs to uppercase
        callsign = callsign.upper()
        tocall = tocall.upper()
        digi_path = digi_path.upper()


        # Save the settings to a file
        with open(SETTINGS_FILE, "w") as file:
            file.write(f"CALLSIGN={callsign}\n")
            file.write(f"TOCALL={tocall}\n")
            file.write(f"SERVER_IP={server_ip}\n")
            file.write(f"SERVER_PORT={server_port}\n")
            file.write(f"DIGI_PATH={digi_path}\n")  # Add this line for the new setting
            file.write(f"BEACON={beacon}\n")  # Add this line for the new setting
            file.write(f"BEACON_INTERVAL={beacon_interval}\n")  # Add this line for the new setting


        # Update the application's variables
        self.callsign_var.set(callsign)
        self.tocall_var.set(tocall)
        self.server_ip_var.set(server_ip)
        self.server_port_var.set(server_port)
        self.digi_path_var.set(digi_path)  # Add this line for the new setting
        self.beacon_var.set(beacon)
        self.beacon_interval_var.set(beacon_interval)

        # Close the settings window
        settings_window.destroy()

        # Restart the app
        self.restart_app()
        
    def load_settings(self):
        try:
            # Load settings from the file
            with open(SETTINGS_FILE, "r") as file:
                lines = file.readlines()

            # Extract CALLSIGN, TOCALL, SERVER_IP, and SERVER_PORT values
            callsign = lines[0].strip().split("=")[1]
            tocall = lines[1].strip().split("=")[1]
            server_ip = lines[2].strip().split("=")[1]
            server_port = lines[3].strip().split("=")[1]
            # Extract DIGI_PATH value
            digi_path = lines[4].strip().split("=", 1)[1] or None
            beacon = lines[5].strip().split("=", 1)[1] or ">NA7Q Messenger" #Return empty value
            beacon_interval = lines[6].strip().split("=", 1)[1] or 0 #Return 0


            # Update the application's variables
            self.callsign_var.set(callsign)
            self.tocall_var.set(tocall)
            self.server_ip_var.set(server_ip)
            self.server_port_var.set(server_port)
            self.digi_path_var.set(digi_path)
            self.beacon_var.set(beacon)
            self.beacon_interval_var.set(beacon_interval)
            

            return {
                "callsign": callsign,
                "tocall": tocall,
                "server_ip": server_ip,
                "server_port": server_port,
                "digi_path": digi_path,  # Add this line for the new setting
                "beacon": beacon,
                "beacon_interval": beacon_interval
                

            }
            
        except FileNotFoundError:
            # Create a default settings file if it doesn't exist
            default_settings = {
                "callsign": "NOCALL",
                "tocall": "APOPYT",
                "server_ip": "127.0.0.1",
                "server_port": "8100",
                "digi_path": "",  # Add this line for the new setting
                "beacon": ">NA7Q Messenger",
                "beacon_interval": "0"
                
            }


            with open(SETTINGS_FILE, "w") as file:
                for key, value in default_settings.items():
                    file.write(f"{key}={value}\n")

            # Update the application's variables with default values
            self.callsign_var.set(default_settings["callsign"])
            self.tocall_var.set(default_settings["tocall"])
            self.server_ip_var.set(default_settings["server_ip"])
            self.server_port_var.set(default_settings["server_port"])
            self.digi_path_var.set(default_settings["digi_path"])
            self.beacon_var.set(default_settings["beacon"])
            self.beacon_interval_var.set(default_settings["beacon_interval"])


            return default_settings
        except (IndexError, ValueError) as e:
            # Handle other potential issues with the file content
            #messagebox.showerror("Error", f"Error loading settings: {e}")
            return {}

            
    def send_beacon(self):
    
            # Get values from entry widgets
            arg1 = self.callsign_var.get()
            arg2 = self.tocall_var.get()
            arg3 = self.beacon_var.get()
            path = self.digi_path_var.get()

            # Encode data using your custom encoding functions
            encoded_data = encode_ui_frame(arg1, arg2, arg3, path)  # Updated function call

            raw_packet = decode_kiss_frame(encoded_data)


            # Initialize formatted_time outside the try block
            formatted_time = datetime.now().strftime("%H:%M:%S")

            try:
                # Send the encoded data to the server
                self.socket.send(encoded_data)

                # Display success message in the GUI
                self.display_packet(formatted_time, raw_packet)

                # Display success message in the GUI
                self.display_packet(formatted_time, "Beacon Sent successfully")

            except Exception as e:
                # Handle errors if sending fails
                error_message = f"Failed to send beacon: {str(e)}"
                self.display_packet(formatted_time, error_message)

# Inside your class definition

    def send_beacon_auto(self):
        # Check if the interval is 0, and if so, break out of the loop
        if self.beacon_interval_var.get() == "0":
            return

        # Check if the socket is ready
        if not self.socket or self.socket.fileno() == -1:
            # Wait for the socket to be open
            self.root.after(1000, self.send_beacon_auto)
            return

        # Get values from entry widgets
        arg1 = self.callsign_var.get()
        arg2 = self.tocall_var.get()
        arg3 = self.beacon_var.get()
        path = self.digi_path_var.get()

        # Encode data using your custom encoding functions
        encoded_data = encode_ui_frame(arg1, arg2, arg3, path)  # Updated function call

        raw_packet = decode_kiss_frame(encoded_data)

        # Initialize formatted_time outside the try block
        formatted_time = datetime.now().strftime("%H:%M:%S")

        try:
            # Send the encoded data to the server
            self.socket.send(encoded_data)

            # Display success message in the GUI
            self.display_packet(formatted_time, raw_packet)

            # Display success message in the GUI
            self.display_packet(formatted_time, "Beacon Sent successfully")

        except Exception as e:
            # Handle errors if sending fails
            error_message = f"Failed to send beacon: {str(e)}"
            self.display_packet(formatted_time, error_message)

        # Schedule the next call to send_beacon_auto after the specified interval
        self.root.after(int(float(self.beacon_interval_var.get()) * 1000), self.send_beacon_auto)

    def exit_app(self):
        # Cleanly close the socket and exit the application
        self.socket.close()
        self.root.destroy()
        sys.exit()

    def show_about(self):
        about_text = "NA7Q APRS Messenger\nVersion 1.0\n\n" \
                     "Support me on Patreon:\n" \
                     "https://www.patreon.com/NA7Q/membership\n\n" \
                     "©2023 NA7Q"

        # Create and center the About window
        about_window = tk.Toplevel(self.root)
        about_window.title("About")

        # Calculate the center position of the main window
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        center_x = root_x + root_width // 2
        center_y = root_y + root_height // 2

        # Calculate the position to center the About window
        about_width = 350  # Adjust this value based on the content
        about_height = 180  # Adjust this value based on the content
        about_x = center_x - about_width // 2
        about_y = center_y - about_height // 2

        about_window.geometry(f"{about_width}x{about_height}+{about_x}+{about_y}")

        about_message = tk.Text(about_window, wrap="word", width=40, height=8)
        about_message.pack(padx=10, pady=10)

        # Add text to the message
        about_message.insert("end", about_text)

        # Add hyperlink to the message
        about_message.tag_configure("link", foreground="blue", underline=True)
        start_index = about_message.search("https://www.patreon.com/NA7Q/membership", "1.0", stopindex="end")
        end_index = f"{start_index}+{len('https://www.patreon.com/NA7Q/membership')}c"
        about_message.tag_add("link", start_index, end_index)
        about_message.tag_bind("link", "<Button-1>", lambda e: self.open_link())

        # Disable the Text widget
        about_message.config(state="disabled")

    def open_link(self):
        webbrowser.open("https://www.patreon.com/NA7Q/membership")

    def show_message_window(self):
        # Create a Toplevel window for the message
        message_window = tk.Toplevel(self.root)
        message_window.title("Send Message")

    #FIX ACK TO ONLY LOOK FOR OUR CALLSIGN!!!
    def check_for_immediate_ack(self, packet):
        callsign = self.callsign_var.get()
        parts = packet.strip().split(':')
        if len(parts) >= 2:
            from_callsign = parts[0].split('>')[0].strip()
            message_text = ':'.join(parts[1:]).strip()

            if "ack" in message_text and callsign in message_text:

            #if "ack" in message_text:
                parts = message_text.split("ack", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    ack_id = parts[1]
                    process_ack_id(from_callsign, ack_id)
                   # print("Immediate ACK processed from check_for_immediate_ack")
                    formatted_time = datetime.now().strftime("%H:%M:%S")                    
                    # Stop the retry timer for the corresponding message ID
                    self.stop_retry_timer(int(ack_id))

    def stop_retry_timer(self, message_id):
        formatted_time = datetime.now().strftime("%H:%M:%S")
        if message_id in self.sent_messages and 'timer' in self.sent_messages[message_id]:
            # Stop the retry timer
            self.sent_messages[message_id]['timer'].cancel()
            # Clear the timer reference
            self.sent_messages[message_id]['timer'] = None
            # Remove the message from the sent_messages dictionary
            del self.sent_messages[message_id]
            # Display a message indicating that retries are stopped
            #self.display_packet(formatted_time, f"Retries stopped for message {message_id}. Immediate ACK received.")

        # Check if there are any unacknowledged messages left
        self.has_unacknowledged_messages = any('timer' in message_info and message_info['timer'] for message_info in self.sent_messages.values())

        # Update the state of the retry button
        self.update_retry_button_state()

   
   # Add the following method to your class
    def update_retry_button_state(self):
        if not self.has_unacknowledged_messages:
            # No unacknowledged messages, disable the retry button
            self.cancel_retry_button['state'] = 'disabled'
        else:
            # Enable the retry button
            self.cancel_retry_button['state'] = 'normal'            
                
    def update_gui(self):
        try:
            formatted_time, decoded_packet = self.queue.get_nowait()
            self.display_packet(formatted_time, decoded_packet)
        except queue.Empty:
            pass

        # Set up the callback to run after 100 milliseconds
        self.root.after(100, self.update_gui)


    def aprslib_parse(self, line):
        try:
            aprs_packet = aprslib.parse(line.strip())
            lat = aprs_packet['latitude']
            lon = aprs_packet['longitude']
            from_callsign = aprs_packet['from']

            print(lat, lon)
            print("From Callsign:", from_callsign)

        except Exception as e:
            # Handle the exception (or ignore it, if no handling is needed)
            print("Error while parsing APRS packet:", e)
            
            
    def parse_packet(self, line):
        # Initialize formatted_time outside the try block
        formatted_time = datetime.now().strftime("%H:%M:%S")
        callsign = self.callsign_var.get()
        tocall = self.tocall_var.get()
        path = self.digi_path_var.get()
       
        self.aprslib_parse(line)

        # Process APRS message
        #print("Received raw APRS packet: {}".format(line.strip()))
        self.display_packet(formatted_time, line.strip())
        parts = line.strip().split(':')
        if len(parts) >= 2:
            from_callsign = parts[0].split('>')[0].strip()
            message_text = ':'.join(parts[1:]).strip()
            print("first", message_text)
            
            #data between > and :
            #destination = parts[0].split('>')[1].strip()
            
            #split at first comma. giving us tocall.
            from_tocall = parts[0].split('>')[1].split(',')[0].strip()

            print(from_tocall)
        
            # Update the "Last Heard" window with the from_callsign
            self.update_last_heard(from_callsign, from_tocall, message_text)
            
            #Decide if TCPIP Message
            if message_text.startswith("}") and "TCPIP" in message_text:
                #create new message text and new callsign
                message_text = message_text.split("}", 1)[1].strip()
                print("second", message_text)
                #new call and text
                
                from_callsign = message_text.split('>')[0].strip()
                message_text = message_text.split(':', 1)[1].strip()
                
                print("third", from_callsign, message_text)
                
                if message_text.startswith(":{}".format(callsign)):
                    # Extract and process ACK ID if present
                    if "ack" in message_text:
                        parts = message_text.split("ack", 1)
                        if len(parts) == 2 and parts[1].isdigit():
                            ack_id = parts[1]
                            process_ack_id(from_callsign, ack_id)
                            print("ack processed from parse packet")
                            self.display_packet(formatted_time, f"Ack Received for message {ack_id}.")
                    # End RXd ACK ID for MSG Retries

                    if "{" in message_text[-6:]:
                        message_id = message_text.split('{')[1]
                        ack_message = send_ack_message(from_callsign, message_id)  
                        print("parsed", ack_message)
                        # Encode data using your custom encoding functions
                        ack_message = encode_ui_frame(callsign, tocall, ack_message, path)  # Updated function call
                        raw_packet = decode_kiss_frame(ack_message)
                        
                        self.socket.send(ack_message)    
                        
                        # Display success message in the GUI
                        self.display_packet(formatted_time, raw_packet) 
                        self.display_packet(formatted_time, "Ack Sent successfully")
 
                        # Remove the first 11 characters from the message to exclude the "Callsign :" prefix
                        verbose_message = message_text[11:].split('{')[0].strip()
                        
                        self.display_packet_messages(formatted_time, from_callsign, callsign, verbose_message, message_id)
                                            
                        # Update the values in the Combobox
                        if from_callsign not in self.previous_tos:
                            self.previous_tos[from_callsign] = True
                            self.to_combobox['values'] = list(self.previous_tos.keys())


            #Not TCPIP
            elif message_text.startswith(":{}".format(callsign)):
                # Extract and process ACK ID if present
                if "ack" in message_text:
                    parts = message_text.split("ack", 1)
                    if len(parts) == 2 and parts[1].isdigit():
                        ack_id = parts[1]
                        process_ack_id(from_callsign, ack_id)
                        print("ack processed from parse packet")
                        self.display_packet(formatted_time, f"Ack Received for message {ack_id}.")
                # End RXd ACK ID for MSG Retries

                if "{" in message_text[-6:]:
                    message_id = message_text.split('{')[1]
                    ack_message = send_ack_message(from_callsign, message_id)  
                    print("parsed", ack_message)
                    # Encode data using your custom encoding functions
                    ack_message = encode_ui_frame(callsign, tocall, ack_message, path)  # Updated function call
                    raw_packet = decode_kiss_frame(ack_message)
                    
                    self.socket.send(ack_message)    
                    
                    # Display success message in the GUI
                    self.display_packet(formatted_time, raw_packet) 
                    self.display_packet(formatted_time, "Ack Sent successfully")

                    # Remove the first 11 characters from the message to exclude the "Callsign :" prefix
                    verbose_message = message_text[11:].split('{')[0].strip()
                    
                    self.display_packet_messages(formatted_time, from_callsign, callsign, verbose_message, message_id)

                    # Update the values in the Combobox
                    if from_callsign not in self.previous_tos:
                        self.previous_tos[from_callsign] = True
                        self.to_combobox['values'] = list(self.previous_tos.keys())



    def display_packet(self, formatted_time, packet):
        # Update the Text widget with the new packet
        self.text_widget.config(state="normal")
        self.text_widget.insert(tk.END, f"{formatted_time}: {packet}\n")
        self.text_widget.config(state="disabled")
        self.text_widget.see(tk.END)

    def display_packet_messages(self, formatted_time, from_callsign, callsign, message_text, message_id):
        # Check if the message ID has already been displayed
        message_tuple = (from_callsign, message_id, message_text)
        if message_tuple not in self.displayed_message_ids:
            # Display the message in the "Messages" window
            # (Assuming self.messages_text_widget is your widget for displaying messages)
            self.messages_text_widget.config(state="normal")
            self.messages_text_widget.insert(tk.END, f"{formatted_time}: [{from_callsign}>{callsign}] {message_text} [ID:{message_id}]\n")
            self.messages_text_widget.config(state="disabled")
            self.messages_text_widget.see(tk.END)

            # Add the message ID to the set of displayed message IDs
            self.displayed_message_ids.add(message_tuple)

            print(f"DEBUG: Message displayed - {message_tuple}")
        else:
            print(f"DEBUG: Message already displayed - {message_tuple}")

    def check_message_entry(self, *args):
        # Callback function to check the message entry and enable/disable the button
        message_text = self.message_var.get().strip()
        to_entry_text = self.to_var.get().strip()

        if message_text and to_entry_text:
            # If there is text in both the message entry and to_entry, enable the button
            self.send_message_button.config(state=tk.NORMAL)
        else:
            # If either the message entry or to_entry is empty, disable the button
            self.send_message_button.config(state=tk.DISABLED)

    def send_message(self):
        global TIMER_START
        # Get values from entry widgets
        arg1 = self.callsign_var.get()
        arg2 = self.tocall_var.get()
        arg3 = self.message_var.get()  # Use the new entry for sending messages
        to = self.to_var.get()  # Use the new entry for sending messages
        path = self.digi_path_var.get()  # Use the new entry for sending messages

        # Update the values in the Combobox
        if to not in self.previous_tos:
            self.previous_tos[to] = True
            self.to_combobox['values'] = list(self.previous_tos.keys())

        self.message_id += 1  # Increment the message ID

        # Format the message as an APRS packet
        formatted_message = format_aprs_packet(to, arg3)

        # Encode data using your custom encoding functions
        encoded_data = encode_ui_frame(arg1, arg2, formatted_message + "{" + str(self.message_id), path)  # Use self.message_id

        #fix path later on
        #raw_packet = "{}>{}:{}".format(arg1, arg2, formatted_message + "{" + str(self.message_id))

        raw_packet = decode_kiss_frame(encoded_data)

        # Initialize formatted_time outside the try block
        formatted_time = datetime.now().strftime("%H:%M:%S")
        
        # Set the flag to True since a message has been sent
        self.has_unacknowledged_messages = True
        # Update the state of the retry button
        self.update_retry_button_state()

        try:
            # Send the encoded data to the TNC
            self.socket.send(encoded_data)

            # Display success message in the GUI
            self.display_packet(formatted_time, raw_packet)
            self.display_packet(formatted_time, "Message Sent successfully")

            #added to callsign
            self.display_packet_messages(formatted_time, arg1, to, arg3, self.message_id)

            # Add the sent message details to the sent_messages dictionary
            self.sent_messages[self.message_id] = {
                'formatted_message': formatted_message,
                'retry_count': 0,
                'timer': threading.Timer(TIMER_START, self.retry_message, args=[self.message_id])
            }
            self.sent_messages[self.message_id]['timer'].start()

            self.message_entry.delete(0, tk.END)
            
            # Disable the button after sending until a new message is entered
            self.send_message_button.config(state=tk.DISABLED)

            # Enable the "Cancel Retry" button after sending a new message
            self.cancel_retry_button['state'] = 'normal'

        except Exception as e:
            # Handle errors if sending fails
            error_message = f"Failed to send message: {str(e)}"
            self.display_packet(formatted_time, error_message)

    def cancel_retry_timer(self):
        formatted_time = datetime.now().strftime("%H:%M:%S")
        canceled_message_ids = []  # Variable to store the canceled message_ids

        # Cancel all timers
        for message_id, message_info in self.sent_messages.items():
            if 'timer' in message_info and message_info['timer'] and message_info['timer'].is_alive():
                message_info['timer'].cancel()
                canceled_message_ids.append(message_id)

        # Clear the sent_messages dictionary
        self.sent_messages.clear()

        if canceled_message_ids:
            canceled_message_ids_str = ', '.join(map(str, canceled_message_ids))
            self.display_packet(formatted_time, f"Retry for messages {canceled_message_ids_str} Aborted!")
            # Disable the "Cancel Retry" button after canceling all timers
            self.cancel_retry_button['state'] = 'disabled'
        else:
            self.display_packet(formatted_time, "No active retry timers found to abort.")

    def retry_message(self, message_id):
        global received_acks, RETRY_INTERVAL, MAX_RETRIES
        formatted_time = datetime.now().strftime("%H:%M:%S")
        path = self.digi_path_var.get()


        if message_id in self.sent_messages:
            retry_count = self.sent_messages[message_id]['retry_count']

            if retry_count < MAX_RETRIES:
                # Calculate the retry interval based on the retry count
                retry_interval = RETRY_INTERVAL * 2 ** retry_count
                
                message_retry_count = retry_count + 1

                # Increment the retry count
                self.sent_messages[message_id]['retry_count'] += 1

                # Check if ACK is received for the message
                if self.is_ack_received(message_id):
                    # ACK received, no need to retry further
                    print(f"ACK received for message {message_id}. No further retries.")
                    # Disable the "Cancel Retry" button as there are no further retries
                    self.cancel_retry_button['state'] = 'disabled'
                    # Display success message in the GUI
                    #self.display_packet(formatted_time, f"Ack Received. No further retries for {message_id}.")
                    return

                # Resend the message
                formatted_message = self.sent_messages[message_id]['formatted_message']
                encoded_data = encode_ui_frame(self.callsign_var.get(), self.tocall_var.get(), formatted_message + "{" + str(message_id), path)
                
                #fix later to fit in path
                #raw_packet = "{}>{}{}:{}".format(self.callsign_var.get(), self.tocall_var.get(), formatted_message + "{" + str(message_id)) 
                
                raw_packet = decode_kiss_frame(encoded_data)
                
                self.socket.send(encoded_data)

                # Display success message in the GUI
                self.display_packet(formatted_time, raw_packet)
                self.display_packet(formatted_time, f"Retry {message_retry_count} Sent successfully (Interval: {retry_interval} seconds)")

                # Restart the timer for the next retry
                self.sent_messages[message_id]['timer'] = threading.Timer(retry_interval, self.retry_message, args=[message_id])
                self.sent_messages[message_id]['timer'].start()
                
                # Enable the "Cancel Retry" button
                self.cancel_retry_button['state'] = 'normal'                
                
            else:
                # Max retries reached, display an error or handle as needed
                print(f"Max retries reached for message {message_id}")
                self.display_packet(formatted_time, f"Max retries exceed for message {message_id}")

                # Disable the "Cancel Retry" button as there are no further retries
                self.cancel_retry_button['state'] = 'disabled'

    def is_ack_received(self, message_id):
        global received_acks  # Reference the global variable

        # Check if ACK is received for the specified message_id
        from_callsign = self.to_var.get()  # Replace this with the actual source callsign for ACKs
        ack_set = received_acks.get(from_callsign, set())

        # Convert message_id to string before checking
        message_id_str = str(message_id)
        
        return message_id_str in ack_set

# Create the main window
root = tk.Tk()

# Create the application instance
app = PacketRadioApp(root)

# Load settings from the file
app.load_settings()

# Start the Tkinter event loop
root.mainloop()
