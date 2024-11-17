from datetime import datetime,timedelta
from app.sdk.models import KernelPlancksterSourceData, BaseJobState, JobOutput
from app.sdk.scraped_data_repository import KernelPlancksterSourceData, ScrapedDataRepository
import time
import numpy as np
from typing import List
import requests
from PIL import Image
from io import BytesIO
import logging
import time
import os
import shutil
from PIL import Image
import re
import json


# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_images_from_url(url: str, date: datetime) -> Image.Image | None:
    
    try:
        split_url = url.split('/')
        webcam_id = split_url[3]  # NOTE: Might as well pass a webcam_id to the function directly
        url_template = "https://storage.roundshot.com/{webcam_id}/{year}-{month}-{day}/{hour}-{minute}-00/{year}-{month}-{day}-{hour}-{minute}-00_half.jpg"
        
        url = url_template.format(
                webcam_id=webcam_id,
                year=date.year,
                month=f"{date.month:02}",
                day=f"{date.day:02}",
                hour=f"{date.hour:02}",
                minute=f"{date.minute:02}",
            )
        logger.info(f"Fetching image from: {url}")
            
        # Fetch the image from the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
            
        # Convert the response content to a PIL Image
        image = Image.open(BytesIO(response.content))
        
        return image
    
    except Exception as e:
        logger.warning(f"Unable to fetch image from '{url}'. Error: {e}")
        return None


def save_image(image, path, factor=1.0, clip_range=(0, 1)):
    """Save the image to the given path."""
    np_image = np.array(image) * factor
    np_image = np.clip(np_image, clip_range[0], clip_range[1])
    np_image = (np_image * 255).astype(np.uint8)
    Image.fromarray(np_image).save(path)


def save_report(report_dict, file_path):
    try:
        with open(file_path, 'w') as json_file:
            json.dump(report_dict, json_file, indent=4)  # indent for pretty-printing
        print(f"Report saved to {file_path}")
    except Exception as e:
        print(f"Error saving report: {e}")

# Updated scrape_URL function
def scrape_URL(case_study_name: str, job_id: int, tracer_id: str, scraped_data_repository: ScrapedDataRepository, log_level: str, latitude, longitude, start_date: datetime, end_date: datetime, file_dir: str, url: str, interval: int) -> JobOutput:

    job_state = BaseJobState.CREATED

    start_time = time.time()

    try:
        logger = logging.getLogger(__name__)
        logging.basicConfig(level=log_level)

        protocol = scraped_data_repository.protocol

        output_data_list: List[KernelPlancksterSourceData] = []

        logger.info(f"{job_id}: Starting Job")

        job_state = BaseJobState.RUNNING

        logger.info(f"starting with webcam URL")
        image_dir = os.path.join(file_dir, "images")
        os.makedirs(image_dir, exist_ok=True)
        current_date = start_date
        report_dict = {}
        interval = timedelta(minutes=interval)# if start_date == datetime.now() else timedelta(days=1)
        #iteration=0
        logger.info(f"Data scraping Interval set at: {interval}")

        while (current_date <= end_date):
            try:
                image = fetch_images_from_url(url=url, date = current_date)

                if image is None:
                    current_date += interval
                    report_dict[int(current_date.timestamp())] = "No data"
                    continue  # logging is done in fetch_images_from_url

                if (current_date <= end_date) and (np.mean(image) != 0.0):  

                    # Save the image locally
                    file_extension = image.format.lower() if image.format else "png"
                    image_filename = f"URLbased_webcam.{file_extension}"
                    unix_timestamp = int(current_date.timestamp())
                    image_path = os.path.join(image_dir, "scraped", image_filename)
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    save_image(image, image_path, factor=1.5 / 255, clip_range=(0, 1))
                    logger.info(f"Scraped Image at {time.time()} and saved to: {image_path}")

                    # Register it in Kernel Planckster
                    data_name = f"webcam_{case_study_name}_{tracer_id}"

                    relative_path = f"{case_study_name}/{tracer_id}/{job_id}/{unix_timestamp}/webcam/{data_name}.{file_extension}"
                    report_dict[unix_timestamp] = {"relative_path" : relative_path}
                    logger.info(f"{report_dict}")
                    current_date += interval
                    
                    media_data = KernelPlancksterSourceData(
                        name=data_name,
                        protocol=protocol,
                        relative_path=relative_path,
                    )
                    
                    scraped_data_repository.register_scraped_photo(
                        job_id=job_id,
                        source_data=media_data,
                        local_file_name=image_path,
                    )

                    output_data_list.append(media_data)

                    time.sleep(0.1)   

            except Exception as e:
                logger.warning(f"Could not scrape data for {current_date}: {e}")
                time.sleep(0.1)   
                continue
                    

        response_time = time.time() - start_time
        logger.info(f"{job_id}: Job finished successfully. Response time: {response_time:.2f} seconds")
        
        return JobOutput(
            job_state=BaseJobState.FINISHED,
            tracer_id=tracer_id,
            source_data_list=output_data_list
        )


    except Exception as error:
        logger.error(f"{job_id}: Unable to scrape data. Job with tracer_id {tracer_id} failed. Job state was '{job_state.value}' Error: {error}")

        return JobOutput(
            job_state=BaseJobState.FAILED,
            tracer_id=tracer_id,
            source_data_list=[]
        )
    
    finally:
        try:
            if report_dict:
                report_path = os.path.join(file_dir, "webcam_report.json")
                os.makedirs(os.path.dirname(report_path), exist_ok=True)
                save_report(report_dict, report_path)
                logger.info(f"Report saved at {time.time()} and saved to: {report_path}")
                data_name = f"webcam_{case_study_name}_{tracer_id}"

                relative_path = f"{case_study_name}/{tracer_id}/{job_id}/webcam/report/{data_name}.json"
                
                media_data = KernelPlancksterSourceData(
                        name=data_name,
                        protocol=protocol,
                        relative_path=relative_path,
                    )
                    
                scraped_data_repository.register_scraped_json(
                        job_id=job_id,
                        source_data=media_data,
                        local_file_name=image_path,
                    )

                output_data_list.append(media_data)
        except Exception as error:
            logger.warning(f"Could not upload webcam-report due to {error}")    
        try:
            if os.path.exists(file_dir):
                shutil.rmtree(file_dir)
                logger.info(f"Deleted tmp directory '{file_dir}'.")
            else:
                logger.info(f"Temporary directory '{file_dir}' does not exist, skipping deletion.")

        except Exception as e:
            logger.warning("Could not delete tmp directory, exiting.")
        
