import importlib.util
import logging
import os
from shutil import copyfile
from urllib.parse import urlencode

from .. import entities, repositories, exceptions, miscellaneous, assets

logger = logging.getLogger(name=__name__)


class Models:
    """
    Models Repository
    """

    def __init__(self, client_api, project=None):
        self._client_api = client_api
        self._project = project

    ############
    # entities #
    ############
    @property
    def project(self):
        if self._project is None:
            try:
                self._project = repositories.Projects(client_api=self._client_api).get()
            except exceptions.NotFound:
                raise exceptions.PlatformException(
                    error='2001',
                    message='Missing "project". need to set a Project entity or use project.models repository')
        return self._project

    @project.setter
    def project(self, project):
        if not isinstance(project, entities.Project):
            raise ValueError('Must input a valid Project entity')
        self._project = project

    ###########
    # methods #
    ###########
    def get(self, model_name=None, model_id=None, checkout=False, fetch=None):
        """
        Get model object

        :param checkout:
        :param model_id:
        :param model_name:
        :param fetch: optional - fetch entity from platform, default taken from cookie
        :return: model object
        """
        if fetch is None:
            fetch = self._client_api.fetch_entities

        if model_name is None and model_id is None:
            model = self.__get_from_cache()
            if model is None:
                raise exceptions.PlatformException(
                    error='400',
                    message='Checked out not found, must provide either model id or model name')
        elif fetch:
            if model_id is not None:
                success, response = self._client_api.gen_request(
                    req_type="get",
                    path="/models/{}".format(model_id))
                if not success:
                    raise exceptions.PlatformException(response)
                model = entities.Model.from_json(client_api=self._client_api,
                                                 _json=response.json(),
                                                 project=self._project)
            elif model_name is not None:
                models = self.list(name=model_name)
                if len(models) == 0:
                    raise exceptions.PlatformException(
                        error='404',
                        message='Model not found. Name: {}'.format(model_name))
                elif len(models) > 1:
                    raise exceptions.PlatformException(
                        error='400',
                        message='More than one file found by the name of: {}'.format(model_name))
                model = models[0]
            else:
                raise exceptions.PlatformException(
                    error='400',
                    message='Checked out not found, must provide either model id or model name')
        else:
            model = entities.Model.from_json(_json={'id': model_id,
                                                    'name': model_name},
                                             client_api=self._client_api,
                                             project=self._project,
                                             is_fetched=False)

        if checkout:
            self.checkout(model=model)
        return model

    def list(self, name=None, creator=None):
        """
        List project models
        :return:
        """
        url = '/models'
        query_params = {
            'name': name,
            'creator': creator
        }

        if self._project is not None:
            query_params['projects'] = self._project.id

        url += '?{}'.format(urlencode({key: val for key, val in query_params.items() if val is not None}, doseq=True))

        # request
        success, response = self._client_api.gen_request(req_type='get',
                                                         path=url)
        if not success:
            raise exceptions.PlatformException(response)

        # return models list
        models = miscellaneous.List()
        for model in response.json()['items']:
            models.append(entities.Model.from_json(client_api=self._client_api,
                                                   _json=model,
                                                   project=self._project))
        return models

    def build(self, model, local_path=None, from_local=None):
        """
        :param model: Model entity
        :param from_local: bool. use current directory to build
        :param local_path: local path of the model (if from_local=False - codebase will be downloaded)

        :return:
        """
        if from_local is None:
            from_local = False

        if from_local:
            # no need to download codebase
            if local_path is None:
                path = os.getcwd()
            else:
                path = local_path

        else:
            # download codebase locally
            if local_path is None:
                local_path = os.path.join(
                    os.path.expanduser("~"),
                    ".dataloop",
                    "models",
                    model.name)

            codebase_id = model.codebase_id
            path = self._project.codebases.unpack(codebase_id=codebase_id, local_path=local_path)

        # load module from path
        entry_point = os.path.join(path, model.entry_point)
        spec = importlib.util.spec_from_file_location("AdapterModel", entry_point)
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)
        adapter_model = foo.AdapterModel
        return adapter_model()

    def push(self, model_name, description='', src_path=None, entry_point='adapter_model.py', codebase_id=None,
             checkout=False):
        """
        Push local model

        :param model_name: name of the model
        :param description: model description
        :param entry_point: location on the AdapterModel class
        :param codebase_id: codebase entity id. if none new will be created from src_path
        :param src_path: codebase location. if None pwd will be taken
        :param checkout: checkout entity to state
        :return:
        """
        # get project
        if self._project is None:
            raise exceptions.PlatformException('400', 'Repository does not have project. Please checkout a project,'
                                                      'or create model from a project models repository')

        # source path
        if src_path is None:
            if codebase_id is None:
                src_path = os.getcwd()
                logger.warning('No src_path is given, getting model information from cwd: {}'.format(src_path))

        # get or create codebase
        if codebase_id is None:
            codebase_id = self._project.codebases.pack(directory=src_path, name=model_name).id

        if not os.path.isfile(os.path.join(src_path, entry_point)):
            raise ValueError('entry point not found. filepath: {}'.format(os.path.join(src_path, entry_point)))
        # check if exist
        models = [model for model in self.list() if model.name == model_name]
        if len(models) > 0:
            model = self._create(codebase_id=codebase_id,
                                 model_name=model_name,
                                 description=description,
                                 entry_point=entry_point,
                                 push=True,
                                 model=models[0])
        else:
            model = self._create(codebase_id=codebase_id,
                                 entry_point=entry_point,
                                 description=description,
                                 model_name=model_name,
                                 push=False)
        if checkout:
            self.checkout(model=model)
        return model

    def _create(self,
                model_name,
                entry_point,
                description='',
                codebase_id=None,
                push=False,
                model=None):
        """
        Create a model in platform

        :param model:
        :param description: model description
        :param entry_point: location on the AdapterModel class
        :param codebase_id: optional - model codebase
        :param model_name: optional - default: 'default model'
        :param push:
        :return: Model Entity
        """
        if push:
            model.codebase_id = codebase_id
            return self.update(model=model)

        payload = {'name': model_name,
                   'codebaseId': codebase_id,
                   'entryPoint': entry_point,
                   'description': description}

        if self._project is not None:
            payload['projectId'] = self._project.id
        else:
            raise exceptions.PlatformException('400', 'Repository must have a project to perform this action')

        # request
        success, response = self._client_api.gen_request(req_type='post',
                                                         path='/models',
                                                         json_req=payload)

        # exception handling
        if not success:
            raise exceptions.PlatformException(response)

        # return entity
        return entities.Model.from_json(_json=response.json(),
                                        client_api=self._client_api,
                                        project=self._project)

    def delete(self, model=None, model_name=None, model_id=None):
        """
        Delete Model object

        :param model:
        :param model_name:
        :param model_id:
        :return: True
        """
        # get id and name
        if model_name is None or model_id is None:
            if model is None:
                model = self.get(model_id=model_id, model_name=model_name)
            model_id = model.id

        # request
        success, response = self._client_api.gen_request(
            req_type="delete",
            path="/models/{}".format(model_id)
        )

        # exception handling
        if not success:
            raise exceptions.PlatformException(response)

        # return results
        return True

    def update(self, model):
        """
        Update Model changes to platform

        :param model:
        :return: Model entity
        """
        assert isinstance(model, entities.Model)

        # payload
        payload = model.to_json()

        # request
        success, response = self._client_api.gen_request(req_type='patch',
                                                         path='/models/{}'.format(model.id),
                                                         json_req=payload)

        # exception handling
        if not success:
            raise exceptions.PlatformException(response)

        # return entity
        return entities.Model.from_json(_json=response.json(),
                                        client_api=self._client_api,
                                        project=self._project)

    @staticmethod
    def generate(src_path=None):
        """
        Generate new model environment

        :return:
        """
        # src path
        if src_path is None:
            src_path = os.getcwd()
        if not os.path.isfile(os.path.join(src_path, '.gitignore')):
            copyfile(assets.paths.ASSETS_GITIGNORE_FILEPATH, os.path.join(src_path, '.gitignore'))
        copyfile(assets.paths.ASSETS_ADAPTER_MODEL_FILEPATH, os.path.join(src_path, assets.paths.ADAPTER_MODEL))
        logger.info('Successfully generated model')

    def __get_from_cache(self):
        model = self._client_api.state_io.get('model')
        if model is not None:
            model = entities.Model.from_json(_json=model, client_api=self._client_api, project=self._project)
        return model

    def checkout(self, model=None, model_id=None, model_name=None):
        """
        Checkout as model

        :param model_id:
        :param model:
        :param model_name:
        :return:
        """
        if model is None:
            model = self.get(model_id=model_id, model_name=model_name)
        self._client_api.state_io.put('model', model.to_json())
        logger.info("Checked out to model {}".format(model.name))
