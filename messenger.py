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

        formatted_time = datetime.now().strftime("%H:%M:%S")

        self.displayed_message_ids = set()


        self.message_id = 0  # Add this line to initialize message ID

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


        # Load settings from file
        self.settings = self.load_settings()

        # Use loaded settings for ip and port
        ip = self.settings.get("server_ip")
        port = self.settings.get("server_port")

        # Create a Text widget to display decoded packets
        self.text_widget = tk.Text(root, wrap="char", height=18, width=120)  # word wrap
        self.text_widget.grid(row=0, column=3, padx=10, pady=10, rowspan=5, sticky="nsew")

        # Create a "Messages" Text Display
        self.messages_text_widget = tk.Text(root, wrap="char", height=7, width=120)
        self.messages_text_widget.grid(row=9, column=3, padx=10, pady=10, rowspan=5, sticky="nsew")

        # Configure row and column resizing the entire GUI
        for i in range(10):  # Assuming the widgets are in rows 0-9
            root.grid_rowconfigure(i, weight=1)  # Make rows expandable
            root.grid_columnconfigure(3, weight=1)  # Make column 3 expandable


        #to label
        self.to_label = tk.Label(root, text="To:")
        self.to_label.grid(row=19, column=1, pady=5, padx=5, sticky="e")

        # Add this line to create a trace on the StringVar
        self.to_var.trace_add("write", lambda *args: self.to_var.set(self.to_var.get().upper()))

        #callsign to entry
        self.to_entry = tk.Entry(root, width=13, textvariable=self.to_var)  # Set textvariable
        self.to_entry.grid(row=19, column=3, pady=5, padx=5, sticky="w")  # Center the entry widget

        #message label
        self.message_label = tk.Label(root, text="Msg:")
        self.message_label.grid(row=20, column=1, pady=5, padx=5, sticky="e")

        #Message entry
        self.message_entry = tk.Entry(root, width=160, textvariable=self.message_var)  # Set textvariable
        self.message_entry.grid(row=20, column=3, pady=5, padx=5, sticky="w", columnspan=2)  # Center the entry widget


        # Create a "Send Message" button
        self.send_message_button = tk.Button(root, text="Send Message", command=self.send_message, state=tk.DISABLED)
        self.send_message_button.grid(row=20, column=4, pady=5, padx=5, sticky="w")  # Center the button

        # Bind the <Tab> key to the callback function
        self.message_entry.bind("<Tab>", self.focus_send_button)

        # Create a "Cancel Retry" button
        self.cancel_retry_button = tk.Button(root, text="Abort Retries", command=lambda: self.cancel_retry_timer(self.message_id))
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

        # Create an Exit button and place it at coordinates (x=10, y=10)
        self.exit_button = tk.Button(root, width=10, text="Exit", command=self.exit_app)
        self.exit_button.grid(row=0, column=4, pady=5, padx=5, sticky="w")  # Center the button

        # Create a socket and connect to Dire Wolf
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.settings.get("server_ip", ip), int(self.settings.get("server_port", port))))
            print("logged in")

            # Create a queue to communicate between threads
            self.queue = queue.Queue()

            # Start the thread to receive data
            self.receive_thread = threading.Thread(target=self.receive_data)
            self.receive_thread.daemon = True
            self.receive_thread.start()

            # Set up a callback to update the GUI
            self.root.after(100, self.update_gui)

        except ConnectionRefusedError as e:
            print(f"Connection refused: {e}")
            self.display_error_message(formatted_time, "Connection refused! Please check your settings!")


        # Create a queue to communicate between threads
        self.queue = queue.Queue()

        # Start the thread to receive data
        self.receive_thread = threading.Thread(target=self.receive_data)
        self.receive_thread.daemon = True
        self.receive_thread.start()

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

        # Create an About menu
        about_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="About", command=self.show_about)

    def focus_send_button(self, event):
        # Callback function to set focus on the "Send Message" button
        self.send_message_button.focus_set()
        return "break"  # Prevent the default behavior of the <Tab> key

    def display_error_message(self, formatted_message, message):
        self.text_widget.insert(tk.END, f"{formatted_message}: {message}\n")
        self.text_widget.see(tk.END)  # Scroll to the end of the text

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

        callsign_var = tk.StringVar(value=self.callsign_var.get())
        tocall_var = tk.StringVar(value=self.tocall_var.get())
        ip_var = tk.StringVar(value=self.settings.get("server_ip", ""))
        port_var = tk.StringVar(value=self.settings.get("server_port", ""))

        callsign_entry = tk.Entry(settings_window, width=30, textvariable=callsign_var)
        callsign_entry.grid(row=0, column=1, pady=5, padx=5, sticky="w")

        tocall_entry = tk.Entry(settings_window, width=30, textvariable=tocall_var)
        tocall_entry.grid(row=1, column=1, pady=5, padx=5, sticky="w")

        ip_entry = tk.Entry(settings_window, width=30, textvariable=ip_var)
        ip_entry.grid(row=2, column=1, pady=5, padx=5, sticky="w")

        port_entry = tk.Entry(settings_window, width=30, textvariable=port_var)
        port_entry.grid(row=3, column=1, pady=5, padx=5, sticky="w")

        # New label and entry for digi_path
        digi_path_label = tk.Label(settings_window, text="Digi Path 1")
        digi_path_label.grid(row=4, column=0, pady=5, padx=5, sticky="e")

        digi_path_var = tk.StringVar(value=self.settings.get("digi_path", ""))
        digi_path_entry = tk.Entry(settings_window, width=30, textvariable=digi_path_var)
        digi_path_entry.grid(row=4, column=1, pady=5, padx=5, sticky="w")

        # Create a Save button to save the settings to a file
        save_button = tk.Button(settings_window, text="Save", command=lambda: self.save_settings(callsign_var.get(), tocall_var.get(), ip_var.get(), port_var.get(), digi_path_var.get(), settings_window))
        save_button.grid(row=5, column=1, pady=10)

    def save_settings(self, callsign, tocall, server_ip, server_port, digi_path, settings_window):
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

        # Update the application's variables
        self.callsign_var.set(callsign)
        self.tocall_var.set(tocall)
        self.server_ip_var.set(server_ip)
        self.server_port_var.set(server_port)
        self.digi_path_var.set(digi_path)  # Add this line for the new setting

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


            # Update the application's variables
            self.callsign_var.set(callsign)
            self.tocall_var.set(tocall)
            self.server_ip_var.set(server_ip)
            self.server_port_var.set(server_port)
            self.digi_path_var.set(digi_path)
            

            return {
                "callsign": callsign,
                "tocall": tocall,
                "server_ip": server_ip,
                "server_port": server_port,
                "digi_path": digi_path  # Add this line for the new setting
            }
            
        except FileNotFoundError:
            # Create a default settings file if it doesn't exist
            default_settings = {
                "callsign": "NOCALL",
                "tocall": "APOPYT",
                "server_ip": "127.0.0.1",
                "server_port": "8100",
                "digi_path": ""  # Add this line for the new setting
            }


            with open(SETTINGS_FILE, "w") as file:
                for key, value in default_settings.items():
                    file.write(f"{key}={value}\n")

            # Update the application's variables with default values
            self.callsign_var.set(default_settings["callsign"])
            self.tocall_var.set(default_settings["tocall"])
            self.server_ip_var.set(default_settings["server_ip"])
            self.server_port_var.set(default_settings["server_port"])

            return default_settings
        except (IndexError, ValueError) as e:
            # Handle other potential issues with the file content
            messagebox.showerror("Error", f"Error loading settings: {e}")
            return {}

            
    def send_beacon(self):
        # Get values from entry widgets
        arg1 = self.callsign_var.get()
        arg2 = self.tocall_var.get()
        arg3 = self.message_var.get()
        path = self.digi_path_var.get()

        # Encode data using your custom encoding functions
        encoded_data = encode_ui_frame(arg1, arg2, arg3, path)  # Updated function call

        # Initialize formatted_time outside the try block
        formatted_time = datetime.now().strftime("%H:%M:%S")

        try:
            # Send the encoded data to the server
            self.socket.send(encoded_data)

            # Display success message in the GUI
            self.display_packet(formatted_time, "Beacon Sent successfully")

            self.message_var.set("")  # Clear the message string


        except Exception as e:
            # Handle errors if sending fails
            error_message = f"Failed to send beacon: {str(e)}"
            self.display_packet(formatted_time, error_message)



    def exit_app(self):
        # Cleanly close the socket and exit the application
        self.socket.close()
        self.root.destroy()
        
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

    def open_link(self):
        webbrowser.open("https://www.patreon.com/NA7Q/membership")

    def show_message_window(self):
        # Create a Toplevel window for the message
        message_window = tk.Toplevel(self.root)
        message_window.title("Send Message")

    def receive_data(self):

        while True:
            data = self.socket.recv(1024)
            if not data:
                break

            for byte in data:
                frame_buffer.append(byte)
                if len(frame_buffer) > 1 and byte == KISS_FEND:
                    hex_data = ' '.join([hex(b)[2:].zfill(2) for b in frame_buffer])
                    formatted_time = datetime.now().strftime("%H:%M:%S")  # Get the current system time
                    decoded_packet = decode_kiss_frame(frame_buffer)
                    if decoded_packet:
                        #self.queue.put((formatted_time, decoded_packet))
                        self.parse_packet(decoded_packet)
                    frame_buffer.clear()


    def update_gui(self):
        try:
            formatted_time, decoded_packet = self.queue.get_nowait()
            self.display_packet(formatted_time, decoded_packet)
        except queue.Empty:
            pass

        # Set up the callback to run after 100 milliseconds
        self.root.after(100, self.update_gui)

    def parse_packet(self, line):
        # Initialize formatted_time outside the try block
        formatted_time = datetime.now().strftime("%H:%M:%S")
        callsign = self.callsign_var.get()
        tocall = self.tocall_var.get()
        path = self.digi_path_var.get()

        # Process APRS message
        #print("Received raw APRS packet: {}".format(line.strip()))
        self.display_packet(formatted_time, line.strip())
        parts = line.strip().split(':')
        if len(parts) >= 2:
            from_callsign = parts[0].split('>')[0].strip()
            message_text = ':'.join(parts[1:]).strip()
            
            #Decide if TCPIP Message
            if message_text.startswith("}") and "TCPIP" in message_text:
                #create new message text and new callsign
                message_text = message_text.split("}", 1)[1].strip()
                
                from_callsign = message_text.split('>')[0].strip()
                message_text = message_text.split(':', 1)[1].strip()
                
                
                if message_text.startswith(":{}".format(callsign)):
                    # Extract and process ACK ID if present
                    if "ack" in message_text:
                        parts = message_text.split("ack", 1)
                        if len(parts) == 2 and parts[1].isdigit():
                            ack_id = parts[1]
                            process_ack_id(from_callsign, ack_id)
                            self.display_packet(formatted_time, f"Ack Received for message {ack_id}.")
                    # End RXd ACK ID for MSG Retries

                    if "{" in message_text[-6:]:
                        message_id = message_text.split('{')[1]
                        ack_message = send_ack_message(from_callsign, message_id)  
                        # Encode data using your custom encoding functions
                        ack_message = encode_ui_frame(callsign, tocall, ack_message, path)  # Updated function call
                        raw_packet = decode_kiss_frame(ack_message)
                        
                        self.socket.send(ack_message)    
                        
                        # Display success message in the GUI
                        self.display_packet(formatted_time, raw_packet) 
                        self.display_packet(formatted_time, "Ack Sent successfully")
 
                        # Remove the first 11 characters from the message to exclude the "Callsign :" prefix
                        verbose_message = message_text[11:].split('{')[0].strip()
                        
                        self.display_packet_messages(formatted_time, from_callsign, verbose_message, message_id)

            #Not TCPIP
            elif message_text.startswith(":{}".format(callsign)):
                # Extract and process ACK ID if present
                if "ack" in message_text:
                    parts = message_text.split("ack", 1)
                    if len(parts) == 2 and parts[1].isdigit():
                        ack_id = parts[1]
                        process_ack_id(from_callsign, ack_id)
                        self.display_packet(formatted_time, f"Ack Received for message {ack_id}.")
                # End RXd ACK ID for MSG Retries

                if "{" in message_text[-6:]:
                    message_id = message_text.split('{')[1]
                    ack_message = send_ack_message(from_callsign, message_id)  
                    # Encode data using your custom encoding functions
                    ack_message = encode_ui_frame(callsign, tocall, ack_message, path)  # Updated function call
                    raw_packet = decode_kiss_frame(ack_message)
                    
                    self.socket.send(ack_message)    
                    
                    # Display success message in the GUI
                    self.display_packet(formatted_time, raw_packet) 
                    self.display_packet(formatted_time, "Ack Sent successfully")

                    # Remove the first 11 characters from the message to exclude the "Callsign :" prefix
                    verbose_message = message_text[11:].split('{')[0].strip()
                    
                    self.display_packet_messages(formatted_time, from_callsign, verbose_message, message_id)


    def display_packet(self, formatted_time, packet):
        # Update the Text widget with the new packet
        self.text_widget.config(state="normal")
        self.text_widget.insert(tk.END, f"{formatted_time}: {packet}\n")
        self.text_widget.config(state="disabled")
        self.text_widget.see(tk.END)

    def display_packet_messages(self, formatted_time, from_callsign, message_text, message_id):
        # Check if the message ID has already been displayed
        if message_id not in self.displayed_message_ids:
            # Display the message in the "Messages" window
            # (Assuming self.messages_text_widget is your widget for displaying messages)
            self.messages_text_widget.config(state="normal")
            self.messages_text_widget.insert(tk.END, f"{formatted_time}: [{from_callsign}] {message_text} [ID:{message_id}]\n")
            self.messages_text_widget.config(state="disabled")
            self.messages_text_widget.see(tk.END)

            # Add the message ID to the set of displayed message IDs
            self.displayed_message_ids.add(message_id)

    def check_message_entry(self, *args):
        # Callback function to check the message entry and enable/disable the button
        message_text = self.message_var.get().strip()
        if message_text:
            # If there is text in the message entry, enable the button
            self.send_message_button.config(state=tk.NORMAL)
        else:
            # If the message entry is empty, disable the button
            self.send_message_button.config(state=tk.DISABLED)


    def send_message(self):
        global TIMER_START
        # Get values from entry widgets
        arg1 = self.callsign_var.get()
        arg2 = self.tocall_var.get()
        arg3 = self.message_var.get()  # Use the new entry for sending messages
        to = self.to_var.get()  # Use the new entry for sending messages
        path = self.digi_path_var.get()  # Use the new entry for sending messages

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

        try:
            # Send the encoded data to the TNC
            self.socket.send(encoded_data)

            # Display success message in the GUI
            self.display_packet(formatted_time, raw_packet)
            self.display_packet(formatted_time, "Message Sent successfully")

            self.display_packet_messages(formatted_time, arg1, arg3, self.message_id)

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

    def cancel_retry_timer(self, message_id):
        formatted_time = datetime.now().strftime("%H:%M:%S")
        if message_id in self.sent_messages:
            if self.sent_messages[message_id]['timer'] and self.sent_messages[message_id]['timer'].is_alive():
                self.sent_messages[message_id]['timer'].cancel()
                self.display_packet(formatted_time, "Retry Aborted!")
                # Disable the "Cancel Retry" button after canceling the retry timer
                self.cancel_retry_button['state'] = 'disabled'


    def retry_message(self, message_id):
        global received_acks, RETRY_INTERVAL, MAX_RETRIES
        formatted_time = datetime.now().strftime("%H:%M:%S")
        path = self.digi_path_var.get()


        if message_id in self.sent_messages:
            retry_count = self.sent_messages[message_id]['retry_count']

            if retry_count < MAX_RETRIES:
                # Calculate the retry interval based on the retry count
                retry_interval = RETRY_INTERVAL * 2 ** retry_count

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
                self.display_packet(formatted_time, f"Retry Sent successfully (Interval: {retry_interval} seconds)")

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
