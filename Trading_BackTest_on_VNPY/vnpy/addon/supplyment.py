
import logging
import os
import json
from vnpy.trader.utility import get_folder_path


class ConfigManager:
    """
    配置管理类
    """
    def __init__(self, default_path = None):
        """
        构造函数

        :param default_path: 可选的默认路径
        """
        if default_path:
            self.default_path = default_path
        else:
            self.default_path = get_folder_path("ZhuLiQieHuan")

    def build_path(self, config_name):
        """
        构建配置文件路径

        :param config_name: 配置名称
        :return: 配置文件路径
        """
        return os.path.join(self.default_path, config_name)

    def read_config(self, config_name):
        """
        读取配置

        :param config_name: 配置名称
        :return: 配置数据（字典）
        """
        default_config_path = self.build_path(config_name)
        # 如果默认路径下存在配置文件
        if os.path.exists(default_config_path):
            with open(default_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 假设已处理运行时环境中的相对路径
        default_config_path = config_name
        # 如果相对路径下存在配置文件
        if os.path.exists(default_config_path):
            with open(default_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 如果都找不到，创建一个空的 JSON 文件并返回空字典
        self.create_empty_config(config_name)
        return {}

    def create_empty_config(self, config_name):
        """
        创建空配置文件

        :param config_name: 配置名称
        """
        default_config_path = self.build_path(config_name)
        empty_data = {}
        with open(default_config_path, 'w', encoding='utf-8') as f:
            json.dump(empty_data, f, indent=4)  # 使用 4 个空格缩进

    def write_config(self, config_name, config_data):
        """
        写入配置

        :param config_name: 配置名称
        :param config_data: 配置数据
        """
        default_config_path = self.build_path(config_name)
        # 如果不存在该配置文件则创建
        if not os.path.exists(default_config_path):
            self.create_empty_config(config_name)
        with open(default_config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)  # 使用 4 个空格缩进

    def define_logger(self, logger_name, log_filename):
        """
        定义日志记录器

        :param logger_name: 日志记录器名称
        :param log_filename: 日志文件名
        :return: 日志记录器对象
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(level=logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        file_handler = logging.FileHandler(
            log_filename, mode="a", encoding="utf8"
        )
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        return logger
