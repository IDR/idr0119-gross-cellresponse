import re
import subprocess
from ome_model.experimental import Plate, Image, create_companion

"""
Creates companions for the plates located in 20221121-Globus directory.
"""

w = 1408
h = 1040
size_c = 3
size_z = 1
pix_type = "uint16"
order = "XYCZT"
channels = "RGP"
rows = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

file_list = '119_files.txt'

# 2101001/A1/field_1/2101001_G_A1_1_04d00h00m.tif
pat = re.compile(r"(?P<plate_name>\w+)\/(?P<well_row>.)(?P<well_col>.)\/field_(?P<field>\d)\/[a-zA-Z0-9-]+_(?P<channel_name>\w+)_.+_.+(?P<day>\d{2})d(?P<hour>\d{2})h(?P<min>\d{2})m.tif$")

file_map = {}
# This is just a list of all the tiff files
with open(file_list, 'r') as read:
    for line in read.readlines():
        if "Analysis" not in line:
            line = line.strip()
            if not line:
                continue
            if pat.match(line):
                m = pat.match(line).groupdict()
                if m['plate_name'] not in file_map:
                    file_map[m['plate_name']] = []
                file_map[m['plate_name']].append(line)


for plate_name, files in file_map.items():
    # Get number of rows and columns
    n_rows = set()
    n_cols = set()
    n_fields = set()
    times = []
    for file in files:
        m = pat.match(file).groupdict()
        n_rows.add(m['well_row'])
        n_cols.add(int(m['well_col']))
        n_fields.add(int(m['field']))
        time = int(m['day']) * 24 * 60 + int(m['hour']) * 60 + int(m['min'])
        if time not in times:
            times.append(time)
    n_rows = len(n_rows)
    n_cols = len(n_cols)
    n_fields = len(n_fields)
    n_times = len(times)
    times.sort()

    images = {}
    for file in files:
        m = pat.match(file).groupdict()
        key = f"{m['well_row']}|{m['well_col']}|{m['field']}"
        if not key in images:
            images[key] = Image(key, w, h, size_z, size_c, n_times, order=order, type=pix_type)
            images[key].add_channel(samplesPerPixel=1)
            images[key].add_channel(samplesPerPixel=1)
            images[key].add_channel(samplesPerPixel=1)
        c_index = channels.index(m['channel_name'])
        time = int(m['day']) * 24 * 60 + int(m['hour']) * 60 + int(m['min'])
        t_index = times.index(time)
        images[key].add_plane(c=c_index, z=0, t=t_index)
        images[key].add_tiff(file, c=c_index, z=0, t=t_index, planeCount=1)

    # assemble plate
    plate = Plate(plate_name, n_rows, n_cols)
    wells = {}
    index = 0
    for well_pos, image in images.items():
        row = rows.index(well_pos.split("|")[0])
        col = int(well_pos.split("|")[1])-1
        field = int(well_pos.split("|")[2])-1
        key = f"{row}|{col}"
        if not key in wells:
            wells[key] = plate.add_well(row, col)
        wells[key].add_wellsample(field, image)

    # write companion file
    companion_file = f"{plate_name}.companion.ome"
    create_companion(plates=[plate], out=companion_file)


    # Indent XML for readability
    proc = subprocess.Popen(
        ['xmllint', '--format', '-o', companion_file, companion_file],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE)
    (output, error_output) = proc.communicate()