import os, struct, subprocess
from io import BufferedReader

if "FLATC_PATH" in os.environ:
  FLATC_PATH = os.environ["FLATC_PATH"]
else:
  FLATC_PATH = "PATH TO FLATC.EXE HERE"


def readbyte(file: BufferedReader) -> int:
    return int.from_bytes(file.read(1), byteorder="little")


def readshort(file: BufferedReader) -> int:
    return int.from_bytes(file.read(2), byteorder="little")


def readlong(file: BufferedReader) -> int:  # SIGNED!!!!
    bytes_data = file.read(4)
    # print(f"readlong: {bytes_data}")
    return int.from_bytes(bytes_data, byteorder="little", signed=True)


def readfloat(file: BufferedReader) -> float:
    return struct.unpack("<f", file.read(4))[0]


def readhalffloat(file: BufferedReader) -> float:
    return struct.unpack("<e", file.read(2))[0]


def readfixedstring(file, length) -> str:
    bytes_data = file.read(length)
    # print(f"readfixedstring ({length}): {bytes_data}")
    return bytes_data.decode("utf-8")


def fseek(file, offset) -> None:
    # print(f"Seeking to {offset}")
    file.seek(offset)


def ftell(file: BufferedReader) -> int:
    return file.tell()


def fclose(file: BufferedReader) -> None:
    file.close()

    
def to_binary(filepath, fileext) -> None:
    filetype = fileext.strip(".")
    schema_dir = os.path.dirname(FLATC_PATH) + f"\\Schemas\\Filetypes\\{filetype}.fbs"
    output_folder = os.path.dirname(filepath) + "\\Modded\\"
    
    if not os.path.exists(output_folder):
      os.makedirs(output_folder)

    flatc_call = [
        FLATC_PATH,
        "--filename-ext",
        filetype,
        "-o",
        output_folder,
        "-b",
        schema_dir,
        filepath,
    ]
    print(flatc_call)
    result = subprocess.run(flatc_call, check=True)
    
    if isinstance(result, subprocess.CalledProcessError):
        print(f"Failed to convert '{filepath}' to binary.")
        print(result.stdout)
    else:
        output_file = os.path.realpath(
        output_folder +
        os.path.basename(filepath).strip(".json") +
        fileext 
        )
        if os.path.exists(output_file):
            rename_call = ["powershell.exe", "-Command", 
            f"Move-Item '{output_file}' '{output_file.removesuffix(fileext)}' -Force"]
            result2 = subprocess.run(rename_call, check=True)
            if isinstance(result, subprocess.CalledProcessError):
                print(f"Failed to rename binary.")
                print(result2.stdout)
        print(f"Successfully converted '{filepath}' to binary.")
