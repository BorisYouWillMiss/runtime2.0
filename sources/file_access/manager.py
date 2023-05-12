
import io
import os
import errno
import shutil

from collections import deque
from threading import RLock
from tempfile import mkdtemp, NamedTemporaryFile, _TemporaryFileWrapper
from glob import glob

import settings
import file_access

from utils.system import *
from utils.mutex import VDOM_named_mutex
from utils.tracing import format_exception_trace
# from utils.file_argument import Attachment

from .auxiliary import cleanup_directory
from .daemon import FileWriter

from minio import Minio

TEMPORARY_DIRECTORY_SUFFIX = "-temporary"
NO_DEFAULT = "NO DEFAULT"


class FileManager(object):

    def __init__(self):
        self._lock = RLock()
        self._queue = deque()
        self._daemon = None

    # threading

    def start_daemon(self):
        if self._daemon is None:
            self._daemon = FileWriter(self)
            self._daemon.start()
        return self._daemon

    def work(self):
        with self._lock:
            queries = tuple(self._queue)
            self._queue.clear()
        for arguments in queries:
            try:
                self.write(*arguments)
            except:
                log.error("Unable to save %s, details below\n%s" %
                    (self.locate(arguments[:3]), format_exception_trace(locals=True, separate=True)))

    # locations

    def locate(self, category=None, owner=None, name=None, *arguments):
        if category is None:
            assert owner is None
            segments = (name,) + arguments
        elif category == file_access.APPLICATION:
            # VDOM_CONFIG["FILE-ACCESS-DIRECTORY"] / application_path="applications" / application_id / application_file_name="app.xml"
            segments = (settings.APPLICATIONS_LOCATION, owner, name) + arguments
        elif category == file_access.TYPE:
            # VDOM_CONFIG["FILE-ACCESS-DIRECTORY"] / global_types_path="types" / object_name
            segments = (settings.TYPES_LOCATION, owner, name) + arguments
        elif category == file_access.RESOURCE:
            # VDOM_CONFIG["FILE-ACCESS-DIRECTORY"] / resources_path="resources" / owner_id / object_name
            # VDOM_CONFIG["FILE-ACCESS-DIRECTORY"] / resources_path="resources"
            segments = settings.RESOURCES_LOCATION, owner, name
        elif category == file_access.DATABASE:
            # VDOM_CONFIG["FILE-ACCESS-DIRECTORY"] / databases_path="databases" / owner / object_name
            # VDOM_CONFIG["FILE-ACCESS-DIRECTORY"] / databases_path="databases"
            segments = settings.DATABASES_LOCATION, owner, name
        elif category == file_access.MODULE:
            assert owner is not None
            # VDOM_CONFIG["FILE-ACCESS-DIRECTORY"] / type_source_path="objects" / object_name
            # segments = settings.MODULES_LOCATION, name
            segments = settings.TYPES_LOCATION, owner, name
        elif category == file_access.LIBRARY:
            assert owner is not None
            assert not arguments
            # segments = settings.LIBRARIES_LOCATION, owner, name
            segments = settings.APPLICATIONS_LOCATION, owner, settings.APPLICATION_LIBRARIES_DIRECTORY, name
        elif category == file_access.STORAGE:
            # VDOM_CONFIG["FILE-STORAGE-DIRECTORY"] / application_id / file_name
            # VDOM_CONFIG["FILE-STORAGE-DIRECTORY"] / application_id
            segments = settings.STORAGE_LOCATION, owner, name
        elif category == file_access.CACHE:
            # VDOM_CONFIG["FILE-ACCESS-DIRECTORY"] / application_path="applications" / application_id / py_files_cache="cache" / object_name
            segments = settings.CACHE_LOCATION, owner, name
        # elif category == file_access.CERTIFICATE:
        #     # VDOM_CONFIG["FILE-ACCESS-DIRECTORY"] / certificates="cert" / file_name
        #     assert owner is None
        #     segments = settings.CERTIFICATES_LOCATION, name
        # elif category == file_access.LOG:
        #     # VDOM_CONFIG["FILE-ACCESS-DIRECTORY"] / certificates="cert" / file_name
        #     assert owner is None
        #     segments = settings.LOGS_LOCATION, name
        elif category == file_access.TEMPORARY:
            segments = settings.TEMPORARY_LOCATION, owner, name
        else:
            raise Exception("Unknown category: %r" % category)
        return os.path.normpath(os.path.join(*filter(None, segments))).decode('utf-8')

    def ensure(self, category, owner, mode, name=None):
        if "w" not in mode:
            return
        if category in (file_access.RESOURCE, file_access.DATABASE, file_access.STORAGE, file_access.CACHE):
            location = self.locate(category, owner)
            if not os.path.isdir(location):
                try:
                    os.makedirs(location)
                except Exception as error:
                    print "Ensure %s directory error: %s" % (location, error)

    # elementary

    def list(self, category=None, owner=None, name=None, pattern=None):
        location = self.locate(category, owner, name)
        if pattern:
            try:
                return glob(location + "/" + pattern)
            except Exception as error:
                print "List storage %s and pattern %s directory error: %s" % (location, pattern, error)
        else:
            try:
                return os.listdir(location)
            except Exception as error:
                print "List storage %s directory error: %s" % (location, error)

    def exists(self, category, owner=None, name=None):
        location = self.locate(category, owner, name)
        return os.path.exists(location)

    def rename(self, category, owner, name, new_name):
        location = self.locate(category, owner, name)
        new_location = self.locate(category, owner, new_name)
        os.rename(location, new_location)

    def open(self, category, owner, name, mode="r", buffering=-1, encoding=None, errors=None, newline=""):
        location = self.locate(category, owner, name)
        # self.ensure(category, owner, mode)
        return io.open(location, mode, buffering, encoding, errors, None if "b" in mode else newline)

    def open_temporary(self, category, owner, mode="w+b", buffering=-1, encoding=None, suffix="", prefix="", delete=True):
        if category is not None:
            raise Exception("Unable to create temporary non-file resource")
        if encoding is not None:
            raise Exception("Unable to create temporary file with encoding")
        return NamedTemporaryFile(mode=mode, bufsize=buffering, suffix=suffix, prefix=prefix,
            dir=os.path.abspath(settings.TEMPORARY_LOCATION), delete=delete)

    def size(self, category, owner, name):
        try:
            return os.path.getsize(self.locate(category, owner, name))
        except os.error:
            return None

    def read(self, category, owner, name, encoding=None, default=NO_DEFAULT):
        location = self.locate(category, owner, name)
        mode = "r" if encoding else "rb"
        try:
            with io.open(location, mode, encoding=encoding, newline=None if "b" in mode else "") as file:
                return file.read()
        except Exception as error:
            if error.errno == errno.ENOENT and default is not NO_DEFAULT:
                return default
            else:
                raise

    def write(self, category, owner, name, data=None, encoding=None, async=False, safely=False):
        if async:
            with self._lock:
                self._queue.append((category, owner, name, data, encoding, False, safely))
                if self._daemon is None:
                    self.start_daemon()
        else:
            location = self.locate(category, owner, name)
            location_dir = os.path.dirname(location)
            if not os.path.exists(location_dir):
                os.makedirs(location_dir)
            mode = "w" if encoding else "wb"
            # self.ensure(category, owner, mode)
            with VDOM_named_mutex(location):
                if isinstance(data, Attachment):
                    if data._get_realpath():
                        if not data.handler.closed:
                            data.handler.close()
                        try:
                            shutil.move(data._get_realpath(), location)
                        except OSError as e:
                            print (u"Attachment save error: %s"%e)
                            try: 
                                os.remove(location)
                            except OSError as e:
                                print (u"Target removal error: %s"%e)
                            shutil.move(data._get_realpath(), location)
                        data._del_fileobj()
                        return
                    else:
                        data = data.handler
                elif isinstance(data, _TemporaryFileWrapper): #TODO: This dirty hack possible not work on 2.7.11 or later
                    if not data.closed:
                        data.close()
                    try:
                        shutil.move(data.name, location)
                    except OSError as e:
                        print (u"Attachment save error: %s"%e)
                        try:
                            os.remove(location)
                        except OSError as e:
                            print (u"Target removal error: %s"%e)
                        shutil.move(data.name, location)
                    return
                if safely:
                    proper_location, location = location, location + ".temporary"
                with io.open(location, mode, encoding=encoding, newline=None if "b" in mode else "") as file:
                    if hasattr(data, "read"):
                        shutil.copyfileobj(data, file)
                    else:
                        file.write(data)
                if safely:
                    shutil.move(location, proper_location)

    def delete(self, category, owner, name):
        location = self.locate(category, owner, name)
        with VDOM_named_mutex(location):
            try:
                os.remove(location)
            except Exception as error:
                if error.errno != errno.ENOENT:
                    print "Delete %s file error: %s" % (location, error)

    # directories

    def prepare_directory(self, category, owner, name=None, cleanup=True):
        location = self.locate(category, owner, name)
        try:
            if os.path.isdir(location):
                if cleanup:
                    cleanup_directory(location, ignore_errors=True)
            else:
                os.makedirs(location)
        except Exception as error:
            print "Prepare %s directory error: %s" % (location, error)

    def cleanup_directory(self, category, owner, remove=False):
        location = self.locate(category, owner)
        try:
            if os.path.isdir(location):
                cleanup_directory(location, ignore_errors=True, remove=remove)
            elif os.path.exists(location):
                raise Exception("Unable to cleanup non-directory: %s" % location)
        except Exception as error:
            print "Cleanup %s directory error: %s" % (location, error)

    def create_temporary_directory(self, prefix=""):
        return mkdtemp(TEMPORARY_DIRECTORY_SUFFIX, prefix, dir=settings.TEMPORARY_LOCATION)

    def delete_temporary_directory(self, name):
        relative = os.path.relpath(os.path.normpath(name), os.path.abspath(settings.TEMPORARY_LOCATION))
        if relative.find('/') >= 0 or relative.find('\\') >= 0:
            raise VDOM_exception_file_access("Provided file name is invalid")
        shutil.rmtree(name)

    # storage

    def create_storage_directory(self, owner, folder_name):
        location = self.locate(file_access.STORAGE, owner, folder_name)
        try:
            os.makedirs(location)
        except Exception as error:
            print "Create storage %s directory error: %s" % (location, error)

    def list_storage_directory(self, owner, folder_name):
        location = self.locate(file_access.STORAGE, owner, folder_name)
        try:
            return os.listdir(location)
        except Exception as error:
            print "List storage %s directory error: %s" % (location, error)

    def delete_storage_directory(self, owner, folder_name):
        location = self.locate(file_access.STORAGE, owner, folder_name)
        try:
            shutil.rmtree(location)
        except Exception as error:
            print "Delete storage %s directory error: %s" % (location, error)

    # libraries

    def write_library(self, owner, name, data):
        # fname = os.path.join(VDOM_CONFIG["LIB-DIRECTORY"], appid, libname + ".py")
        self.write(file_access.LIBRARY, owner, name, data, encoding="utf-8")

    def delete_library(self, owner, name):
        # fname = os.path.join(VDOM_CONFIG["LIB-DIRECTORY"], appid, libname + ".py")
        # self.cleanup_directory(file_access.LIBRARY, owner)
        self.delete(file_access.LIBRARY, owner, name)
        # try:
        #     os.remove(fname)
        # except:
        #     pass
        # try:
        #     os.remove(fname + "c")
        # except:
        #     pass


VDOM_file_manager = FileManager
