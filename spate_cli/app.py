import requests
import argparse
import configparser
import logging
import json
import time
import sys
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SpateCLI():
    def __init__(self,config={}):
        self.config = config

    def execute(self):
        result = self.send_request_for_execution()
        if self.config.get("wait"):
            if result["response"]["status"] == "complete":
                logging.info(json.dumps(result,indent=4))
            self.check_callback_url(result["response"]["callback_url"])
        logging.info(json.dumps(result,indent=4))
        return

    def check_callback_url(self,callback_url):
        data = self.format_request()
        data["url"] = "{}{}".format(self.config["url"],callback_url)
        for poll in range(self.config["poll"]):
            result = requests.get(**data)
            if result.ok:
                result = result.json()
                if result.get("complete"):
                    logging.info(json.dumps(result,indent=4))
                    sys.exit()
                elif result.get("paused"):
                    logging.info("Execution has been paused - please resume in the console")
                    sys.exit()
            time.sleep(2)
        logging.warning("Timed out waiting for the execution results")
        return

    def view_executions(self):
        data = self.format_request()
        data["url"] = "{}/api/v1/workflows/{}/executions".format(self.config["url"],self.config["uuid"])
        response = requests.get(**data)
        if not response.ok:
            logging.warning("Non 200 response from the workflow: {}".format(response.json()))
            return
        self.print_table(response.json())
        return

    def send_request_for_execution(self):
        data = self.format_request(add_payload=True)
        data["url"] = "{}/api/v1/endpoints/{}".format(self.config["url"],self.config["uuid"])
        response = requests.post(**data)
        if not response.ok:
            logging.warning("Non 200 response from the workflow: {}".format(response.json()))
            return
        return response.json()

    def load_config_from_file(self,path):
        config = {}
        if os.path.exists(path):
            parser = configparser.ConfigParser()
            parser.read(path)
            for each_section in parser.sections():
                for (each_key, each_val) in parser.items(each_section):
                    config[each_key.lower()] = each_val
        return config

    def print_table(self, myDict, colList=None):
        if not colList: colList = list(myDict[0].keys() if myDict else [])
        myList = [colList] # 1st row = header
        for item in myDict: myList.append([str(item[col] if item[col] is not None else '') for col in colList])
        colSize = [max(map(len,col)) for col in zip(*myList)]
        formatStr = ' | '.join(["{{:<{}}}".format(i) for i in colSize])
        myList.insert(1, ['-' * i for i in colSize]) # Seperating line
        for item in myList: print(formatStr.format(*item))

    def format_request(self,add_payload=False):
        if "url" not in self.config:
            logging.error("url is required")
            sys.exit()
        if not self.config["url"].startswith("http"):
            logging.error("url does not start with http")
            sys.exit()
        if "uuid" not in self.config:
            logging.error("uuid is required")
            sys.exit()
        data = {
            "url":"",
            "headers":{},
            "verify":True
        }
        if "skip_verification" in self.config:
            data["verify"] = False
        if add_payload:
            if "payload" in self.config:
                data["json"] = self.config["payload"]
        if "token" in self.config:
            data["headers"]["token"] = self.config["token"]
        return data

if __name__ == "__main__":
    client = SpateCLI()

    parser = argparse.ArgumentParser(description='Spate CLI for the API Trigger')

    parser.add_argument('--uuid', type=str,
                    help='uuid of the workflow')
    parser.add_argument('--url', type=str,
                    help='url for the spate-ingress service')
    parser.add_argument('--payload', type=str,
                    help="payload (json) that is sent to the workflow (e.g. '{\"key\":\"value\"}')")
    parser.add_argument('--token', type=str,
                    help='authentication token for the workflow')
    parser.add_argument('--config', type=str,
                    help='path to optional config file (cli arguments over-write the config file)')
    parser.add_argument('--level', type=str,
                    help='set the logging level (e.g. info,debug,warning,error)',default="info")
    parser.add_argument('--verbose', action='store_true',
                    help='enable verbose logging')
    parser.add_argument('--skip-verification', action='store_true',
                    help='skip certificate verification')
    parser.add_argument('--action', type=str,
                    help='action to perform (e.g. execute,view,config')
    parser.add_argument('--wait', action='store_true',
                    help='wait for the execution to complete')
    parser.add_argument('--poll', type=int, default=10,
                    help='number of iterations to wait for execution to complete (only used when <wait> is set)')
    args = parser.parse_args()

    # set up logging
    if args.verbose:
        args.level = "debug"
    logging.basicConfig(format='%(levelname)s - %(asctime)s - %(message)s',
      level=getattr(logging,args.level.upper())
    )

    # read in values from config file
    config = {}
    if args.config:
        if not os.path.exists(args.config):
            logging.error("Config file:{} does not exist".format(args.config))
            sys.exit()
        config = client.load_config_from_file(args.config)
    # over-write config file with cli arguments
    if args:
        for key,value in vars(args).items():
            if value != None:
                config[key.lower()] = value

    # load payload if exists
    if args.payload:
        config["payload"] = json.loads(args.payload)

    if "url" in config:
        config["url"] = config["url"].strip("/")

    # execute the action
    client.config = config
    if args.action == "execute":
        client.execute()
    elif args.action == "view":
        client.view_executions()
    elif args.action == "config":
        logging.info(json.dumps(config,indent=4))
    else:
        logging.info("Nothing to do!")
