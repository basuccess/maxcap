# MaxCap Project

## Overview

The MaxCap Project is a Python-based tool designed to process and aggregate traffic performance metrics from CSV files. It scans a specified directory for CSV files that follow a specific naming convention and aggregates the data based on user-defined resampling frequencies. The tool also provides an option to identify the busiest hour based on Downlink (DL) Tonnage GB for specified periods.

## Features

- Processes CSV files with mandatory and optional fields.
- Aggregates data based on user-defined resampling frequencies (hourly, daily, weekly, monthly, yearly).
- Identifies the busiest hour based on DL Tonnage GB for specified periods.
- Outputs aggregated data to a specified CSV file or displays it on the console.
- Logs detailed information about the processing steps and any issues encountered.

## Requirements

- Python 3.x
- pandas
- numpy
- argparse
- logging

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/basuccess/maxcap-project.git
    ```
2. Navigate to the project directory:
    ```sh
    cd maxcap-project
    ```
3. Install the required Python packages:
    ```sh
    pip install -r /path/to/requirements.txt
    ```

## Usage

### Command-Line Options

- `-o, --outfile <filename>`: Specify the output CSV file to save the aggregated results. If not provided, the output will be displayed on the console.
- `-f, --frequency <freq>`: Define the resampling frequency for aggregating data. Options are:
  - `h`: Hourly (default)
  - `d`: Daily
  - `w`: Weekly
  - `m`: Monthly
  - `y`: Yearly
- `-b, --busiest <period>`: Output the busiest hour based on DL Tonnage GB for the specified period. Options are:
  - `d`: Day (default)
  - `w`: Week
  - `m`: Month
  - `y`: Year
- `-d, --directory <directory>`: Specify the directory to scan for CSV files (default is current directory).
- `-u, --usage`: Display usage information and exit.

### Example Commands

1. Display output on console without saving to a file:
    ```sh
    python src/maxcap1.py
    ```
2. Save the output to a specific CSV file named `results.csv`:
    ```sh
    python src/maxcap1.py -o results.csv
    ```
3. Aggregate data daily and find the busiest days:
    ```sh
    python src/maxcap1.py -f d -b d
    ```
4. Aggregate data weekly and save the results to `output_weekly.csv`:
    ```sh
    python src/maxcap1.py -f w -o output_weekly.csv
    ```
5. Specify a different directory to scan for CSV files:
    ```sh
    python src/maxcap1.py -d /path/to/directory
    ```

## CSV File Requirements

### Mandatory Fields

- `Time` (must be of datetime format)
- `RF Utilization` (Radio Frequency utilization)
- `DL Capacity` (Downlink capacity)

### Optional Fields

- `UL Capacity` (Uplink capacity)
- `Active Connections` (Number of active connections at peak times)
- `DL Peak Rate` (Peak downlink rate during busy hour)
- `UL Peak Rate` (Peak uplink rate during busy hour)
- `Bandwidth, Carrier 0-3` (Bandwidth for each carrier)

## Logging

The script logs detailed information about the processing steps and any issues encountered. The log file is named `maxcap1.log` and is created in the current directory.

## License

Rights to use and modify this code are granted to authorized personnel.

## Author

Tony Houweling

## Company

Tarana Wireless, Inc.

## GitHub Repository

[https://github.com/basuccess/maxcap-project.git](https://github.com/basuccess/maxcap-project.git)
