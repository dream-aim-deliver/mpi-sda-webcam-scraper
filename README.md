##WEBCAM_SCRAPER
## Usage

* `MJPG` : for public [MJPG streamers](https://github.com/jacksonliam/mjpg-streamer)

* `webcamXP` : for public [webcamXP streamers](http://www.webcamxp.com/)

* `yawCam`: for public [yawCam steamers](https://www.yawcam.com/)

* `hipcam`: for public hipcam streamers

* `rtsp`: **DANGER** searches for rtsp servers on shodan, and performs enumeration on them to try and find streams

* `help`: for more options and help

The program will output a list of links with the format of `ip_address:port`, and descriptions of the image beneath it.

If your terminal supports links, click the link and open it in your browser, otherwise, copy the link and open it in your browser.

## Installation
1. Clone this repository

2. install requirements.txt: `pip install -r requirements.txt`

3. set up shodan:
   go to [shodan.io](https://shodan.io), register/log in and grab your API key

4. set up clarifai:
   go to [clarifai.com](https://clarifai.com), register/log in, create an application and grab your API key.
   Alternatively, use the local [places365](#places365-on-device-footage-classification) model.

5. setup geoip:
   go to [geo.ipify.org](https://geo.ipify.org), register/log in and grab your API key
   
6. Add API keys:
   1. open demo.sh file
   2. enter your shodan, clarifai and geoip API keys

And then you can [run](#Usage) the program!

## Places365: On device footage classification
It is now possible to run [the Places365 model](https://github.com/CSAILVision/places365),
a model fined tuned for real world locations,
to get information about webcam footage.

To use this model, you need to install the following packages:
```bash
pip install -r requirements-places.txt
```

Then, you can run the program with the `--places` flag set
