import re
from typing import NamedTuple

from app.config import ROUNDSHOT_WEBCAM_MATRIX

URL_TEMPLATE = "https://storage.roundshot.com/{webcam_id}/{year}-{month}-{day}/{hour}-{minute}-00/{year}-{month}-{day}-{hour}-{minute}-00_half.jpg"


class KernelPlancksterRelativePath(NamedTuple):
    case_study_name: str
    tracer_id: str
    job_id: str
    timestamp: str
    dataset: str
    evalscript_name: str
    image_hash: str
    file_extension: str

def generate_relative_path(case_study_name, tracer_id, job_id, timestamp, dataset, evalscript_name, image_hash, file_extension):
    return f"{case_study_name}/{tracer_id}/{job_id}/{timestamp}/sentinel/{dataset}_{evalscript_name}_{image_hash}.{file_extension}"

def parse_relative_path(relative_path) -> KernelPlancksterRelativePath:
    parts = relative_path.split("/")
    case_study_name = parts[0]
    tracer_id = parts[1]
    job_id = parts[2]
    timestamp = parts[3]
    dataset, evalscript_name, image_hash_extension = parts[5].split("_")
    image_hash, file_extension = image_hash_extension.split(".")
    return KernelPlancksterRelativePath(case_study_name, tracer_id, job_id, timestamp, dataset, evalscript_name, image_hash, file_extension)


def sanitize_location(location: str):
    """
    Sanitize a location string by removing single dashes, and changing whitespaces to double dots.
    """
    location = location.replace("-", "")
    location = location.replace(" ", "")
    return location

def get_webcam_name(webcam_id: str) -> str:

    webcam_dict_array = (dict for dict in ROUNDSHOT_WEBCAM_MATRIX if dict["webcam_id"] == webcam_id)

    try:
        webcam_dict = next(webcam_dict_array)
        location_raw, country, latitude, longitude = webcam_dict["location"], webcam_dict["country"], webcam_dict["latitude"], webcam_dict["longitude"]
        location = sanitize_location(location_raw)


        return f"{location}..{country}..{latitude}..{longitude}"

    except StopIteration:
        raise StopIteration(f"Webcam ID '{webcam_id}' not found in ROUNDSHOT_WEBCAM_MATRIX")

    except Exception as e:
        raise Exception(f"Error while fetching webcam info for webcam ID '{webcam_id}': {e}")    


def get_webcam_info_from_name(webcam_name: str) -> dict[str, str]:
    
    webcam_split = webcam_name.split("..")


    webcam_dict = {
        "location": webcam_split[0],
        "country": webcam_split[1],
        "latitude": webcam_split[2],
        "longitude": webcam_split[3]
    }

    return webcam_dict
        