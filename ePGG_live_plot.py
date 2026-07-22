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
duration = 60                    # seconds
sample_interval_s = 200e-6       # matches Arduino's SAMPLE_INTERVAL
plot_window_sec = 5              # how many seconds of data to show on screen at once

# ---------- Setup serial ----------
ser = serial.Serial(port, baud, timeout=0)  # timeout=0 = non-blocking reads
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
max_points = int(plot_window_sec / sample_interval_s)
times = deque(maxlen=max_points)
voltages = deque(maxlen=max_points)

sample_count = 0
start_wall_time = time.time()
leftover = ""  # holds partial line data between reads

def update():
    global sample_count, leftover

    if time.time() - start_wall_time > duration:
        finish()
        return

    # read everything currently available in the buffer
    waiting = ser.in_waiting
    if waiting:
        raw_bytes = ser.read(waiting).decode(errors="ignore")
        leftover += raw_bytes
        lines = leftover.split("\n")
        leftover = lines[-1]  # keep incomplete last line for next time
        for line in lines[:-1]:
            line = line.strip()
            if not line:
                continue
            try:
                voltage = float(line)
                time_s = sample_count * sample_interval_s
                writer.writerow([time_s, voltage])
                sample_count += 1
                times.append(time_s)
                voltages.append(voltage)
            except ValueError:
                continue

    if times:
        curve.setData(list(times), list(voltages))

def finish():
    timer.stop()
    print("Done recording.")
    csv_file.close()
    ser.close()

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(33)  # update ~30 times per second

print("Recording...")
sys.exit(app.exec_())
