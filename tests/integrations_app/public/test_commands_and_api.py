import os
from subprocess import Popen
from time import sleep

import pytest
import requests
from integrations_app.public import _PATH_EXAMPLES

from lightning_app.testing.testing import run_app_in_cloud
from lightning_app.utilities.cloud import _get_project
from lightning_app.utilities.network import LightningClient


@pytest.mark.timeout(300)
@pytest.mark.cloud
def test_commands_and_api_example_cloud() -> None:
    with run_app_in_cloud(os.path.join(_PATH_EXAMPLES, "app_commands_and_api")) as (
        admin_page,
        _,
        fetch_logs,
        _,
    ):
        # 1: Collect the app_id
        app_id = admin_page.url.split("/")[-1]

        # 2: Connect to the App and send the first & second command with the client
        # Requires to be run within the same process.
        cmd_1 = f"python -m lightning connect {app_id}"
        cmd_2 = "python -m lightning command with client --name=this"
        cmd_3 = "python -m lightning command without client --name=is"
        cmd_4 = "lightning disconnect"
        process = Popen(" && ".join([cmd_1, cmd_2, cmd_3, cmd_4]), shell=True)
        process.wait()

        # This prevents some flakyness in the CI. Couldn't reproduce it locally.
        sleep(5)

        # 5: Send a request to the Rest API directly.
        client = LightningClient()
        project = _get_project(client)

        lit_apps = [
            app
            for app in client.lightningapp_instance_service_list_lightningapp_instances(
                project_id=project.project_id
            ).lightningapps
            if app.id == app_id
        ]
        app = lit_apps[0]

        base_url = app.status.url
        resp = requests.post(base_url + "/user/command_without_client?name=awesome")
        assert resp.status_code == 200, resp.json()

        # 6: Validate the logs.
        has_logs = False
        while not has_logs:
            for log in fetch_logs():
                if "['this', 'is', 'awesome']" in log:
                    has_logs = True
            sleep(1)

        # 7: Send a request to the Rest API directly.
        resp = requests.get(base_url + "/pure_function")
        assert resp.status_code == 200
        assert resp.json() == "Hello World !"
