import math
from construct import (
    Adapter,
    BitsInteger,
    BitStruct,
    Bytes,
    GreedyRange,
    If,
    Int8ub,
    Int16ub,
    Int32ub,
    Int64ub,
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


class BinningAdapter(Adapter):
    """Adapter to convert binning value: actual_binning = 1 << stored_value"""
    def _decode(self, obj, context, path):
        return 1 << obj
    
    def _encode(self, obj, context, path):
        # For encoding, we need to find the power of 2
        return int(math.log2(obj))


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

# PEU and ASW housekeeping data structure
# Expected size: 27*2 + 6*2 + 4*1 + 6*4 + 4*2 + 8*2 + 2*2 + 4*1 + 8 = 54 + 12 + 4 + 24 + 8 + 16 + 4 + 4 + 8 = 134 bytes
# This matches the struct.unpack format: '>27H' (54 bytes) + '>6H4B6I4H8H2H4BQ' (80 bytes) = 134 bytes total
ImgInfoStruct = Struct(
    # PEU housekeeping data values (27 uint16 values, ignoring spares)
    "spare0" / Int16ub, 
    "P_L_Exposure" / Int16ub,
    "P_F_Exposure" / Int16ub,
    "P_Y_Start_ADDR" / Int16ub,
    "P_Y_Length" / Int16ub,
    "P_N_Frames" / Int16ub,
    "spare6" / Int16ub,
    "spare7" / Int16ub,
    "C_Reset" / Int16ub,
    "C_Make_Frame" / Int16ub,
    "C_Diagnostic" / Int16ub,
    "C_Reset_Time" / Int16ub,
    "spare12" / Int16ub,
    "spare13" / Int16ub,
    "H_Version" / Int16ub,
    "H_TIME_LO" / Int16ub,
    "H_TIME_HI" / Int16ub,
    "H_CIS_TEMP" / Int16ub,
    "H_D_TEMP" / Int16ub,
    "H_E_TEMP" / Int16ub,
    "H_R_TEMP" / Int16ub,
    "spare21" / Int16ub,
    "spare22" / Int16ub,
    "spare23" / Int16ub,
    "spare24" / Int16ub,
    "H_FRAME_COUNT" / Int16ub,
    "H_STATUS" / Int16ub,
    "H_LAST_CMD" / Int16ub,
    "spare28" / Int16ub,  # spare field, not used
    "spare29" / Int16ub,  # spare field, not used
    "spare30" / Int16ub,  # spare field, not used
    "spare31" / Int16ub,  # spare field, not used

    # ASW housekeeping data values (>6H4B6I4H8H2H4BQ format)
    "SizeX" / Int16ub,
    "SizeY" / Int16ub,
    "RoiStartX" / Int16ub,
    "RoiStartY" / Int16ub,
    "RoiSizeX" / Int16ub,
    "RoiSizeY" / Int16ub,
    "Binning" / BinningAdapter(Int8ub),
    "Compression" / Int8ub,
    "NumImg" / Int8ub,
    "FilterStatus" / Int8ub,
    "HKTime" / Int32ub,
    "ImgTime" / Int32ub,
    "RefSCET" / Int32ub,
    "RefTime" / Int32ub,
    "PeuMkImgTime" / Int32ub,
    "PeuResetTime" / Int32ub,
    "SpikeMaxVal" / Int16ub,
    "SpikeDist" / Int16ub,
    "BadCount" / Int16ub,
    "SpikeCount" / Int16ub,
    "OHU_Temp1" / Int16ub,
    "OHU_Temp2" / Int16ub,
    "OHU_Temp3" / Int16ub,
    "OHU_Temp4" / Int16ub,
    "OHU_Temp5" / Int16ub,
    "DPM_Temp1" / Int16ub,
    "DPM_Temp2" / Int16ub,
    "Ref_Temp" / Int16ub,
    "PeuParityCount" / Int16ub,
    "PeuErrorFlags" / Int16ub,
    "PreProFlags" / Int8ub,
    "CoverSwitchStatus" / Int8ub,
    "CoverLogicStatus" / Int8ub,
    "spare135" / Int8ub,
    "PeuResetTimeUsec" / Int64ub,
    "spare144" / Int8ub,  # padding to align to 160 bytes
    "unused" / Padding(15),  # padding to align to 160 bytes
)

ScienceHeader = Struct(
    "SESSION_ID" / Int32ub,
    "IMG_COUNT" / Int16ub,
    "PKG_TOTAL" / Int16ub,
    "PKG_COUNT" / Int16ub,
    "VERSION" / Int8ub,
    "IMG_INFO_SIZE" / Int8ub,
    "IMG_INFO" / If(this.IMG_INFO_SIZE > 0, ImgInfoStruct),
    "IMG_DATA_LEN1" / Int16ub,
    "CRC_1" / Int8ub,
)

ScienceData = Struct(
    "IMG_DATA" / If(
        this._.science_header.IMG_DATA_LEN1 > 1,
        Bytes(this._.science_header.IMG_DATA_LEN1 - 1),
    ),
    "CRC_2" / If(this._.science_header.IMG_DATA_LEN1 > 0, Int8ub),
)

SciPacket = Struct(
    "header" / PacketHeader,
    "data_field_header" / DataFieldHeader,
    "science_header" / ScienceHeader,
    "science_data" / ScienceData,
)


SSMM = Struct("packets" / GreedyRange(SciPacket))
