from mavpy.base import Maven


class Maven3(Maven):
    def __init__(self, bin_path):
        super().__init__(bin_path)