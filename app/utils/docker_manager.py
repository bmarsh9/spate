import docker
import json
import io
import tarfile
import os

class DockerManager():
    def __init__(self,timeout=10):
        self.client = docker.from_env(timeout=timeout)

    def list_images(self):
        return self.client.images.list()

    def list_containers(self):
        return self.client.containers.list()

    def get_container(self,id,to_json=False):
        data = {}
        attrs = ['Id', 'Created', 'Path', 'Args', 'State', 'Image',
          'Name', 'RestartCount', 'Driver', 'Platform', 'MountLabel',
          'ProcessLabel', 'ExecIDs', 'HostConfig', 'Mounts', 'Config',
          'NetworkSettings']
        try:
            container = self.client.containers.get(id)
        except:
            container = None
        if not to_json:
            return container
        if container:
            for attr in attrs:
                data[attr] = container.attrs[attr]
        return data

    def get_image(self,id,to_json=False):
        data = {}
        attrs = ['Id', 'RepoTags', 'RepoDigests', 'Parent',
          'Comment', 'Created', 'Container', 'ContainerConfig',
          'DockerVersion', 'Author', 'Config', 'Architecture',
          'Os', 'Size', 'VirtualSize', 'Metadata']
        try:
            image = self.client.images.get(id)
            if not to_json:
                return image
            if image:
                for attr in attrs:
                    data[attr] = image.attrs[attr]
                data["Name"] = image.attrs["RepoTags"][-1]
        except docker.errors.ImageNotFound:
            pass
        return data

    def get_id_for_image(self,name):
        return self.get_image(name).short_id

    def find_container_by_workflow_name(self,name):
        '''search for workflow_name key set on the
        container labels
        '''
        for container in self.list_containers():
            if container.labels.get("workflow_name","") == name:
                return container
        return None

    def get_logs(self,id):
        return self.get_container(id).logs()

    def pull_image(self,name):
        return self.client.images.pull(name)

    def stop_container(self,id):
        return self.get_container(id).stop()

    def stop_all_containers(self):
        for container in self.list_containers():
            return self.get_container(container.short_id).stop()
        return True

    def run_container(self,image,host_volume_path=None,bind_path="/app/workflow",**kwargs):
        volume_dict = {}
        if host_volume_path:
            volume_dict = {host_volume_path: {"bind": bind_path, "mode": "rw"}}
        if volume_dict:
            kwargs["volumes"] = volume_dict
        if "detach" not in kwargs:
            kwargs["detach"] = True
        return self.client.containers.run(image, **kwargs)

    def exec_to_container(self,name,command,env={},format=True,output="log",detach=False):
        '''
        execute command within running container
        if format is True, it loads the response as a JSON
        object and returns the result
        '''
        result = self.get_container(name).exec_run(command,environment=env,detach=detach)
#        if format and not detach:
#            return self.format_output_from_exec(result,output=output)
        return result

    def list_volumes(self):
        return self.client.volumes.list()

    def get_volume(self,id):
        return self.client.volumes.get(id)

    def create_volume(self,name=None):
        if name:
            return self.client.volumes.create(name=name)
        return self.client.volumes.create()

    def remove_volume(self,id):
        return self.get_volume(id).remove()

    def start_base_container(self):
        '''
        start a base container to get it running, mount volumes, etc.
        and then we can run exec_to_container and run code against it
        '''
        pass

    def format_output_from_exec(self,result,output="log"):
        if output == "json":
            return json.loads(result.output.decode("utf-8"))
        elif output == "list":
            return result.output.decode("utf-8").split("\n")
        return result.output.decode("utf-8")

    def copy_to(self, container, src, dst):
        container.exec_run("rm -r /app/workflow/tmp",detach=False)
        os.chdir(os.path.dirname(src))
        srcname = os.path.basename(src)
        tar = tarfile.open(src + '.tar', mode='w')
        try:
            tar.add(srcname)
        finally:
            tar.close()
        data = open(src + '.tar', 'rb').read()
        container.put_archive(dst, data)
        return True
