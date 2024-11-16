from datetime import datetime,timedelta
from app.sdk.models import KernelPlancksterSourceData, BaseJobState, JobOutput
from app.sdk.scraped_data_repository import KernelPlancksterSourceData
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

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_images_from_url(url: str, date: datetime) -> Image.Image:
    
    split_url = url.split('/')
    webcam_id = split_url[3]
    url_template = "https://storage.roundshot.com/{webcam_id}/{year}-{month}-{day}/{hour}-{minute}-00/{year}-{month}-{day}-{hour}-{minute}-00_half.jpg"
    
    try:
        url = url_template.format(
                webcam_id=webcam_id,
                year=date.year,
                month=f"{date.month:02}",
                day=f"{date.day:02}",
                hour=f"{date.hour:02}" if date >= datetime.now() else "12",
                minute=f"{date.minute:02}" if date >= datetime.now() else "00",
            )
        logger.info(f"Fetching image from: {url}")
            
        # Fetch the image from the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
            
        # Convert the response content to a PIL Image
        image = Image.open(BytesIO(response.content))
    except Exception as e:
        logger.error(f"Error fetching image for {date}: {e}")
        
    return image

def save_image(image, path, factor=1.0, clip_range=(0, 1)):
    """Save the image to the given path."""
    np_image = np.array(image) * factor
    np_image = np.clip(np_image, clip_range[0], clip_range[1])
    np_image = (np_image * 255).astype(np.uint8)
    Image.fromarray(np_image).save(path)

# Updated scrape_URL function
def scrape_URL(case_study_name, job_id, tracer_id, scraped_data_repository, log_level, latitude, longitude, start_date: datetime, end_date: datetime, file_dir, url, interval):
    try:
        logger = logging.getLogger(__name__)
        logging.basicConfig(level=log_level)

        job_state = BaseJobState.CREATED
        current_data: KernelPlancksterSourceData | None = None
        last_successful_data: KernelPlancksterSourceData | None = None

        protocol = scraped_data_repository.protocol

        output_data_list: List[KernelPlancksterSourceData] = []
        if job_state:  # for typing
            logger.info(f"{job_id}: Starting Job")
            job_state = BaseJobState.RUNNING
            try:
                logger.info(f"starting with webcam URL")
                image_dir = os.path.join(file_dir, "images")
                os.makedirs(image_dir, exist_ok=True)
                current_date = start_date
                interval = timedelta(minutes=interval) if start_date == datetime.now() else timedelta(days=1)
                iteration=0
                logger.info(f"Data scraping Interval set as:{interval}")
                while (current_date <= end_date):
                    image = fetch_images_from_url(url=url,date=current_date)

                    if image is None:
                        logger.error("Error: Unable to fetch image.")
                        continue
                    if (current_date <= end_date) and (np.mean(image) != 0.0):  

                        # Save the image locally
                        file_extension = image.format.lower() if image.format else "png"
                        image_filename = f"URLbased_webcam.{file_extension}"
                        unix_timestamp = int(current_date.timestamp()) + iteration   
                        image_path = os.path.join(image_dir, "scraped", image_filename)
                        os.makedirs(os.path.dirname(image_path), exist_ok=True)
                        save_image(image, image_path, factor=1.5 / 255, clip_range=(0, 1))
                        logger.info(f"Scraped Image at {time.time()} and saved to: {image_path}")

                        # Register it in Kernel Planckster
                        data_name = f"webcam_{latitude}_{longitude}"

                        relative_path = f"{case_study_name}/{tracer_id}/{job_id}/{unix_timestamp}/webcam/{data_name}.{file_extension}"

                        current_date += interval
                        iteration += 1
                        
                        media_data = KernelPlancksterSourceData(
                            name=data_name,
                            protocol=protocol,
                            relative_path=relative_path,
                        )
                        
                        try:
                            scraped_data_repository.register_scraped_photo(
                                job_id=job_id,
                                source_data=media_data,
                                local_file_name=image_path,
                            )
                        except Exception as e:
                            logger.info(f"Could not register file: {e}")
                        
                        print(f"job_id = {job_id} and tracer_id = {tracer_id}")
                        response_time = time.time() - start_date.timestamp()
                        response_data = {
                            "message": f"Pipeline processing completed",
                            "response_time": f"{response_time:.2f} seconds"
                        }

                        output_data_list.append(media_data)
                time.sleep(0.1)   
                
                job_state = BaseJobState.FINISHED
                logger.info(f"{job_id}: Job finished")
                
                return JobOutput(
                    job_state=job_state,
                    tracer_id=tracer_id,
                    source_data_list=output_data_list
                )

            except Exception as e:
                logger.error(f"Error in processing pipeline: {e}")
                job_state = BaseJobState.FAILED
                f"{job_id}: Unable to scrape data. Error:\n{e}\nJob with tracer_id {tracer_id} failed.\nLast successful data: {last_successful_data}\nCurrent data: \"{current_data}\", job_state: \"{job_state}\""
                
                return JobOutput(
                    job_state=job_state,
                    tracer_id=tracer_id,
                    source_data_list=[]
                )

        if os.path.exists(file_dir):
            try:
                shutil.rmtree(file_dir)
                print("deleted tmp directory, exiting")
            except Exception as e:
                logger.warning(f"Could not delete tmp directory,due to error: '{e}'")
            else:
                logger.warning(f"Temporary directory '{file_dir}' does not exist, skipping deletion.")
                
        return JobOutput(
                job_state=job_state,
                tracer_id=tracer_id,
                source_data_list=output_data_list
            )

    except Exception as error:
        logger.error(f"{job_id}: Unable to scrape data. Job with tracer_id {tracer_id} failed. Error:\n{error}")
        job_state = BaseJobState.FAILED
        try:
            logger.warning("deleting tmp directory")
            shutil.rmtree(file_dir)
        except Exception as e:
            logger.warning("Could not delete tmp directory, exiting")
