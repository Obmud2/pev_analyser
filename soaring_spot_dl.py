# Import Soaring Spot data

from genericpath import exists
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import re
import os
import urllib.request
import csv

class SoaringSpotDL():
    soaringspot_url = "https://www.soaringspot.com"

    def __init__(self, comp_url):
        self.comp_url = comp_url

    def __get_days_flown(self):
        """Retrieve competition classes and task days from soaring spot"""
        page = requests.get(self.soaringspot_url + self.comp_url + "/results")
        soup = BeautifulSoup(page.content, 'html.parser')
        days_flown = []
        tables = soup.find_all("table", class_="result-overview")

        for table in tables:
            comp_class = table.find("th").get_text().strip()
            for row in table.find_all("tr"):
                day = row.find_all("td")
                if len(day) > 3:
                    task_date = datetime.strptime(day[0].get_text(), "%d/%m/%Y")
                    task_results_url = day[3].a['href']
                    days_flown.append({"comp_class":comp_class,
                                        "task_date":task_date,
                                        "results_url":task_results_url})
        return days_flown

    def __select_day(self, days_flown):
        """Select day from days_flown"""
        n = 1
        print("Select Day:")
        for day in days_flown:
            print(f"{n}:\t{day['comp_class']}\t{day['task_date']}")
            n += 1
        i = int(input())
        return days_flown[i-1]

    def __get_data(self, results_url):
        """Scrape all soaring spot competitor data"""
        competitor_data = []
        page = requests.get(self.soaringspot_url + results_url)
        soup = BeautifulSoup(page.content, "html.parser")
        t = soup.find("tbody")
        rows = t.find_all("tr")
        data_headings = [
                "day_position",
                "position_delta",
                "comp_no",
                "pilot_name",
                "trace_id",
                "glider",
                "handicap",
                "start_time",
                "finish_time",
                "task_duration",
                "day_speed",
                "day_distance",
                "day_points"
        ]

        for r in rows:
            r_data = r.find_all("td")
            trace_id = re.search("[0-9]{4}-[0-9]{10}", str(r_data[2]))
            competitor_data.append([
                r_data[0].get_text().replace(".",""), #day_position
                r_data[1].get("data-value") if r_data[1].get("data-value") else 0, #position_delta
                r_data[2].get_text().strip(), #comp_no
                r_data[3].get_text().strip(), #pilot_name
                trace_id.group() if trace_id != None else None, #trace_id
                r_data[4].get_text(), #glider
                r_data[5].get_text(), #handicap
                r_data[6].get_text(), #start_time
                r_data[7].get_text(), #finish_time
                r_data[8].get_text(), #task_duration
                r_data[9].get_text().replace("km/h", "").strip(), #day_speed
                r_data[10].get_text().replace("km", "").strip(), #day_distance
                r_data[11].get_text().strip() #day_points
            ])
        return data_headings, competitor_data

    def __get_traces(self, day, path="default", basename="", overwrite=False):
        """Download traces from results url, option to overwrite existing traces"""
        if path=="default":
            path = f"igc/{day['comp_class']}/{day['task_date'].strftime('%Y-%m-%d')}"
        download_url = "/en_gb/download-contest-flight/"
        dt_head, competitor_data = self.__get_data(day['results_url'])

        # make dirs
        if not os.path.exists(path):
            os.makedirs(path)

        # store csv data
        with open(f"{path}/{day['comp_class'].replace(' ','')}_{day['task_date'].strftime('%Y-%m-%d')}.csv", 'w') as file:
            writer = csv.writer(file)
            writer.writerow(dt_head)
            for competitor in competitor_data:
                writer.writerow(competitor)

        # download traces
        trace_counter=1
        for competitor in competitor_data:
            comp_no = competitor[2]
            trace_id = competitor[4]
            url = f"{self.soaringspot_url}{download_url}{trace_id}?dl=1"
            file_name = f"{path}/{basename}{comp_no}.igc"
            if trace_id == None:
                print(f"No trace for {comp_no} ({trace_counter}/{len(competitor_data)})")
            elif not os.path.exists(file_name):
                print(f"Downloading trace {comp_no} ({trace_counter}/{len(competitor_data)}): {url}")
                response = urllib.request.urlretrieve(url, file_name)
            elif overwrite:
                print(f"Overwriting trace {comp_no} ({trace_counter}/{len(competitor_data)})")
                response = urllib.request.urlretrieve(url, file_name)
            else:
                print(f"Skip trace {comp_no} ({trace_counter}/{len(competitor_data)})")
            print(file_name)
            trace_counter += 1
    
    def download_traces(self, comp_class="all", task_day="all", overwrite=False, select_day=False):
        days = self.__get_days_flown()
        if select_day:
            day = self.__select_day(days)
            self.__get_traces(day, overwrite=overwrite)
        else:
            for day in days:
                if comp_class=='all' or comp_class==day['comp_class']:
                    if task_day=='all' or task_day==day['task_date']:
                        path = f"igc/{day['comp_class']}/{day['task_date'].strftime('%Y-%m-%d')}"
                        self.__get_traces(day, overwrite=overwrite)

if __name__ == "__main__":
    competition_url = "/en_gb/junior-world-gliding-championships-2022-tabor-2022"
    jwgc22 = SoaringSpotDL(competition_url)
    jwgc22.download_traces(select_day=True)