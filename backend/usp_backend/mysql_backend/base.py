import pymysql

pymysql.install_as_MySQLdb()

from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from django.db.backends.mysql.features import DatabaseFeatures as MySQLDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(MySQLDatabaseFeatures):
    @cached_property
    def minimum_database_version(self):
        if self.connection.mysql_is_mariadb:
            return (10, 4)
        return super().minimum_database_version

    @cached_property
    def can_return_columns_from_insert(self):
        if self.connection.connection is None:
            return False
        if self.connection.mysql_is_mariadb and self.connection.mysql_version < (10, 5):
            return False
        return super().can_return_columns_from_insert

    @cached_property
    def has_native_uuid_field(self):
        if self.connection.connection is None:
            return False
        return super().has_native_uuid_field


class DatabaseWrapper(MySQLDatabaseWrapper):
    features_class = DatabaseFeatures
