import argparse
from search import Scanner
from rich import print
from threading import Thread
from streaming import StreamManager
import json
import rtsp
import os

class CLI:
    def __init__(self, shodan_api_key, clarifai_api_key=None, geoip_api_key=None, settings=None):
        self.settings=settings
        self.scanner = Scanner(
            shodan_api_key=shodan_api_key,
            clarifai_api_key=clarifai_api_key,
            geoip_api_key=geoip_api_key,
            settings=settings
            
        )

    def status(self):
        print("Status [green]OK[/green]!")
        
    def search(
        self,
        preset,
        check=None,
        tag=None,
        store=None,
        loc=None,
        places=None,
        debug=None,
        parallel=None,
        protocol=None,
        query="",
        ):
        # Set defaults based on settings if not provided
        if check is None:
            check = self.settings.check
        if tag is None:
            tag = self.settings.tag
        if store is None:
            store = self.settings.store
        if loc is None:
            loc = self.settings.loc
        if places is None:
            places = self.settings.places
        if debug is None:
            debug = self.settings.debug
        if parallel is None:
            parallel = self.settings.parallel
        if protocol is None:
            protocol = self.settings.protocol
        print(f"Running search with preset: {preset}")

        res = self.scanner.scan_preset(
        preset, check, tag, places, loc, debug, parallel, query
        )
        
        if store:
            json.dump(res, open(store, "w"))


    def search_custom(
        self,
        camera_type,
        url_scheme="",
        check_empty_url="",
        check_empty=None,
        tag=None,
        loc=None,
        places=None,
        parallel=None,
        store=None,
        search_q="webcams",
        debug=None,
        ):
        # Set defaults based on settings if not provided
        if check_empty is None:
            check_empty = self.settings.check
        if tag is None:
            tag = self.settings.tag
        if loc is None:
            loc = self.settings.loc
        if places is None:
            places = self.settings.places
        if parallel is None:
            parallel = self.settings.parallel
        if store is None:
            store = self.settings.store
        if debug is None:
            debug = self.settings.debug
        """
        :param camera_type: string, the type of camera. this string must appear in the data returned by Shodan
        :param url_scheme: string, the format in which the result will be displayed
        :param check_empty_url: string, the format that leads to an image that could be downloaded
        :param check_empty: boolean, indicates whether or not you want to check if the image is completely black or white
        :param tag: boolean, indicates whether or not you want to generate descriptions for the image
        :param store: (optional)string, indicates the location where you want to save the results.
        :param search_q: string, the term to search for in Shodan
        :param debug: boolean, indicates whether or not you want to print debug info.
        """
        res = self.scanner.scan(
            camera_type=camera_type,
            url_scheme=url_scheme,
            check_empty_url=check_empty_url,
            check_empty=check_empty,
            tag=tag,
            search_q=search_q,
            loc=loc,
            places=places,
            debug=debug,
        )
        if store:
            json.dump(res, open(store, "w"))

    def play(self, url: str):
        """
        :param url: string, the URL of the webcam
        """
        if url.startswith("rtsp"):
            rtsp.play(url)
        else:
            os.system(f"open {url}")