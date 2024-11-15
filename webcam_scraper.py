import logging
import pprint
import sys
from app.sdk.models import KernelPlancksterSourceData
from app.sdk.scraped_data_repository import ScrapedDataRepository
from app.setup import datetime_parser, setup, string_validator
from app.url_image_scraper import scrape_URL



def main(
    case_study_name: str,
    job_id: int,
    tracer_id: str,
    latitude: str,
    longitude: str,
    date: str,
    file_dir: str,
    url: str,
    start_date: str,
    end_date: str,
    interval: int,
    kp_host: str,
    kp_port: str,
    kp_auth_token: str,
    kp_scheme: str,
    log_level: str = "WARNING"
) -> None:

    try:
        logger = logging.getLogger(__name__)
        logging.basicConfig(level=log_level)

    
        if not all([case_study_name, job_id, tracer_id, latitude, longitude, date]):
            logger.error(f"case_study_name, job_id, tracer_id, coordinates, and date range must all be set.") 
            raise ValueError("case_study_name, job_id, tracer_id, coordinates, and date range must all be set.")

        string_variables = {
            "case_study_name": case_study_name,
            "job_id": job_id,
            "tracer_id": tracer_id,
            "latitude": latitude,
            "longitude": longitude
        }

        logger.info(f"Validating string variables:  {string_variables}")

        for name, value in string_variables.items():
            string_validator(value, name)

        logger.info(f"String variables validated successfully!")

        logger.info(f"Converting start and end date to datetime objects")
        start_date_dt = datetime_parser(start_date)
        end_date_dt = datetime_parser(end_date)
        if start_date_dt > end_date_dt:
            raise ValueError(f"Start date must be before end date. Found: {start_date_dt} > {end_date_dt}.")
        logger.info(f"Start and end date converted to datetime objects successfully")

        logger.info(f"Setting up scraper for case study: {case_study_name}")

        kernel_planckster, protocol, file_repository = setup(
            job_id=job_id,
            logger=logger,
            kp_auth_token=kp_auth_token,
            kp_host=kp_host,
            kp_port=kp_port,
            kp_scheme=kp_scheme,
        )

        scraped_data_repository = ScrapedDataRepository(
            protocol=protocol,
            kernel_planckster=kernel_planckster,
            file_repository=file_repository,
        )

        logger.info(f"Scraper setup successfully for case study: {case_study_name}")

    except Exception as e:
        logger.error(f"Error setting up scraper: {e}")
        sys.exit(1)

    logger.info(f"Scraping data for case study: {case_study_name}")

    scrape_URL(
        case_study_name=case_study_name,
        job_id=job_id,
        tracer_id=tracer_id,
        scraped_data_repository=scraped_data_repository,
        log_level=log_level,
        latitude=latitude,
        longitude=longitude,  
        start_date=start_date_dt,
        end_date=end_date_dt,
        file_dir=file_dir,
        url=url,
        interval=interval,
    )

    logger.info(f"Data scraped successfully for case study: {case_study_name}")



if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="Scrape data from Sentinel datacollection.")

    parser.add_argument(
        "--case-study-name",
        type=str,
        default="webcam",
        help="The name of the case study",
    )

    parser.add_argument(
        "--job-id",
        type=str,
        default="1",
        help="The job id",
    )

    parser.add_argument(
        "--tracer-id",
        type=str,
        default="1",
        help="The tracer id",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="WARNING",
        help="The log level to use when running the scraper. Possible values are DEBUG, INFO, WARNING, ERROR, CRITICAL. Set to WARNING by default.",
    )

    parser.add_argument(
        "--latitude",
        type=str,
        default="0",
        help="latitude of the location",
    )

    parser.add_argument(
        "--longitude",
        type=str,
        default="0",
        required=True,
        help="longitude of the location",
    )

    parser.add_argument(
        "--date",
        type=str,
        default="2023-08-08",
        required=True,
        help="start date",
    )

    parser.add_argument(
        "--start_date",
        type=str,
        required=True,
        help="Start datetime in the format 'YYYY-MM-DDTHH:MM",
    )

    parser.add_argument(
        "--end_date",
        type=str,
        required=True,
        help="End datetime in the format 'YYYY-MM-DDTHH:MM",
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default="60",
        help="Time interval between screenshots",
    )

    parser.add_argument(
        "--kp_host",
        type=str,
        default="60",
        help="kp host",
    )

    parser.add_argument(
        "--kp_port",
        type=int,
        default="60",
        help="kp port",
    )

    parser.add_argument(
        "--kp_auth_token",
        type=str,
        default="60",
        help="kp auth token",
        )

    parser.add_argument(
        "--kp_scheme",
        type=str,
        default="http",
        help="kp scheme",
        )

    parser.add_argument(
        "--file_dir",
        type=str,
        default="./.tmp",
        help="saved file directory",
    )

    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="URL of the camera stream",
    )
    

    parser.add_argument(
        "--duration",
        type=int,
        default="600",
        help="total duration to take screenshots",
    )


    args = parser.parse_args()


    main(
        case_study_name=args.case_study_name,
        job_id=args.job_id,
        tracer_id=args.tracer_id,
        log_level=args.log_level,
        latitude=args.latitude,
        longitude=args.longitude,
        date=args.date,
        kp_host=args.kp_host,
        kp_port=args.kp_port,
        kp_auth_token=args.kp_auth_token,
        kp_scheme=args.kp_scheme,
        start_date=args.start_date,
        end_date=args.end_date,
        file_dir=args.file_dir,
        url=args.url,
        interval=args.interval,
    )


