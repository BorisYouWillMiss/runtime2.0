import copy
import managers
import file_access
# from storage import storage
# from utils.exception import VDOM_exception
import uuid


class VDOM_resource_descriptor(object):
    def __init__(self, owner_id, res_id=None):
        """constructor"""
        self.application_id = owner_id
        self.id = res_id or str(uuid.uuid4())
        self.__loaded = False

    @classmethod
    def convert(self, resource_object):
        """Convertation from v1.1 to v1.5"""

        assert(isinstance(resource_object, VDOM_resource_object))
        res = VDOM_resource_descriptor(resource_object.application_id, resource_object.id)
        new_res = copy.copy(res)
        new_res.name = resource_object.name if len(resource_object.name) < 80 else "Huge name"  # TODO: check later
        new_res.res_type = resource_object.res_type
        new_res.res_format = resource_object.res_format
        new_res.filename = resource_object.filename
        new_res.save_record()
        return res

    def __load_data(self):
        """Database request to load resource info"""
        # Cleaning fields
        if getattr(self, "object_id", None):
            self.__loaded = True
        else:
            self.object_id = None
            self.use_counting = False
            # self.dependences = {}
            # self.res_type = "permanent"
            # self.res_format = ""
            self.label = ""
            # self.name = ""
            self.showtimes = None
            # Loading from DB
            self.__loaded = True
            # storage.get_resource_record(self)
            managers.storage.get_resource_record(self)  # ?????

    def load_copy(self):
        """Making copy and load it from DB"""
        new_res = copy.copy(self)
        new_res.__load_data()
        return new_res

    def save_record(self):
        """Writing resource record to DB"""
        if not getattr(self, "res_type", None):  # Means it's new
            self.res_type = "permanent"
            self.label = ""
        # storage.save_resource_record(self)
        managers.storage.save_resource_record(self)  # ?????

    def __get_filename(self):
        """Lazy initialisation of filename"""
        fn = getattr(self, "_VDOM_resource_descriptor__filename", None)
        if fn:
            return fn
        else:
            self.__filename = str(uuid.uuid4())
            return self.__filename

    def __set_filename(self, value):
        self.__filename = value

    filename = property(__get_filename, __set_filename)

    def __get_dependences(self):
        return {}
    def __set_dependences(self, value):
        return None
    dependences = property(__get_dependences, __set_dependences)

    def get_data(self):
        if self.__loaded:
            # TODO: Check this...
            # return managers.file_manager.read(file_access.resource,self.application_id,self.object_id,self.filename)
            return managers.file_manager.read(file_access.resource, self.application_id, self.filename)
        else:
            new_res = self.load_copy()
            # return managers.file_manager.read(file_access.resource,new_res.application_id,None,new_res.filename)
            return managers.file_manager.read(file_access.resource, new_res.application_id, new_res.filename)

    def get_fd(self):
        """Reading resource data from HDD"""
        if self.__loaded:
            # TODO: Check this...
            # return managers.file_manager.get_fd(file_access.resource,self.application_id,self.object_id,self.filename)
            return managers.file_manager.open(file_access.resource, self.application_id, self.filename, mode="rb")
        else:
            new_res = self.load_copy()
            # return managers.file_manager.get_fd(file_access.resource,new_res.application_id,None,new_res.filename)
            return managers.file_manager.open(file_access.resource, new_res.application_id, new_res.filename, mode="rb")

    def decrease(self, object_id, remove=False):
        if remove:
            self.__load_data()
            # managers.file_manager.delete(file_access.resource,self.application_id,None,self.filename)
            managers.file_manager.delete(file_access.resource, self.application_id, self.filename)
            managers.storage.delete_resources_index(self)
            return 0
        return 1

    def increase(self, object_id):
        return 1


class VDOM_resource_object:
    """resource object class"""

    def __init__(self, owner_id, object_id, id):
        """constructor"""
        self.application_id = owner_id
        self.use_counting = False
        self.dependences = {}
        self.res_type = "permanent"
        self.res_format = ""
        self.label = ""
        self.id = id
        self.name = ""
        self.filename = str(uuid.uuid4())
        self.showtimes = None