from app.sdk.models import KernelPlancksterSourceData, BaseJobState, JobOutput, ProtocolEnum
from app.sdk.scraped_data_repository import ScrapedDataRepository,  KernelPlancksterSourceData
import time
import numpy as np
from typing import List
from PIL import Image
from collections import Counter
import logging
import time
import cv2
import os
import shutil
from PIL import Image
import re

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to fetch an image from the stream
def fetch_image_from_stream(url)->Image:
    try:
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            logger.error("Error: Unable to open video stream.")
            return None

        ret, frame = cap.read()
        if not ret:
            logger.error("Error: Unable to read frame from video stream.")
            return None

        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        return img
    except Exception as e:
        logger.error(f"Error fetching image from stream: {e}")
        return None
    finally:
        cap.release()

def sanitize_filename(filename):
    # Replace disallowed characters with underscores
    return re.sub(r'[^\w./]', '_', filename)

def save_image(image, path, factor=1.0, clip_range=(0, 1)):
    """Save the image to the given path."""
    np_image = np.array(image) * factor
    np_image = np.clip(np_image, clip_range[0], clip_range[1])
    np_image = (np_image * 255).astype(np.uint8)
    Image.fromarray(np_image).save(path)

# Updated scrape_URL function
def scrape_URL(job_id, tracer_id, scraped_data_repository, log_level, latitude, longitude, date, file_dir, url, interval, duration):
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
            num_screenshots = duration // interval    
            start_time = time.time()  # Record start time for response time measurement
            try:
                logger.info(f"starting with webcam URL")
                image_dir = os.path.join(file_dir, "images")
                os.makedirs(image_dir, exist_ok=True)
                start_time = time.perf_counter()
                next_capture_time = start_time
                num_screenshots=0

                while (time.perf_counter() - start_time) < duration:
                    image = fetch_image_from_stream(url)
                    if image is None:
                        logger.error("Error: Unable to fetch image.")
                        continue
                    if (time.perf_counter() >= next_capture_time) and (np.mean(image) != 0.0) and (num_screenshots!=duration//interval):  
                        image_filename = f"URLbased_webcam.png"
                        data_name = f"Webcam_{latitude}_{longitude}_{date}_{time.time()}"
                        image_path = os.path.join(image_dir, "scraped", image_filename)
                        os.makedirs(os.path.dirname(image_path), exist_ok=True)
                        save_image(image, image_path, factor=1.5 / 255, clip_range=(0, 1))
                        logger.info(f"Scraped Image at {time.time()} and saved to: {image_path}")
                        relative_path = f"Webcam/{tracer_id}/{job_id}/scraped/{sanitize_filename(data_name)}.png"
                        next_capture_time += interval
                        num_screenshots+=1
                        
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
                            logger.info("Could not register file: ", e)
                        
                        print(f"job_id = {job_id} and tracer_id = {tracer_id}")
                        response_time = time.time() - start_time
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
                f"{job_id}: Unable to scrape data. Error:\n{error}\nJob with tracer_id {tracer_id} failed.\nLast successful data: {last_successful_data}\nCurrent data: \"{current_data}\", job_state: \"{job_state}\""
                
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
