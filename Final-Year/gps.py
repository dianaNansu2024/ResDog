import gps
import folium
from time import sleep
from pidog import Pidog

# Initialize the PiDog
my_dog = Pidog()
sleep(0.5)

# Set up GPS session
session = gps.gps(mode=gps.WATCH_ENABLE)

# Initialize map and file
map_file = "robot_map.html"
robot_map = None
path_coordinates = []
gps_failure_count = 0  # Tracks consecutive GPS failures

def initialize_map(lat, lon):
    """
    Initialize a folium map centered at the given latitude and longitude.
    """
    global robot_map
    robot_map = folium.Map(location=[lat, lon], zoom_start=18)
    folium.Marker(location=[lat, lon], popup="Start Location", icon=folium.Icon(color='green')).add_to(robot_map)
    robot_map.save(map_file)

def update_map(lat, lon):
    """
    Update the map with the robot's current coordinates.
    """
    global robot_map, path_coordinates

    # Add coordinates to path and update map
    path_coordinates.append((lat, lon))
    folium.Marker(location=[lat, lon], popup="Robot Location").add_to(robot_map)
    folium.PolyLine(path_coordinates, color="blue", weight=2.5).add_to(robot_map)

    # Save the updated map to an HTML file
    robot_map.save(map_file)

def get_gps_coordinates():
    """
    Fetch GPS coordinates from the module.
    Returns latitude and longitude if available, otherwise None.
    """
    try:
        report = session.next()
        if report['class'] == 'TPV':
            lat = getattr(report, 'lat', None)
            lon = getattr(report, 'lon', None)
            return lat, lon
    except StopIteration:
        pass
    except Exception as e:
        print(f"GPS Error: {e}")
    return None, None

def main():
    """
    Main function to run PiDog and GPS module together.
    """
    global robot_map, gps_failure_count

    try:
        print("Starting PiDog with GPS integration...")
        print("Waiting for initial GPS fix...")

        # Wait for initial GPS fix
        lat, lon = None, None
        while lat is None or lon is None:
            lat, lon = get_gps_coordinates()
            if lat and lon:
                print(f"Initial GPS Fix: Latitude: {lat}, Longitude: {lon}")
                initialize_map(lat, lon)
            else:
                gps_failure_count += 1
                if gps_failure_count > 5:  # If no GPS data after 5 attempts
                    print("GPS is not working. Please check the connection.")
                    gps_failure_count = 0  # Reset counter to avoid flooding messages
                sleep(1)

        gps_failure_count = 0  # Reset the counter once GPS data is received

        # Start robot actions
        while True:
            # Fetch GPS data
            lat, lon = get_gps_coordinates()
            if lat and lon:
                gps_failure_count = 0  # Reset on successful GPS data
                print(f"Latitude: {lat}, Longitude: {lon}")
                update_map(lat, lon)
            else:
                gps_failure_count += 1
                print("Waiting for GPS data...")
                if gps_failure_count > 10:  # Notify user after multiple failures
                    print("GPS is still not responding. Ensure the GPS module is functional.")
                    gps_failure_count = 0  # Reset counter to avoid flooding messages

            # Robot action: Trot
            my_dog.do_action('trot', step_count=10, speed=95)
            sleep(1)

    except KeyboardInterrupt:
        print("\nExiting PiDog GPS program.")
    finally:
        my_dog.close()

if __name__ == "__main__":
    main()
