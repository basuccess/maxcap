# Author: Tony Houweling
# Company: Tarana Wireless, Inc.
# Rights to use and modify this code are granted to authorized personnel.
# GitHub Repository: https://github.com/basuccess/maxcap

import os
import pandas as pd
import numpy as np
import glob
import argparse
import sys
import logging  # Added import for logging

# Define constants
FILEPATH = '/Users/thouweling/Downloads'
PATTERN = 's*-*.csv'
LOGGINGLEVEL = 'DEBUG'    # Set to DEBUG to capture all levels of logs

# Configure logging
logging.basicConfig(
    filename='maxcap1.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOGGINGLEVEL)  
)

# Define mandatory fields and output field names for aggregation.
MANDATORY_FIELDS = ['Time', 'DL Capacity', 'RF Utilization']
OUTPUT_FIELDS = [
    'Device Serial',
    'Time',
    'RF Utilization',
    'DL Tonnage GB',
    'UL Tonnage GB',
    'DL Capacity',
    'UL Capacity',  # Changed from 'UL Rate' to 'UL Capacity'
    'DL Rate',  # Added DL Rate
    'UL Rate',  # Added UL Rate
    'DL Peak Rate',
    'UL Peak Rate',
    'Active Connections',
    'Bandwidth, Carrier 0',
    'Bandwidth, Carrier 1',
    'Bandwidth, Carrier 2',
    'Bandwidth, Carrier 3'
]

def find_files(pattern):
    """Find all files matching the given pattern in the specified directory."""
    return glob.glob(os.path.join(FILEPATH, pattern))

def process_file(filepath, frequency):
    """Read and process each file."""
    device_serial = os.path.basename(filepath).split('-')[0]
    
    try:
        logging.info(f"Processing file: {filepath}")  # Added logging

        # Read CSV file into DataFrame.
        df = pd.read_csv(filepath)
        logging.debug(f"Read {len(df)} rows from {filepath}")  # Added logging
        
        # Strip whitespace from column names to prevent mismatches.
        df.columns = df.columns.str.strip()
        
        for i in range(4):
            if f"Bandwidth, Carrier {i}" in df.columns:
                df[f"Bandwidth, Carrier {i}"] = pd.to_numeric(df[f"Bandwidth, Carrier {i}"], errors='coerce')
                logging.debug(f"Converted 'Bandwidth, Carrier {i}' to numeric")  # Added logging
            else:
                df[f"Bandwidth, Carrier {i}"] = np.nan
                logging.warning(f"'Bandwidth, Carrier {i}' missing in {filepath}, initialized with NaN")  # Added logging
        
        # Check for mandatory fields.
        if not all(field in df.columns for field in MANDATORY_FIELDS):
            logging.error(f"Skipped file {filepath}: Missing mandatory fields")  # Replaced print with logging
            logging.error(f"Expected fields: {MANDATORY_FIELDS}")
            logging.error(f"Found fields: {list(df.columns)}")
            return None
        
        # **New Checks Start**
        # If 'DL Capacity' is all NaN, skip the file
        if df['DL Capacity'].isna().all():
            logging.error(f"Skipped file {filepath}: All 'DL Capacity' values are NaN")
            return None
        
        # If 'RF Utilization' is all NaN, skip the file
        if df['RF Utilization'].isna().all():
            logging.error(f"Skipped file {filepath}: All 'RF Utilization' values are NaN")
            return None
        # **New Checks End**
        
        # Convert time column to datetime format; errors='coerce' will turn invalid entries into NaT (Not a Time).
        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
        
        # Drop rows with NaT in the Time column.
        df.dropna(subset=['Time'], inplace=True)
        
        # Create an hourly period bin based on Time column.
        df.set_index('Time', inplace=True)
        ## Resampling data with .mean() & .max() as required by specifications per hour bin 
        
        # Build aggregation dictionary dynamically based on existing columns
        aggr_dict = {
            "DL Capacity": "mean",
            "RF Utilization": "mean",
        }
        
        # Define optional aggregation fields and their functions
        optional_agg = {
            "UL Capacity": "mean",  # Changed from 'UL Rate'
            "DL Rate": "mean",  # Added DL Rate
            "UL Rate": "mean",  # Added UL Rate
            "Active Connections": "max",
            "DL Peak Rate": "max",
            "UL Peak Rate": "max"
        }
        
        for field, func in optional_agg.items():
            if field in df.columns:
                aggr_dict[field] = func
        
        # Add aggregation for existing Bandwidth carriers
        for i in range(4):
            carrier = f"Bandwidth, Carrier {i}"
            if carrier in df.columns:
                aggr_dict[carrier] = "max"
        
        aggregated_df = df.resample(frequency).agg(aggr_dict)
        logging.debug(f"Aggregated data with frequency '{frequency}'")  # Added logging
        
        # Ensure all Bandwidth carriers are present in the aggregated DataFrame
        for i in range(4):
            carrier = f"Bandwidth, Carrier {i}"
            if carrier not in aggregated_df.columns:
                aggregated_df[carrier] = np.nan
                logging.warning(f"'{carrier}' missing after aggregation, initialized with NaN")  # Added logging
        
        ### Fill missing values with NaN; aggregate method already takes care of it via means/maxes 
        aggregated_df.fillna(np.nan, inplace=True) 
        
        ### Add Device Serial information as a new column 
        aggregated_df.insert(0, "Device Serial", device_serial) 
        
        ### Reset index so we can output time back out nicely later   
        aggregated_df.reset_index(inplace=True)

        #### Format “Time” back to desired string format: %m/%d/%y %H     
        aggregated_df["Time"] = aggregated_df["Time"].dt.strftime("%m/%d/%y %H") 

        # After formatting "Time", convert "Bandwidth, Carrier" fields to integers
        for i in range(4):
            carrier = f"Bandwidth, Carrier {i}"
            aggregated_df[carrier] = aggregated_df[carrier].fillna(0).astype(int)
            logging.debug(f"Converted '{carrier}' to integers")  # Added logging
        
        # Convert "Active Connections" to integer if it exists
        if "Active Connections" in aggregated_df.columns:
            aggregated_df["Active Connections"] = aggregated_df["Active Connections"].fillna(0).astype(int)
            logging.debug("Converted 'Active Connections' to integers")  # Added logging

        # Round floating columns to 3 decimals
        floating_columns = ["DL Capacity", "UL Capacity", "RF Utilization", "DL Rate", "UL Rate", "DL Peak Rate", "UL Peak Rate"]  # Changed from 'UL Rate'
        existing_floating = [col for col in floating_columns if col in aggregated_df.columns]
        aggregated_df[existing_floating] = aggregated_df[existing_floating].round(3)
        logging.debug("Rounded floating columns to 3 decimals")  # Added logging

        # Calculate "DL Tonnage GB" and "UL Tonnage GB"
        if "DL Capacity" in aggregated_df.columns:
            aggregated_df["DL Tonnage GB"] = (aggregated_df["DL Capacity"] * 3600) / 8000
            aggregated_df["DL Tonnage GB"] = aggregated_df["DL Tonnage GB"].round(3)
            logging.debug("Calculated 'DL Tonnage GB'")  # Added logging
        else:
            aggregated_df["DL Tonnage GB"] = np.nan
            logging.warning("'DL Capacity' missing, 'DL Tonnage GB' set to NaN")  # Added logging

        if "UL Capacity" in aggregated_df.columns:
            aggregated_df["UL Tonnage GB"] = (aggregated_df["UL Capacity"] * 3600) / 8000  # Changed from 'UL Rate' to 'UL Capacity'
            aggregated_df["UL Tonnage GB"] = aggregated_df["UL Tonnage GB"].round(3)
            logging.debug("Calculated 'UL Tonnage GB'")
        else:
            aggregated_df["UL Tonnage GB"] = np.nan
            logging.warning("'UL Capacity' missing, 'UL Tonnage GB' set to NaN")  # Updated logging message

        logging.info(f"Finished processing file: {filepath}")  # Added logging
        return aggregated_df

    except Exception as e:
        logging.error(f"Error processing file {filepath}: {e}")
        return None

def main(frequency, busiest, output_filename=None):  
    logging.info("Script run started.")  # Added logging
    all_results=[] 

    files= find_files(PATTERN) 
    logging.info(f"Found {len(files)} files to process")  # Added logging

    for filepath in files: 
        result_df= process_file(filepath, frequency)  
        if result_df is not None:  
            # **New Check Start**
            if busiest:
                try:
                    # Identify the busiest hour based on DL Tonnage GB
                    busiest_hour = result_df.loc[result_df['DL Tonnage GB'].idxmax()]
                    
                    # Check if 'DL Capacity' or 'RF Utilization' is NaN in busiest hour
                    if pd.isna(busiest_hour['DL Capacity']) or pd.isna(busiest_hour['RF Utilization']):
                        logging.warning(f"Skipped file {filepath}: Busiest hour has NaN in 'DL Capacity' or 'RF Utilization'")
                        continue  # Skip adding this file's results
                except Exception as e:
                    logging.error(f"Error identifying busiest hour in file {filepath}: {str(e)}")
                    continue  # Skip adding this file's results
            # **New Check End**
            
            all_results.append(result_df)
            logging.info(f"Appended results from {filepath}")  # Added logging

    if all_results:  
        combined_result = pd.concat(all_results).reset_index(drop=True)  
        logging.debug("Combined all aggregated results")  # Added logging

        # Exclude rows where "DL Capacity" or "RF Utilization" is NaN
        combined_result.dropna(subset=['DL Capacity', 'RF Utilization'], inplace=True)
        logging.debug("Dropped rows with NaN in 'DL Capacity' or 'RF Utilization'")

        # Convert 0 to NaN for "Bandwidth, Carrier" fields before printing the output
        for i in range(4):
            carrier = f"Bandwidth, Carrier {i}"
            combined_result[carrier] = combined_result[carrier].replace(0, np.nan)
            combined_result[carrier] = combined_result[carrier].astype('Int64')
            logging.debug(f"Converted 0 to NaN for '{carrier}' and ensured non-0 values remain integers")  # Added logging

        # Convert 0 to NaN for "Active Connections" field before printing the output
        if "Active Connections" in combined_result.columns:
            combined_result["Active Connections"] = combined_result["Active Connections"].replace(0, np.nan)
            combined_result["Active Connections"] = combined_result["Active Connections"].astype('Int64')
            logging.debug("Converted 0 to NaN for 'Active Connections' and ensured non-0 values remain integers")  # Added logging

        if busiest:
            # Convert "Time" back to datetime for resampling
            combined_result['Time'] = pd.to_datetime(combined_result['Time'], format='%m/%d/%y %H')
            logging.debug("Converted 'Time' to datetime for resampling")
            
            # Define frequency mapping
            period_map = {
                'day': 'D',
                'week': 'W',
                'month': 'MS',  # Changed from 'M' to 'MS' to avoid FutureWarning
                'year': 'YE'    # Changed from 'Y' to 'YE' to avoid FutureWarning
            }

            # Group by both 'Device Serial' and the specified period, then find idxmax
            idx = combined_result.groupby(['Device Serial', pd.Grouper(key='Time', freq=period_map[busiest])])['DL Tonnage GB'].idxmax()
            logging.debug("Grouped data and identified indices for busiest periods")
            
            # Check if idx is empty
            if (idx.empty):
                logging.warning(f"No busiest hours found for period: {busiest.capitalize()}")
                print(f"\nNo busiest hours found for period: {busiest.capitalize()}")
            else:
                # Select the busiest hours based on the indices
                busiest_hours = combined_result.loc[idx].copy()
                
                # Check for NaN in 'DL Capacity' or 'RF Utilization' in busiest hours
                if busiest_hours[['DL Capacity', 'RF Utilization']].isna().any().any():
                    logging.warning(f"Skipped output for busiest hours due to NaN in 'DL Capacity' or 'RF Utilization'")
                else:
                    # Format "Time" back to desired string format: %m/%d/%y %H     
                    busiest_hours["Time"] = busiest_hours["Time"].dt.strftime("%m/%d/%y %H")
                    
                    # Print all fields for the busiest hours
                    print(busiest_hours[OUTPUT_FIELDS].to_csv(index=False))
                    logging.info(f"Printed busiest hours for period: {busiest.capitalize()}")
        else:
            # Output aggregated data
            combined_result[OUTPUT_FIELDS].to_csv(output_filename or sys.stdout, index=False)
            logging.info(f"Output aggregated data to {'stdout' if not output_filename else output_filename}")  # Added logging
    else:
        logging.warning("No results to combine and output")

def map_busiest(value):
    """Map abbreviations to full forms for the busiest argument."""
    mapping = {'d': 'day', 'w': 'week', 'm': 'month', 'y': 'year'}
    return mapping.get(value.lower(), value.lower())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process CSV files and aggregate data.')
    
    parser.add_argument('-o', '--outfile', type=str,
                        help='Optional output filename (default is stdout)')
    
    # Add resampling frequency argument
    parser.add_argument('-f', '--frequency', type=str, nargs='?', const='h', default='h',
                        help='Resampling frequency (e.g., h for hourly, d for daily)')
    
    # Add busiest hour argument with abbreviations
    parser.add_argument('-b', '--busiest', type=map_busiest,
                        choices=['day', 'week', 'month', 'year'],
                        nargs='?', const='day', default=None,
                        help='Output busiest hour based on DL Tonnage GB for specified period (d=day, w=week, m=month, y=year)')
    
    # Add usage argument
    parser.add_argument('-u', '--usage', action='store_true',
                        help='Display usage information')

    args = parser.parse_args()
    
    if args.usage:
        usage_text = """
Usage Information:

This script processes exported traffic performance metrics from CSV files that follow a specific naming convention.

Mandatory fields required in CSV Files (columns):
- Time (must be of datetime format)
- RF Utilization (Radio Frequency utilization)
- DL Capacity (Downlink capacity)

Optional fields (if available):
- UL Capacity (Uplink capacity)
- Active Connections (Number of active connections at peak times)
- DL Peak Rate (Peak downlink rate during busy hour)
- UL Peak Rate (Peak uplink rate during busy hour)
- Bandwidth, Carrier 0-3 (Bandwidth for each carrier)

Command-Line Options:
- -o, --outfile <filename>:
    Specify the output CSV file to save the aggregated results. If not provided, the output will be displayed on the console.
    
- -f, --frequency <freq>:
    Define the resampling frequency for aggregating data.
    - 'h' : Hourly (default)
    - 'd' : Daily
    - 'w' : Weekly
    - 'm' : Monthly
    - 'y' : Yearly

- -b, --busiest <period>:
    Output the busiest hour based on DL Tonnage GB for the specified period.
    - 'd' : Day (default)
    - 'w' : Week
    - 'm' : Month
    - 'y' : Year

- -h, --help:
    Display the help message and exit.
    
- -u, --usage:
    Display this usage information and exit.

Example Command Line Usage:

1. To display output on console without saving to a file:
   python your_script.py 

2. To save the output to a specific CSV file named results.csv:
   python your_script.py -o results.csv 

3. To aggregate data daily and find the busiest days:
   python your_script.py -f d -b d

4. To aggregate data weekly and save the results to output_weekly.csv:
   python your_script.py -f w -o output_weekly.csv

Note that only files matching the pattern BNserial#-*.csv will be processed.

GitHub Repository: https://github.com/basuccess/maxcap
"""
        print(usage_text)
        sys.exit()
    
    main(args.frequency, args.busiest, args.outfile)