from io_pknx.ImportTRMDL import from_trmdl_scvi, from_trmdl_pla

filep = ".\\tests"
trmdl = open(filep + "p0_hrs1010_00_hrs00.trmdl", "rb")
settings = {
            "rare": False,
            "loadlods": False,
            "bonestructh": True,
            }

exception = None

from_trmdl_pla(".\\tests", open(filep + "p0_hrs1010_00_hrs00.trmdl", "rb"), settings)


filep = ".\\tests"
trmdl = open(filep + "p0_hrs1010_00_hrs00.trmdl", "rb")
settings = {
            "rare": False,
            "loadlods": False,
            "bonestructh": True,
            "basearmature": "None",
            }

exception = None
from_trmdl_scvi(filep, trmdl, settings)