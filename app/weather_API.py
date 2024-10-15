import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import argparse
import json
import logging
from logging import Logger
import logging
from typing import List
from app.sdk.models import KernelPlancksterSourceData, BaseJobState, JobOutput, ProtocolEnum
from app.sdk.scraped_data_repository import ScrapedDataRepository,  KernelPlancksterSourceData
import time
import os
import json
import pandas as pd
from PIL import Image
from numpy import ndarray
import numpy as np
import cv2
import shutil
import hashlib
import requests



# Setup Open-Meteo API with caching and retries
def setup_openmeteo_client():
    try:
        cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)
        return openmeteo
    except Exception as e:
        print(f"Error setting up Open-Meteo client: {e}")
        return None

# Fetch weather data from Open-Meteo API
def fetch_weather_data(latitude, longitude, start_date, end_date):
    try:
        openmeteo = setup_openmeteo_client()
        if openmeteo is None:
            return None

        url = "https://archive-api.open-meteo.com/v1/archive"

        # Specify multiple hourly weather parameters
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(["rain", "snowfall", "cloud_cover", "sunshine_duration"])  # Add multiple parameters here
        }

        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]  # Assuming a single location is processed
        return response
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None

# Process weather data and convert to a pandas DataFrame
def process_weather_data(response):
    try:
        hourly = response.Hourly()

        # Extract variables with their indices
        cloud_cover = hourly.Variables(0).ValuesAsNumpy() if hourly.Variables(0) else None
        rain = hourly.Variables(1).ValuesAsNumpy() if hourly.Variables(1) else None
        snowfall = hourly.Variables(2).ValuesAsNumpy() if hourly.Variables(2) else None
        sunshine_duration = hourly.Variables(3).ValuesAsNumpy() if hourly.Variables(3) else None

        # Create a pandas DataFrame with the time data
        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            )
        }

        # Add weather variables if they are available
        if cloud_cover is not None:
            hourly_data["cloud_cover"] = cloud_cover
        if rain is not None:
            hourly_data["rain"] = rain
        if snowfall is not None:
            hourly_data["snowfall"] = snowfall
        if sunshine_duration is not None:
            hourly_data["sunshine_duration"] = sunshine_duration

        return pd.DataFrame(data=hourly_data)
    except Exception as e:
        print(f"Error processing weather data: {e}")
        return pd.DataFrame()
 
def save_data(type_entry, latitude, longitude, weather, date, file_dir):
    try:
        # Create a dictionary with the result data
        result = {
            "type": type_entry,
            "weather": weather,
            "date": date,
            "latitude": latitude,
            "longitude": longitude
        }

        # Define file path for the JSON
        json_filename = os.path.join(file_dir, 'temp_results.json')
        os.makedirs(os.path.dirname(json_filename), exist_ok=True)

        # Load existing data if the JSON file exists
        if os.path.exists(json_filename):
            existing_data = pd.read_json(json_filename, orient="index")
        else:
            # Initialize an empty DataFrame if no file exists
            existing_data = pd.DataFrame(columns=["type", "weather", "date", "latitude", "longitude"])

        # Check if the result is already in the existing DataFrame
        is_duplicate = (
            (existing_data['latitude'] == latitude) &
            (existing_data['longitude'] == longitude) &
            (existing_data['date'] == date) &
            (existing_data['weather'] == weather)
        ).any()

        # Only append if it is not a duplicate
        if not is_duplicate:
            new_row = pd.DataFrame([result])
            updated_data = pd.concat([existing_data, new_row], ignore_index=True)

            # Save the updated DataFrame back to the JSON file
            updated_data.to_json(json_filename, orient="index")
            print(f"Data saved to {json_filename}")
            return updated_data
        else:
            print(f"Duplicate entry found for {latitude}, {longitude} on {date}. Skipping...")
            return existing_data

    except Exception as e:
        print(f"Error saving results to DataFrame: {e}")
        return pd.DataFrame()  # Return empty DataFrame on failure


def weather(job_id, tracer_id, scraped_data_repository, protocol, log_level, latitude, longitude, start_date, end_date, file_dir, url):
    try:
        logger = logging.getLogger(__name__)
        logging.basicConfig(level=log_level)

        # Fetch weather data using Open-Meteo API
        response = fetch_weather_data(latitude, longitude, start_date, end_date)
        if response is None:
            logger.error("Failed to fetch weather data.")
            return []

        weather_df = process_weather_data(response)
        if weather_df.empty:
            logger.error("Weather data processing failed.")
            return []

        # Determine weather condition based on cloud cover, rain, and snowfall
        avg_cloud_cover = weather_df["cloud_cover"].mean() if "cloud_cover" in weather_df.columns else 0
        avg_rain = weather_df["rain"].mean() if "rain" in weather_df.columns else 0
        avg_snowfall = weather_df["snowfall"].mean() if "snowfall" in weather_df.columns else 0
        avg_sunshine = weather_df["sunshine_duration"].mean() if "sunshine_duration" in weather_df.columns else 0

        if avg_rain > 0:
            weather_condition = "rainy"
        elif avg_snowfall > 0:
            weather_condition = "snowy"
        elif avg_cloud_cover < 20 and avg_sunshine > 0:
            weather_condition = "sunny"
        else:
            weather_condition = "cloudy"

        # Save the result (JSON saving)
        df = save_data(
            type_entry="API",
            date=start_date,
            latitude=latitude,
            longitude=longitude,
            weather=weather_condition,
            file_dir=file_dir,
        )
        
        if df.empty:
            logger.error(f"DataFrame is empty or None. Skipping JSON save.")
            return []

        # Define a directory and save the DataFrame as JSON
        data_name = f"Webcam_{latitude}_{longitude}_{start_date}"
        json_dir = os.path.join(file_dir, 'results')  # Use a directory for results
        os.makedirs(json_dir, exist_ok=True)
        json_path = os.path.join(json_dir, f"{data_name}.json")
        
        df.to_json(json_path, orient="index")
        logger.info(f"Augmented JSON saved to: {json_path}")

        # Construct relative path for storage
        relative_path = f"Webcam/{tracer_id}/{job_id}/augmented/{data_name}.json"
        media_data = KernelPlancksterSourceData(
            name=data_name,
            protocol=protocol,
            relative_path=relative_path
        )

        # Register the JSON in the scraped_data_repository
        try:
            scraped_data_repository.register_scraped_json(
                job_id=job_id,
                source_data=media_data,
                local_file_name=json_path,  # Correct file name here
            )
        except Exception as e:
            logger.error(f"Error registering file {json_path}: {e}")

        return [media_data]

    except Exception as e:
        logger.error(f"Error in weather function: {e}")
        return []



# Main function to fetch and display weather data
def scrape(job_id,tracer_id,scraped_data_repository,log_level,latitude, longitude, start_date, end_date, file_dir, url=None) -> JobOutput:
    try:
        logger = logging.getLogger(__name__)
        logging.basicConfig(level=log_level)

        job_state = BaseJobState.CREATED
        current_data: KernelPlancksterSourceData | None = None
        last_successful_data: KernelPlancksterSourceData | None = None

        protocol = scraped_data_repository.protocol

        output_data_list: List[KernelPlancksterSourceData] = []
        if job_state:  # for typing
            # Set the job state to running
            logger.info(f"{job_id}: Starting Job")
            job_state = BaseJobState.RUNNING
            #job.touch()

            start_time = time.time()  # Record start time for response time measurement
            try:
                logger.info(f"starting with weather API")
                output_data_list = weather(job_id=job_id,tracer_id=tracer_id,scraped_data_repository=scraped_data_repository,protocol=protocol,log_level=log_level,latitude=latitude,longitude=longitude,start_date=start_date,end_date=end_date,file_dir=file_dir, url=url)
                print(f"job_id = {job_id} and tracer_id = {tracer_id}")
                # Calculate response time
                response_time = time.time() - start_time
                response_data = {
                    "message": f"Pipeline processing completed",
                    "response_time": f"{response_time:.2f} seconds"
                }
        
            except Exception as e:
                logger.error(f"Error in processing pipeline: {e}")
                #raise HTTPException(status_code=500, detail="Internal server error occurred.")
                job_state = BaseJobState.FAILED
                logger.error(
                    f"{job_id}: Unable to scrape data. Error:\n{error}\nJob with tracer_id {tracer_id} failed.\nLast successful data: {last_successful_data}\nCurrent data: \"{current_data}\", job_state: \"{job_state}\""
                )


                

            job_state = BaseJobState.FINISHED
            #job.touch()
            logger.info(f"{job_id}: Job finished")
            try:
                shutil.rmtree(file_dir)
                print("deleted tmp directory, exiting")
            except Exception as e:
                logger.warning(f"Could not delete tmp directory,due to error: '{e}'")
            return JobOutput(
                job_state=job_state,
                tracer_id=tracer_id,
                source_data_list=output_data_list,
            )


    except Exception as error:
        logger.error(f"{job_id}: Unable to scrape data. Job with tracer_id {tracer_id} failed. Error:\n{error}")
        job_state = BaseJobState.FAILED
        try:
            logger.warning("deleting tmp directory")
            shutil.rmtree(file_dir)
        except Exception as e:
            logger.warning("Could not delete tmp directory, exiting")