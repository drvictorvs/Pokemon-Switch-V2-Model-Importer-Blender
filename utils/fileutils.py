import struct


def readbyte(file):
    return int.from_bytes(file.read(1), byteorder="little")


def readshort(file):
    return int.from_bytes(file.read(2), byteorder="little")


def readlong(file):  # SIGNED!!!!
    bytes_data = file.read(4)
    # print(f"readlong: {bytes_data}")
    return int.from_bytes(bytes_data, byteorder="little", signed=True)


def readfloat(file):
    return struct.unpack("<f", file.read(4))[0]


def readhalffloat(file):
    return struct.unpack("<e", file.read(2))[0]


def readfixedstring(file, length):
    bytes_data = file.read(length)
    # print(f"readfixedstring ({length}): {bytes_data}")
    return bytes_data.decode("utf-8")


def fseek(file, offset):
    # print(f"Seeking to {offset}")
    file.seek(offset)


def ftell(file):
    return file.tell()


def fclose(file):
    file.close()