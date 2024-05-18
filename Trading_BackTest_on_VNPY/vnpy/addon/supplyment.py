import json
import os
import logging
from vnpy.trader.utility import get_folder_path

class ConfigManager:
    def __init__(self, default_path = None):
        if default_path:
            self.default_path = default_path
        else:
            self.default_path = get_folder_path("ZhuLiQieHuan")

    def build_path(self, config_name):
        return os.path.join(self.default_path, config_name)

    def read_config(self, config_name):
        default_config_path = self.build_path(config_name)
        if os.path.exists(default_config_path):
            with open(default_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 运行时环境中的相对路径假设已处理
        default_config_path = config_name
        if os.path.exists(default_config_path):
            with open(default_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 如果都找不到，创建一个空的 JSON 文件并返回空字典
        self.create_empty_config(config_name)
        return {}

    def create_empty_config(self, config_name):
        default_config_path = self.build_path(config_name)
        empty_data = {}
        with open(default_config_path, 'w', encoding='utf-8') as f:
            json.dump(empty_data, f, indent=4)  # 使用 4 个空格缩进

    def write_config(self, config_name, config_data):
        default_config_path = self.build_path(config_name)
        if not os.path.exists(default_config_path):
            self.create_empty_config(config_name)
        with open(default_config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)  # 使用 4 个空格缩进

    def define_logger(self, logger_name, log_filename):
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

