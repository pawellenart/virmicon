import threading
import time
import tkinter as tk
from tkinter import scrolledtext, ttk

import keyboard
import mido
import rtmidi


class Virmicon:
    def __init__(self, midi_port_name="Virmicon", config=None):
        self.midi_port_name = midi_port_name
        # Initialize alphanumeric keys with different control values
        self.config = config or {chr(k): 60 + (k % 36) for k in range(48, 58)}
        # Add all alphabetic keys (a-z)
        self.config.update({chr(k): 60 + (k % 36) for k in range(97, 123)})
        self.running = True
        self.cc_states = {key: False for key in self.config}

        # Set up the GUI
        self.root = tk.Tk()
        self.root.title("Virmicon v1.0")
        self.midiout = rtmidi.MidiOut()
        self.available_ports = [f"[{i}] {port}" for i,
                                port in enumerate(self.midiout.get_ports())]

        # Dropdown to select MIDI port
        self.midi_port_var = tk.StringVar()
        self.midi_port_dropdown = ttk.Combobox(
            self.root, textvariable=self.midi_port_var, values=self.available_ports, state='readonly')
        self.midi_port_dropdown.bind(
            "<<ComboboxSelected>>", self.on_midi_port_change)
        if self.available_ports:
            self.midi_port_var.set(self.available_ports[0])
        self.midi_port_dropdown.pack(fill=tk.X, padx=10, pady=5)

        # Button to clear the log
        self.clear_log_button = tk.Button(
            self.root, text="Clear Log", command=self.clear_log)
        self.clear_log_button.pack(anchor='w', padx=10, pady=5)

        # Log window
        self.log_text = scrolledtext.ScrolledText(
            self.root, width=50, height=20, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Connect to initial MIDI port
        self.connect_to_midi_port()

    def connect_to_midi_port(self):
        selected_port = self.midi_port_var.get()
        available_ports = self.midiout.get_ports()

        if selected_port and any(selected_port.endswith(f"[{i}] {port}") for i, port in enumerate(available_ports)):
            port_index = next(i for i, port in enumerate(
                available_ports) if selected_port.endswith(f"[{i}] {port}"))
            self.midiout.open_port(port_index)
            self.log(f"Successfully connected to MIDI port: {selected_port}")
        elif available_ports:
            self.midiout.open_port(0)
            self.log(f"No specific port selected, connected to default port: {
                     available_ports[0]}")
        else:
            self.log("No available MIDI ports found.")
            self.running = False

    def on_midi_port_change(self, event):
        if self.midiout.is_port_open():
            self.midiout.close_port()
        self.connect_to_midi_port()

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state='disabled')

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state='disabled')
        self.log_text.yview(tk.END)

    def send_cc(self, control, value):
        msg = mido.Message('control_change', control=control, value=value)
        self.midiout.send_message(msg.bytes())
        self.log(f"Key '{self.last_key_pressed}': Control Change: Control {
                 control}, Value: {value}")

    def key_event_handler(self, event):
        self.last_key_pressed = event.name
        if event.name == 'esc' and event.event_type == keyboard.KEY_DOWN:
            self.on_close()
        elif event.name in self.config:
            control = self.config[event.name]
            if event.event_type == keyboard.KEY_DOWN:
                # Toggle between 127 and 0 on each key press
                new_value = 0 if self.cc_states[event.name] else 127
                self.send_cc(control, new_value)
                self.cc_states[event.name] = not self.cc_states[event.name]

    def start(self):
        if not self.running:
            return
        # Run the keyboard hook and MIDI monitoring in separate threads
        threading.Thread(target=self.keyboard_listener, daemon=True).start()
        threading.Thread(target=self.monitor_midi_ports, daemon=True).start()
        self.log("Virmicon is running. Press 'esc' to quit.")
        self.root.mainloop()

    def keyboard_listener(self):
        for key in self.config.keys():
            keyboard.on_press_key(
                key, lambda e: self.key_event_handler(e), suppress=False)
        keyboard.on_press_key(
            'esc', lambda e: self.key_event_handler(e), suppress=False)
        while self.running:
            time.sleep(0.1)

    def monitor_midi_ports(self):
        while self.running:
            available_ports = self.midiout.get_ports()
            current_port_name = self.midiout.get_port_name(
                self.midiout.get_port_count() - 1) if self.midiout.get_port_count() > 0 else ""

            if available_ports and current_port_name not in available_ports:
                self.midiout.close_port()
                self.connect_to_midi_port()
            time.sleep(1)

    def on_close(self):
        self.running = False
        self.root.quit()


if __name__ == "__main__":
    controller = Virmicon()
    controller.start()
