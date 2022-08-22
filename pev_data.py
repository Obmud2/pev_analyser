# Module for extracting the Pilot Event Start Markers (PEVs) from IGC traces
# Jon Pring
# 01-08-2022 JWGC Tabor, CZ

import os
import re
import datetime
import pandas as pd

UTC_OFFSET = 2

class Position:
    def __init__(self, fix_time, lat_long, press_alt, gps_alt):
        conv_m_to_ft = 3.2808
        if re.match('[0-9]{7}[NS][0-9]{8}[EW]', lat_long):
            self.lat = int(lat_long[0:7]) / 100000
            self.lat *= 1 if lat_long[7]=="N" else -1
            self.long = int(lat_long[8:16]) / 100000
            self.lat *= 1 if lat_long[16]=="E" else -1
            self.press_alt = round(int(press_alt) * conv_m_to_ft)
            self.gps_alt = round(int(gps_alt) * conv_m_to_ft)
        else:
            raise Exception(f"Coordinate format error: {lat_long}")

        if isinstance(fix_time, datetime.datetime):
            self.time = fix_time
        else:
            raise Exception(f"Fix time format error: {fix_time}")

    def update_date(self, new_date):
        self.time = datetime.combine(self.time.time() ,new_date)
    
    def get_position_str(self):
        lat_str = "{:.5f}".format(abs(self.lat))
        lat_str += "N" if self.lat>=0 else "S"
        long_str = "{:.5f}".format(abs(self.long))
        long_str += "E" if self.long>=0 else "W"
        return f"{self.time.strftime('%X')} UTC+{UTC_OFFSET} {lat_str} {long_str} Press:{self.press_alt}ft GPS:{self.gps_alt}ft"

def get_csv_data(full_path):
    df = pd.read_csv(full_path)
    df = df.set_index('comp_no')
    return df

def get_time(time_str, utc=0):
    if re.match("[0-9]{6}", time_str):
        return datetime.time(
            hour   = int(time_str[0:2]) + utc,
            minute = int(time_str[2:4]),
            second = int(time_str[4:6]))
    else:
        print(f"Time parse error: {time_str}")

def parse_row(row_str, file_date=datetime.date(1970,1,1)):
    if row_str.startswith("H"):
        if row_str[1:5] == "FDTE":
            date_str = re.search("[0-9]{6}", row_str).group()
            return datetime.datetime.strptime(date_str, "%d%m%y").date()
    elif row_str.startswith("E"):
        if row_str[7:10]=="PEV":
            return datetime.datetime.combine(file_date, get_time(row_str[1:7], UTC_OFFSET))
    elif row_str.startswith("B"):
        fix_time = datetime.datetime.combine(file_date, get_time(row_str[1:7], UTC_OFFSET))
        return Position(fix_time,row_str[7:24],row_str[25:30],row_str[30:35])
    print(f"Type not parsed: {row_str}")

def get_pevs(path):
    igc_files = os.listdir(path=path)
    pevs = []
    for igc_file in igc_files:
        if igc_file.endswith('.csv'):
            competitor_data = get_csv_data(f"{path}/{igc_file}")
            break
    for igc_file in igc_files:
        if not igc_file.endswith('.igc'):
            continue
        comp_no = igc_file.split(".")[0]
        with open(f"{path}/{igc_file}", mode='r') as file:
            n_lines = 0
            check_next_line = 0
            file_date = 0
            temp_start_time = competitor_data.loc[comp_no]['start_time'].replace(':','')
            if temp_start_time:
                temp_start_time = get_time(temp_start_time)
            pevs.append([comp_no, None, []]) #Comp no, start datetime, list of PEVs
            try:
                for line in file:
                    if line.startswith("HFDTE"): # Date line
                        file_date = parse_row(line)
                        start_time_obj = datetime.datetime.combine(file_date, temp_start_time)
                        pevs[-1][1] = start_time_obj
                    elif line.startswith("E") and line[7:10]=="PEV": # PEV marker
                        pev_time = parse_row(line, file_date)
                        check_next_line = 1
                    elif check_next_line and line.startswith("B"): # Next B fix after PEV
                        pos = parse_row(line, file_date)
                        time_delta_to_start = start_time_obj - pos.time
                        time_delta_str = "After start" if time_delta_to_start < datetime.timedelta(0) else f"-{time_delta_to_start}"
                        pevs[-1][2].append(pos)
                        check_next_line = 0
                    n_lines += 1
            except UnicodeDecodeError:
                #print(f"Unicode error: Line {n_lines}, Comp_No: {comp_no}")
                pass
    sorted_pevs = sorted(pevs, key=lambda x:x[1])
    return sorted_pevs

def print_pevs(pevs):
    for pilot in pevs:
        comp_no = pilot[0]
        start_time = pilot[1]
        pilot_pevs = pilot[2]
        print(f"Comp No: {comp_no}\nStart Time: {start_time.strftime('%X')}")
        for pev in pilot_pevs:
            pev_time = pev.time
            time_delta = start_time - pev_time
            time_delta_str = "After start" if time_delta < datetime.timedelta(0) else f"-{time_delta}"
            print(f"PEV: {pev_time.strftime('%X')} ({time_delta_str})")
        print("---------------------------------")
