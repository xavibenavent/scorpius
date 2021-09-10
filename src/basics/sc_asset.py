# sc_asset.py


class Asset:
    def __init__(self,
                 name: str,
                 pv: int  # precision for visualization
                 ):
        self._name = name.upper()
        self._pv = pv

    def name(self) -> str:
        return self._name

    def pv(self) -> int:
        return self._pv
