"""
Project Rest Implementation - Harvester (Rancher Steve) REST API operations
Uses get_harvester_api_client() for every call.
"""
import time
from datetime import datetime, timedelta

from utility.utility import (
    logging, get_harvester_api_client, get_retry_count_and_interval
)
from constant import (
    LOCAL_CLUSTER_ID, LABEL_TEST, LABEL_TEST_VALUE, DEFAULT_TIMEOUT,
)
from project.base import Base

PROJECTS_PATH = "v1/management.cattle.io.projects"
PROJECT_TYPE = "management.cattle.io.project"


class Rest(Base):
    """Project Rest implementation - makes actual API calls"""

    def __init__(self):
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    @property
    def api(self):
        return get_harvester_api_client()

    @staticmethod
    def _message(data):
        if isinstance(data, dict):
            return data.get("message") or str(data)
        return str(data)

    def create(self, display_name, cpu_limit=None, memory_limit=None,
               ns_default_cpu=None, ns_default_memory=None,
               description=None):
        body = self.build_manifest(
            display_name, cpu_limit, memory_limit,
            ns_default_cpu, ns_default_memory, description
        )
        body["type"] = PROJECT_TYPE

        logging(f"Creating project '{display_name}' via REST "
                f"(cpu={cpu_limit}, memory={memory_limit})")
        code, data = self.api.post(PROJECTS_PATH, data=body)
        assert code in (200, 201), \
            f"Failed to create project '{display_name}': {code}, {data}"

        project_id = data["metadata"]["name"]
        logging(f"Created project '{display_name}': {project_id}")
        return project_id

    def try_create(self, display_name, cpu_limit=None, memory_limit=None,
                   ns_default_cpu=None, ns_default_memory=None):
        body = self.build_manifest(
            display_name, cpu_limit, memory_limit,
            ns_default_cpu, ns_default_memory
        )
        body["type"] = PROJECT_TYPE
        code, data = self.api.post(PROJECTS_PATH, data=body)
        return {"success": code in (200, 201), "code": code,
                "message": "" if code in (200, 201)
                else self._message(data)}

    def list(self, label_selector=None):
        code, data = self.api.get(f"{PROJECTS_PATH}/{LOCAL_CLUSTER_ID}")
        assert code == 200, f"Failed to list projects: {code}, {data}"
        items = data.get("data", [])

        if label_selector:
            key, _, value = label_selector.partition("=")
            items = [i for i in items
                     if i.get("metadata", {}).get("labels", {}).get(key)
                     == value]
        return items

    def get(self, display_name):
        return self.find_by_display_name(self.list(), display_name)

    def get_id(self, display_name):
        project = self.get(display_name)
        if project is None:
            raise AssertionError(f"Project '{display_name}' not found")
        return project["metadata"]["name"]

    def exists(self, display_name):
        try:
            return self.get(display_name) is not None
        except Exception as e:
            logging(f"Error checking project '{display_name}': {e}",
                    'WARNING')
            return False

    def wait_for_active(self, display_name, timeout=DEFAULT_TIMEOUT):
        logging(f"Waiting for project '{display_name}' to be active")
        endtime = datetime.now() + timedelta(seconds=int(timeout))
        project = None
        while endtime > datetime.now():
            try:
                project = self.get(display_name)
                if project and self.is_active(project):
                    logging(f"Project '{display_name}' is active")
                    return project
            except Exception as e:
                logging(f"Error polling project '{display_name}': {e}",
                        'WARNING')
            time.sleep(self.retry_interval)

        state = (project or {}).get("metadata", {}).get("state")
        raise AssertionError(
            f"Project '{display_name}' not active within {timeout}s "
            f"(exists={project is not None}, state={state})"
        )

    def get_resource_limits(self, display_name):
        project = self.get(display_name)
        if project is None:
            raise AssertionError(f"Project '{display_name}' not found")
        return self.extract_limits(project)

    def delete(self, display_name):
        project = self.get(display_name)
        if project is None:
            logging(f"Project '{display_name}' not found, nothing to delete")
            return
        project_id = project["metadata"]["name"]
        logging(f"Deleting project '{display_name}' ({project_id})")
        code, data = self.api.delete(
            f"{PROJECTS_PATH}/{LOCAL_CLUSTER_ID}/{project_id}"
        )
        assert code in (200, 204, 404), \
            f"Failed to delete project '{display_name}': {code}, {data}"

    def try_delete(self, display_name):
        project = self.get(display_name)
        if project is None:
            return {"success": False, "code": 404,
                    "message": f"NotFound: project '{display_name}'"}
        code, data = self.api.delete(
            f"{PROJECTS_PATH}/{LOCAL_CLUSTER_ID}/"
            f"{project['metadata']['name']}"
        )
        return {"success": code in (200, 204), "code": code,
                "message": "" if code in (200, 204)
                else self._message(data)}

    def wait_for_deleted(self, display_name, timeout=DEFAULT_TIMEOUT):
        logging(f"Waiting for project '{display_name}' to be deleted")
        endtime = datetime.now() + timedelta(seconds=int(timeout))
        while endtime > datetime.now():
            if self.get(display_name) is None:
                logging(f"Project '{display_name}' deleted")
                return True
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"Project '{display_name}' still exists after {timeout}s"
        )

    def cleanup(self):
        logging('Cleaning up test projects')
        try:
            projects = self.list(
                label_selector=f"{LABEL_TEST}={LABEL_TEST_VALUE}"
            )
            for project in projects:
                display_name = project["spec"].get("displayName")
                try:
                    logging(f"Deleting test project: {display_name}")
                    self.delete(display_name)
                except Exception as e:
                    logging(f"Error deleting project {display_name}: {e}",
                            'WARNING')
        except Exception as e:
            logging(f"Error during project cleanup: {e}", 'WARNING')
