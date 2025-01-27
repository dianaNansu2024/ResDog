import tkinter as tk
from tkinter import messagebox, scrolledtext
import gps
import folium
from time import sleep
from pidog import Pidog
import threading
import webbrowser
import os

class PiDogGPSApp:
    def __init__(self, master):
        """
        Initialize the PiDog GPS Tracking Application.
        
        Args:
            master (tk.Tk): The main window of the application
        """
        self.master = master
        master.title("PiDog GPS Tracker")
        master.geometry("600x500")

        # Initialize PiDog and GPS
        self.my_dog = Pidog()
        self.session = gps.gps(mode=gps.WATCH_ENABLE)
        
        # Tracking variables
        self.map_file = "robot_map.html"
        self.robot_map = None
        self.path_coordinates = []
        self.gps_failure_count = 0
        self.tracking_active = False

        # Create UI components
        self.create_widgets()

    def create_widgets(self):
        """
        Create and layout the application's UI components.
        """
        # Status Display
        self.status_label = tk.Label(
            self.master, 
            text="PiDog GPS Tracker", 
            font=("Arial", 14, "bold")
        )
        self.status_label.pack(pady=10)

        # Log Area
        self.log_area = scrolledtext.ScrolledText(
            self.master, 
            wrap=tk.WORD, 
            width=70, 
            height=15
        )
        self.log_area.pack(padx=10, pady=10)

        # Control Buttons Frame
        button_frame = tk.Frame(self.master)
        button_frame.pack(pady=10)

        # Start Tracking Button
        self.start_button = tk.Button(
            button_frame, 
            text="Start Tracking", 
            command=self.start_tracking,
            bg="green",
            fg="white"
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        # Stop Tracking Button
        self.stop_button = tk.Button(
            button_frame, 
            text="Stop Tracking", 
            command=self.stop_tracking,
            bg="red",
            fg="white",
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # View Map Button
        self.view_map_button = tk.Button(
            button_frame, 
            text="View Map", 
            command=self.open_map,
            state=tk.DISABLED
        )
        self.view_map_button.pack(side=tk.LEFT, padx=5)

    def log_message(self, message):
        """
        Log messages to the scrolled text area.
        
        Args:
            message (str): Message to log
        """
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)

    def initialize_map(self, lat, lon):
        """
        Initialize a folium map centered at the given coordinates.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
        """
        self.robot_map = folium.Map(location=[lat, lon], zoom_start=18)
        folium.Marker(
            location=[lat, lon], 
            popup="Start Location", 
            icon=folium.Icon(color='green')
        ).add_to(self.robot_map)
        self.robot_map.save(self.map_file)
        self.view_map_button.config(state=tk.NORMAL)

    def update_map(self, lat, lon):
        """
        Update the map with new coordinates.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
        """
        self.path_coordinates.append((lat, lon))
        folium.Marker(
            location=[lat, lon], 
            popup="Robot Location"
        ).add_to(self.robot_map)
        folium.PolyLine(
            self.path_coordinates, 
            color="blue", 
            weight=2.5
        ).add_to(self.robot_map)
        self.robot_map.save(self.map_file)

    def get_gps_coordinates(self):
        """
        Fetch GPS coordinates from the module.
        
        Returns:
            tuple: (latitude, longitude) or (None, None)
        """
        try:
            report = self.session.next()
            if report['class'] == 'TPV':
                lat = getattr(report, 'lat', None)
                lon = getattr(report, 'lon', None)
                return lat, lon
        except StopIteration:
            pass
        except Exception as e:
            self.log_message(f"GPS Error: {e}")
        return None, None

    def tracking_thread(self):
        """
        Background thread for tracking PiDog's movement and GPS coordinates.
        """
        try:
            # Wait for initial GPS fix
            lat, lon = None, None
            while lat is None or lon is None and self.tracking_active:
                lat, lon = self.get_gps_coordinates()
                if lat and lon:
                    self.log_message(f"Initial GPS Fix: Lat {lat}, Lon {lon}")
                    self.master.after(0, self.initialize_map, lat, lon)
                else:
                    self.gps_failure_count += 1
                    if self.gps_failure_count > 5:
                        self.log_message("GPS not working. Check connection.")
                        break
                sleep(1)

            # Tracking loop
            while self.tracking_active:
                lat, lon = self.get_gps_coordinates()
                if lat and lon:
                    self.gps_failure_count = 0
                    self.log_message(f"Tracking: Lat {lat}, Lon {lon}")
                    self.master.after(0, self.update_map, lat, lon)
                    
                    # Perform PiDog action (trot)
                    self.my_dog.do_action('trot', step_count=10, speed=95)
                else:
                    self.gps_failure_count += 1
                    self.log_message("Waiting for GPS data...")
                    
                    if self.gps_failure_count > 10:
                        self.log_message("GPS not responding.")
                        break
                
                sleep(1)

        except Exception as e:
            self.log_message(f"Tracking Error: {e}")
        finally:
            self.master.after(0, self.stop_tracking)

    def start_tracking(self):
        """
        Start the tracking process.
        """
        self.tracking_active = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.log_message("Starting PiDog GPS Tracking...")
        
        # Start tracking in a separate thread
        threading.Thread(
            target=self.tracking_thread, 
            daemon=True
        ).start()

    def stop_tracking(self):
        """
        Stop the tracking process.
        """
        self.tracking_active = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.log_message("Stopping PiDog GPS Tracking...")
        
        # Close PiDog resources
        self.my_dog.close()

    def open_map(self):
        """
        Open the generated map in the default web browser.
        """
        if os.path.exists(self.map_file):
            webbrowser.open('file://' + os.path.realpath(self.map_file))
        else:
            messagebox.showerror("Error", "Map file not found.")

def main():
    """
    Main function to launch the PiDog GPS Tracking Application.
    """
    root = tk.Tk()
    app = PiDogGPSApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()