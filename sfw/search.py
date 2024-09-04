import argparse
import os
import traceback
import sys
import shodan
import warnings
import socket
import json
from PIL import Image
from rich import print
from halo import Halo
from pathlib import Path
from geoip import Locater
from crfi import Clarifai
from cam import get_cam, CameraEntry, Camera
from streaming import StreamRecord, StreamManager
from utils import Dummy
import threading


def handle():
    err = sys.exc_info()[0]
    print("[red]ERROR:[/red]")
    print(err)
    print(traceback.format_exc())


class Scanner(object):
    def __init__(self, shodan_api_key, clarifai_api_key=None, geoip_api_key=None, settings=None):
        socket.setdefaulttimeout(5)
        directory = Path(__file__).parent
        self.settings = settings
        
        self.SHODAN_API_KEY = shodan_api_key
        self.CLARIFAI_API_KEY = clarifai_api_key
        self.GEOIP_API_KEY = geoip_api_key
        
        self.api = shodan.Shodan(self.SHODAN_API_KEY)
        # preset url schemes
        self.clarifai = self.locator = self.places = self.vllm_manager = None
        self.cli = True
        with open(directory / "cams.json") as f:
            self.config = json.load(f)

    def init_clarifai(self):
        if self.CLARIFAI_API_KEY is None:
            raise KeyError("Clarifai API key not provided")
        self.clarifai = Clarifai(self.CLARIFAI_API_KEY)

    def init_geoip(self):
        if self.GEOIP_API_KEY is None:
            raise KeyError("Geoip API key not provided")
        self.locator = Locater(self.GEOIP_API_KEY)

    def init_places(self):
        try:
            from places_mod import Places

            self.places = Places()
        except ImportError as e:
            warnings.warn(
                "Please make sure you have torch and torchvision installed to use this feature"
            )
            raise e
        except Exception as e:
            print(f"Unexpected Error: {e}")
   
    def tag_image(self, url):
        concepts = self.clarifai.get_concepts(url)
        return concepts

    def check_empty(self, im: Image, tolerance=5) -> bool:
        extrema = im.convert("L").getextrema()
        if abs(extrema[0] - extrema[1]) <= tolerance:    #need to check the tolerance filter
            return False
        return True

    def output(self, *args, **kwargs):
        print(*args, **kwargs)

    def scan(
        self,
        cam: Camera,
        check_empty=None,
        tag=None,
        geoip=True,
        places=None,
        debug=None,
        parallel=None,
        add_query="",
        stream_manager: None | StreamManager = None,
        stdout_lock=None,
        indicator=True,
        ):
        # Set defaults based on settings if not provided
        if check_empty is None:
            check_empty = self.settings.check
        if tag is None:
            tag = self.settings.tag
        if places is None:
            places = self.settings.places
        if debug is None:
            debug = self.settings.debug
        if parallel is None:
            parallel = self.settings.parallel
        print(
            f"loc:{geoip}, check_empty:{check_empty}, clarifai:{tag}, places:{places}, async:{parallel}"
        )
        print(stream_manager)
        query = cam.query + " " + add_query
        if debug:
            print(f"Searching for: {query}")
        else:
            os.environ["OPENCV_LOG_LEVEL"] = "OFF"
        if self.SHODAN_API_KEY == "":
            print("[red]Please set up shodan API key![/red]")
            return
        spinner = Halo(text="Initializing...", spinner="dots") if indicator else Dummy()
        spinner.start()
        if tag and (self.clarifai is None):
            self.init_clarifai()
        if geoip and (self.locator is None):
            self.init_geoip()
        if places and (self.places is None):
            self.init_places()
        spinner.succeed()
        spinner = (
            Halo(text="Looking for possible servers...", spinner="dots")
            if indicator
            else Dummy()
        )
        spinner.start()
        try:
            raw_response = self.api.search(query)
            # print(raw_response)  # Add this line to inspect the response
            results = raw_response
            spinner.succeed("Done")
        except Exception as e:
            spinner.fail(f"Get data from API failed: {e}")
            if debug:
                handle()
            return
        max_time = len(results["matches"]) * 10
        print(f"maximum time: {max_time} seconds")
        camera_type_list = []
        for result in results["matches"]:
            if cam.camera_type is None or cam.camera_type in result["data"]:
                camera_type_list.append(result)
        store = []
        scanner_threads = []
        stdout_lock = stdout_lock or threading.Lock()
        for result in camera_type_list:
            entry = CameraEntry(result["ip_str"], int(result["port"]))
            args = (
                cam,
                entry,
                stdout_lock,
                check_empty,
                tag,
                geoip,
                places,
                debug,
                stream_manager,
            )
            if parallel:
                t = threading.Thread(target=self.scan_one, args=args)
                t.start()
                scanner_threads.append(t)
            else:
                self.scan_one(*args)
        for t in scanner_threads:
            t.join()
        return store

    def scan_one(
        self,
        cam: Camera,
        entry: CameraEntry,
        stdout_lock: threading.Lock,
        check_empty=None,
        tag=None,
        geoip=True,
        places=None,
        debug=None,
        stream_manager: None | StreamManager = None,
        ):
        # Set defaults based on settings if not provided
        if check_empty is None:
            check_empty = self.settings.check
        if tag is None:
            tag = self.settings.tag
        if places is None:
            places = self.settings.places
        if debug is None:
            debug = self.settings.debug
        try:
            res = ""  # Track results locally

            if cam.check_accessible(entry):
                if not check_empty:
                    display_url = cam.get_display_url(entry)
                    #print(f"Display URL: {display_url}")
                    res += display_url + "\n"
                    if stream_manager is not None:
                        record = StreamRecord(cam, entry)
                        print(f"Adding record: {record}")
                        stream_manager.add(record)
                else:
                    im = cam.get_image(entry)
                    if im is None:
                        print(f"Failed to retrieve image for: {entry}")
                    else:
                        print(f"Image retrieved for: {entry}, image size: {im.size}")
                        is_empty = self.check_empty(im)
                        print(f"Image is empty: {is_empty}")
                        if is_empty:
                            res += cam.get_display_url(entry) + "\n"
                            if stream_manager is not None:
                                record = StreamRecord(cam, entry)
                                print(f"Adding record: {record}")
                                stream_manager.add(record)
                        else:
                            return
                if geoip:
                    country, region, hour, minute = self.locator.locate(entry.ip)
                    geoip_info = f":earth_asia:[green]{country} , {region} {hour:02d}:{minute:02d}[/green]"
                    print(f"URL: {display_url} \n LOCATION : {geoip_info} ")
                    res += geoip_info + "\n"
                if tag:
                    tags = self.tag_image(cam.get_image(entry))
                    print(f"Tags: {tags}")
                    for t in tags:
                        res += f"|[green]{t}[/green]| "
                    if len(tags) == 0:
                        res += "[i green]no description[i green]\n"
                    res += "\n"
                if places:
                    im = cam.get_image(entry)
                    places_output = self.places.output(im)
                    print(f"Places Output: {places_output}")
                    res += places_output + "\n"
                with stdout_lock:
                    print(res)  # Final print of accumulated results
        except Exception as e:
            if debug:
                print(f"Exception: {e}")
                raise e

    def testfunc(self, **kwargs):
        print(kwargs)

    def scan_preset(
        self,
        preset,
        check=None,
        tag=None,
        places=None,
        loc=None,
        debug=None,
        parallel=None,
        add_query="",
        stream_manager: None | StreamManager = None,
        stdout_lock=None,
        ):
        # Set defaults based on settings if not provided
        if check is None:
            check = self.settings.check
        if tag is None:
            tag = self.settings.tag
        if places is None:
            places = self.settings.places
        if loc is None:
            loc = self.settings.loc
        if debug is None:
            debug = self.settings.debug
        if parallel is None:
            parallel = self.settings.parallel

        if preset not in self.config:
            raise KeyError("The preset entered doesn't exist")
        for key in self.config[preset]:
            if self.config[preset][key] == "[def]":
                self.config[preset][key] = self.config["default"][key]
        print("beginning scan...")
        cam = get_cam(**self.config[preset])
        print(f"Accessible Camera format: {cam}")
        res = self.scan(
            cam=cam,
            check_empty=check,
            tag=tag,
            geoip=loc,
            places=places,
            debug=debug,
            parallel=parallel,
            add_query=add_query,
            stream_manager=stream_manager,
            stdout_lock=stdout_lock,
        )

        print("scan finished")
        return res
