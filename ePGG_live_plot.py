import sys
import serial
import csv
import time
from collections import deque
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

# ---------- Settings ----------
port = "COM7"
baud = 1000000
filename = "Will_pgg_data.csv"

duration = 360                   # Total recording time (seconds)
sample_interval_s = 200e-6       # Arduino sample interval
plot_window_sec = 20             # Show only most recent 20 seconds


# ---------- Setup serial ----------
ser = serial.Serial(port, baud, timeout=0)  # Non-blocking reads
time.sleep(2)
ser.reset_input_buffer()


# ---------- Setup CSV ----------
csv_file = open(filename, mode="w", newline="")
writer = csv.writer(csv_file)
writer.writerow(["time_s", "voltage_V"])


# ---------- Setup plot window ----------
app = QtWidgets.QApplication(sys.argv)

win = pg.GraphicsLayoutWidget(title="Live PGG Data")
win.resize(900, 500)

plot = win.addPlot(title="Live PGG Voltage")

plot.setLabel("bottom", "Time", units="s")
plot.setLabel("left", "Voltage", units="V")

curve = plot.plot(pen="y")

win.show()


# ---------- Data buffers ----------
# Only keep enough points for the visible 20-second window
max_points = int(plot_window_sec / sample_interval_s)

times = deque(maxlen=max_points)
voltages = deque(maxlen=max_points)


# ---------- Recording variables ----------
sample_count = 0
start_wall_time = time.time()
leftover = ""


# ---------- Update function ----------
def update():
    global sample_count, leftover

    # Stop after the requested recording duration
    if time.time() - start_wall_time > duration:
        finish()
        return

    # Check for incoming serial data
    waiting = ser.in_waiting

    if waiting:
        raw_bytes = ser.read(waiting).decode(errors="ignore")

        leftover += raw_bytes

        lines = leftover.split("\n")

        # Save incomplete line for the next serial read
        leftover = lines[-1]

        # Process complete lines
        for line in lines[:-1]:

            line = line.strip()

            if not line:
                continue

            try:
                # Convert Arduino reading to voltage
                voltage = float(line)

                # Cap voltage at 3.5 V
                if voltage > 3.5:
                    voltage = 3.5

                # Use actual elapsed time
                time_s = time.time() - start_wall_time

                # Save EVERY measurement to CSV
                writer.writerow([time_s, voltage])

                sample_count += 1

                # Add measurement to graph buffer
                times.append(time_s)
                voltages.append(voltage)

            except ValueError:
                # Ignore malformed serial lines
                continue


    # ---------- Update graph ----------
    if times:

        curve.setData(
            list(times),
            list(voltages)
        )

        current_time = times[-1]

        # Sliding 20-second x-axis
        if current_time < plot_window_sec:

            # During the first 20 seconds,
            # gradually expand from 0 to 20 seconds
            plot.setXRange(
                0,
                plot_window_sec,
                padding=0
            )

        else:

            # After 20 seconds, slide the window forward
            plot.setXRange(
                current_time - plot_window_sec,
                current_time,
                padding=0
            )

        # Automatically adjust voltage axis
        plot.enableAutoRange(axis="y")


# ---------- Finish recording ----------
def finish():

    timer.stop()

    print("Done recording.")

    csv_file.close()
    ser.close()


# ---------- Start timer ----------
timer = QtCore.QTimer()

timer.timeout.connect(update)

# Update graph approximately 30 times per second
timer.start(33)


# ---------- Start recording ----------
print("Recording...")

sys.exit(app.exec_())
