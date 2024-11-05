from construct import (
    BitsInteger,
    BitStruct,
    Bytes,
    GreedyRange,
    Int8ub,
    Int16ub,
    Int32ub,
    Padding,
    Struct,
    this,
)

PacketHeader = BitStruct(
    "VERSION_NUMBER" / BitsInteger(3),
    "PACKET_TYPE" / BitsInteger(1),
    "DFH" / BitsInteger(1),
    "APID" / BitsInteger(11),
    # "PRID" / BitsInteger(7),
    # "PCAT" / BitsInteger(4),
    "GROUP_FLAGS" / BitsInteger(2),
    "SEQUENCE_COUNTER" / BitsInteger(14),
    "PACKET_DATA_FIELD_LENGTH" / BitsInteger(16),
)


DataFieldHeader = BitStruct(
    Padding(1),
    "VERSION_NUMBER" / BitsInteger(3),
    Padding(4),
    "SERVICE_TYPE" / BitsInteger(8),
    "SERVICE_SUB_TYPE" / BitsInteger(8),
    "DESTINATION" / BitsInteger(8),
    "COARSE_TIME" / BitsInteger(32),
    "FINE_TIME" / BitsInteger(16),
)

ScienceHeader = Struct(
    "SESSION_ID" / Int32ub,
    "IMG_COUNT" / Int16ub,
    "PKG_TOTAL" / Int16ub,
    "PKG_COUNT" / Int16ub,
    "VERSION" / Int8ub,
    "IMG_INFO_SIZE" / Int8ub,
    "IMG_INFO" / Bytes(this.IMG_INFO_SIZE),
    "IMG_DATA_LEN1" / Int16ub,
    "CRC_1" / Int8ub,
)

ScienceData = Struct(
    "IMG_DATA" / Bytes(this._.science_header.IMG_DATA_LEN1 - 1),
    "CRC_2" / Int8ub,
)

SciPacket = Struct(
    "header" / PacketHeader,
    "data_field_header" / DataFieldHeader,
    "science_header" / ScienceHeader,
    "science_data" / ScienceData,
)


SSMM = Struct("packets" / GreedyRange(SciPacket))
