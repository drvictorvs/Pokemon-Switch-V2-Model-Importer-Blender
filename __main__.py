from io_pknx.ImportTRMDL import from_trmdl_scvi, from_trmdl_pla

filep = "C:\\Users\\victor.vasconcelos\\OneDrive\\Games\\Modding\\Scarlet\\Taller\\p0_hrs1010_halfup\\"
trmdl = open(filep + "p0_hrs1010_00_hrs00.trmdl", "rb")
settings = {
            "rare": False,
            "loadlods": False,
            "bonestructh": True,
            }

exception = None

from_trmdl_pla(filep, trmdl, settings)


filep = "C:\\Users\\victor.vasconcelos\\OneDrive\\Games\\Modding\\Scarlet\\Taller\\p0_hrs1010_halfup\\"
trmdl = open(filep + "p0_hrs1010_00_hrs00.trmdl", "rb")
settings = {
            "rare": False,
            "loadlods": False,
            "bonestructh": True,
            "basearmature": "None",
            }

exception = None
from_trmdl_scvi(filep, trmdl, settings)