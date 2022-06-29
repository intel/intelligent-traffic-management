"""
Copyright 2022 Intel Corporation
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import json
import logging
import os
import psycopg2
import re
import requests
import sys
import time
from flask import Flask, render_template, make_response

app = Flask(__name__)
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s :: %(message)s")
HOST_IP = os.getenv("HOST_IP")
LOCAL_PORT = os.getenv("LOCAL_PORT")
LOCAL_HOST = os.getenv("LOCAL_HOST")
NAMESPACE = os.getenv('NAMESPACE')
GRAFANA_HOST = os.getenv("GRAFANA_HOST")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD")
GRAFANA_PORT = "3000"
INFLUXDB_URL = "influxdb.{}.svc.cluster.local:8086".format(NAMESPACE)
PSQL_USER = os.getenv("PSQL_USER")
PSQL_PASS = os.getenv("PSQL_PASS")

MAP_JS_CDN = "https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.4.3/build/ol.js"
JS_CDN_INTEGRITY = "sha384-RffttofZaGGmE3uVvQmIW/dh1bzuHAJtWkxFyjRkb7eaUWfHo3W3GV8dcET2xTPI"
MAP_CSS_CDN = "https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.4.3/css/ol.css"

NUM_CH = 1
CONF_DATA, URL_DATA = {}, {}

class PsqlConn:
    def __init__(self, username_, password_, host_="localhost", port_=32432, database_="itm_metadata"):
        retries = 5
        i = 0
        while i <= retries:
            time.sleep(3)
            try:
                self.conn = psycopg2.connect(user=username_,
                                        password=password_,
                                        host=host_,
                                        port=port_,
                                        database=database_,
                                        connect_timeout=3)
                break
            except (Exception, psycopg2.Error) as error:
                log.error(error)
            i += 1

    def retrieve_entries(self):
        rows = []
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM itm_camera;")
            rows = cursor.fetchall()
            cursor.close()
        except (Exception, psycopg2.Error) as error:
            cursor.execute("rollback")
            log.error(error)
            return -1
        return rows

    def close_conn(self):
        self.conn.close()

class GrafanaConnect:
    """
    Class to communicate with grafana server
    """
    def __init__(self, grafana_url, map_server_url, influxdb_url, user, password):
        """
        Init function
        """
        self.grafana_url = grafana_url
        self.map_server_url = map_server_url
        self.influxdb_url = influxdb_url
        self.datasource_url = os.path.join(self.grafana_url, 'api/datasources')
        self.dashboard_url = os.path.join(self.grafana_url, 'api/dashboards/db')
        self.datasource_search_url = os.path.join(self.grafana_url, 'api/search')
        self.auth = requests.auth.HTTPBasicAuth(user, password)
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
        }

    def _post(self, url, json_data):
        """
        Post data to grafana server
        """
        try:
            r = requests.post(url, auth=self.auth,
                              headers=self.headers,
                              json=json_data)
            return r
        except Exception as err:
            log.error(f'Error: {err}')
            return -1

    def _get(self, url, timeout=None):
        """
        Get data from grafana server
        """
        try:
            r = requests.get(url, auth=self.auth, headers=self.headers, timeout=timeout)
            return r
        except Exception as err:
            log.error(err)
            return -1

    def create_datasource(self, template_path):
        """
        Add/Update datasource
        """
        with open(template_path, 'r') as f:
            json_data = json.loads(f.read())
        json_data["url"] = self.influxdb_url
        r = self._post(self.datasource_url, json_data=json_data)
        if r == -1:
            log.error('Failed to connect to grafana container.')
            sys.exit(-1)
        res = r.json()
        if 'Data source with the same name already exists' in res['message']:
            pass
        elif 'Datasource added' in res['message']:
            test_query = self.datasource_url + \
                         f'/proxy/{res["id"]}/query?db={json_data["database"]}' \
                         f'&q=SHOW%20RETENTION%20POLICIES%20on%20"{json_data["database"]}"&epoch=ms'
            r = self._get(test_query)
            if r.json()['results'][0]['statement_id'] == 0:
                log.info('Data added successfully')
            else:
                log.warning('Failed to add datasource')
        return res

    def add_dashboard(self, json_data, url=None):
        """
        Add/Update dashboard
        """
        if url:
            json_data['dashboard']['panels'][1]['url'] = self.map_server_url + url
        else:
            json_data['dashboard']['panels'][1]['url'] = self.map_server_url + '/dashboard'
        r = self._post(self.dashboard_url, json_data=json_data)
        try:
            res = r.json()
            log.info(f'Successfully added dashboard {res["id"]}')
        except:
            log.error(f'Error in updating dashboard. Message: {r}')
        return res

    def add_channel_dashbords(self, template_path, camera_conf):
        """
        Add/Update dashboards for each channel
        """
        url_data = {}
        with open(template_path, 'r') as f:
            str_data = f.read()
        for i in range(0, NUM_CH):
            st = re.sub("channel0", f'channel{i}', str_data)
            final_data = json.loads(st)
            final_data['dashboard']['title'] = f'ITM ({camera_conf["cameras"][i]["name"]}) - {camera_conf["cameras"][i]["address"]}'
            final_data['dashboard']['panels'][2]['url'] = "https://" + camera_conf["cameras"][i]["server_ip"] + f'/camera/{i}'
            final_data['dashboard']['panels'][2]['method'] = "iframe"
            res = self.add_dashboard(final_data, f'/camera/{i}')
            url_data[i] = GRAFANA_EXTERNAL_URL + res['url']
        return url_data

    def init_grafana_server(self, camera_config, datasource_template_path,
                            consolidated_dashboard_template_path,
                            channel_dashboard_template_path):
        """
        Initialize datasource and dashboards on grafana server
        """
        # test grafana api
        i = -1
        while i < 100:
            i += 1
            time.sleep(1)
            test = self._get(self.datasource_url, timeout=3)
            if test == -1 or test.status_code != 200:
                log.info(test)
                log.info('Connecting grafana: Grafana container not up yet, retrying...')
                continue
            else:
                break
        self.create_datasource(datasource_template_path)
        with open(consolidated_dashboard_template_path, 'r') as f:
            json_data = json.loads(f.read())
        res = self.add_dashboard(json_data)
        url_data = self.add_channel_dashbords(channel_dashboard_template_path,
                                              camera_config)
        url_data[-1] = GRAFANA_EXTERNAL_URL + res['url']
        return url_data


@app.route('/dashboard')
def dashboard():
    """
    Route to HTML page which shows MapUI. Home Page.
    """
    conf = CONF_DATA
    conf['urls'] = URL_DATA
    response = make_response(render_template('dashboard.html', title='Dashboard',
                             map_js=MAP_JS_CDN, map_cdn_integrity=JS_CDN_INTEGRITY,
                             map_css=MAP_CSS_CDN, config=json.dumps(conf)))
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    return response


@app.after_request
def add_csp(resp):
    resp.headers['Content-Security-Policy']  =  "frame-ancestors 'none' https://*:32000 ;" \
                                                "media-src 'none' https://*:30303 ; " \
                                                "object-src 'none' ; " \
                                                "connect-src 'none' ; " \
                                                "plugin-src 'none' ; " \
                                                "frame-src 'none' ; " \
                                                "img-src 'self' https://openlayers.org http://a.tile.openstreetmap.org http://b.tile.openstreetmap.org http://c.tile.openstreetmap.org https://*:30303  ; "
    return resp


def init_all(over_write=False):
    """
    Initialize global variables and
    update datasources and dashboards on grafana server
    """
    global NUM_CH, CONF_DATA, URL_DATA

    psqlDB = PsqlConn(PSQL_USER, PSQL_PASS, HOST_IP)
    i = 0
    while i < 15:
        time.sleep(5)
        entries = psqlDB.retrieve_entries()
        i += 1
        if isinstance(entries, int):
            continue
        else:
            break

    num_ch = len(entries)

    servers = []
    conf_data = {'cameras': [0] * num_ch}
    for i in range(0, num_ch):
        conf_data['cameras'][i] = {
            'id': entries[i][0],
            'name': entries[i][1],
            'address': entries[i][2],
            'latitude': entries[i][3],
            'longitude': entries[i][4],
            'analytics': entries[i][5],
            'server_ip': entries[i][6],
            'cam_index': entries[i][7]
        }
        servers.append(entries[i][6])

    conf_data['servers'] = list(set(servers))
    # log.info(conf_data)
    NUM_CH, CONF_DATA = num_ch, conf_data
    grafana_connect = GrafanaConnect(GRAFANA_URL, MAP_SERVER_URL, INFLUXDB_URL, 'admin', GRAFANA_PASSWORD)
    URL_DATA = grafana_connect.init_grafana_server(CONF_DATA, 'grafana_templates/datasource_template.json',
                                                  'grafana_templates/consolidated_dashboard_template.json',
                                                  'grafana_templates/channel_dashboard_template.json')
    if URL_DATA == -1:
       sys.exit(-1)


def main():
    """
    Main Function
    """
    global GRAFANA_URL, MAP_SERVER_URL, GRAFANA_EXTERNAL_URL

    GRAFANA_URL = f'http://{GRAFANA_HOST}:{GRAFANA_PORT}'
    MAP_SERVER_URL = f'https://{HOST_IP}:{os.getenv("SERVER_PORT")}'
    GRAFANA_EXTERNAL_URL = f'https://{HOST_IP}:32000'
    log.info("MAP SERVER URL %s " % MAP_SERVER_URL)
    log.info("GRAFANA_URL %s " % GRAFANA_URL)
    log.info("GRAFANA_EXTERNAL_URL %s" % GRAFANA_EXTERNAL_URL)

    # allow service time to start and add the entries into the database
    init_all(over_write=True)

    try:
        app.run(host=LOCAL_HOST, port=LOCAL_PORT, threaded=False, ssl_context=('/app/itm.pem', '/app/itm-key.pem'))
    except KeyboardInterrupt:
        process.terminate()


if __name__=='__main__':
    main()
