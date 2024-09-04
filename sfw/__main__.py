import argparse
from cli import CLI

class Config:
    pass

settings = Config()

def main():
    parser = argparse.ArgumentParser(description="Scanner for Cameras")
    parser.add_argument("--shodan_api_key", required=True, help="Shodan API key")
    parser.add_argument("--clarifai_api_key", help="Clarifai API key")
    parser.add_argument("--geoip_api_key", help="GeoIP API key")
    parser.add_argument("--preset", required=True, help="Run preset")
    parser.add_argument("--check", action="store_true", help="Check for empty images")
    parser.add_argument("--tag", action="store_true", help="Generate descriptions for the webcam")
    parser.add_argument("--store", help="Location to save the results")
    parser.add_argument("--loc", action="store_true", help="Include location data")
    parser.add_argument("--places", action="store_true", help="Use the 'places' model for descriptions")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel processing")
    parser.add_argument("--protocol", help="Protocol to use (http or rtsp)")
    parser.add_argument("--query", default="", help="Additional query for the scan")

    args = parser.parse_args()
    
    settings.shodan_api_key = args.shodan_api_key
    settings.clarifai_api_key = args.clarifai_api_key
    settings.geoip_api_key = args.geoip_api_key
    settings.preset = args.preset
    settings.check = args.check
    settings.tag = args.tag
    settings.store = args.store
    settings.loc = args.loc
    settings.places = args.places
    settings.debug = args.debug
    settings.parallel = args.parallel
    settings.protocol = args.protocol
    settings.query = args.query

    # Initialize CLI with provided API keys
    cli = CLI(
        shodan_api_key=args.shodan_api_key,
        clarifai_api_key=args.clarifai_api_key,
        geoip_api_key=args.geoip_api_key,
        settings=settings
    )

    # Run the preset scan
    cli.search(
        preset=args.preset,
        check=args.check,
        tag=args.tag,
        store=args.store,
        loc=args.loc,
        places=args.places,
        debug=args.debug,
        parallel=args.parallel,
        protocol=args.protocol,
        query=args.query,
    )

if __name__ == "__main__":
    main()
