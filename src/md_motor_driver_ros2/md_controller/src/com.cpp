#include "md_controller/com.hpp"

#include <algorithm>
#include <cstdint>

serial::Serial ser;
static bool g_serial_debug = false;

void ResetReceiveState()
{
    Com.byStep = 0;
    Com.byPacketNum = 0;
    Com.byChkSum = 0;
    Com.byMaxDataNum = 0;
    Com.byDataNum = 0;
    Com.fgPacketOK = 0;
}

// Get the low and high byte from short
IByte Short2Byte(short sIn)
{
    IByte Ret;

    Ret.byLow = sIn & 0xff;
    Ret.byHigh = sIn>>8 & 0xff;

    return Ret;
}
// Make short data from two bytes
int Byte2Short(BYTE byLow, BYTE byHigh)
{
    return static_cast<int16_t>(static_cast<uint16_t>(byLow) |
                                (static_cast<uint16_t>(byHigh) << 8));
}

// Make long data from four bytes
int Byte2LInt(BYTE byData1, BYTE byData2, BYTE byData3, BYTE byData4)
{
    const uint32_t value = static_cast<uint32_t>(byData1) |
                           (static_cast<uint32_t>(byData2) << 8) |
                           (static_cast<uint32_t>(byData3) << 16) |
                           (static_cast<uint32_t>(byData4) << 24);
    return static_cast<int32_t>(value);
}

void SetSerialDebug(bool enabled)
{
    g_serial_debug = enabled;
}

//Initialize serial communication in ROS
int InitSerial(void)
{
    try
    {
        ser.setPort(Com.nPort);
        ser.setBaudrate(Com.nBaudrate);
        serial::Timeout to = serial::Timeout::simpleTimeout(1667); //1667 when baud is 57600, 0.6ms
        ser.setTimeout(to);                                        //2857 when baud is 115200, 0.35ms
        ser.open();
    }
    catch (serial::IOException& e)
    {
        RCLCPP_ERROR_STREAM(rclcpp::get_logger("rclcpp"),"Unable to open port ");
        return -1;
    }
    if(ser.isOpen())
        RCLCPP_INFO_STREAM(rclcpp::get_logger("rclcpp"),"Serial Port initialized");
    else
        return -1;
    return 0;
}

//for sending the data (One ID)
int PutMdData(BYTE byPID, BYTE byMID, int id_num, int nArray[])
{
    BYTE byPidDataSize, byDataSize, i, j;
    static BYTE byTempDataSum;
    
    for(j = 0; j <MAX_PACKET_SIZE; j++) Com.bySndBuf[j] = 0;

    Com.bySndBuf[0] = byMID;
    Com.bySndBuf[1] = 184;
    Com.bySndBuf[2] = id_num;
    Com.bySndBuf[3] = byPID;

    switch(byPID)
    {
        case PID_REQ_PID_DATA:
                byDataSize      = 1;
                byPidDataSize   = 7;
                byTempDataSum   = 0;

                Com.bySndBuf[4] = byDataSize;
                Com.bySndBuf[5] = (BYTE)nArray[0];

                for(i = 0; i < (byPidDataSize-1); i++) byTempDataSum += Com.bySndBuf[i];
                Com.bySndBuf[byPidDataSize-1] = ~(byTempDataSum) + 1; //check sum

                ser.write(Com.bySndBuf, byPidDataSize);

                break;
                
        case PID_POSI_RESET:
                byDataSize    = 1;
                byPidDataSize = 7;
                byTempDataSum = 0;

                Com.bySndBuf[4]  = byDataSize;
                Com.bySndBuf[5]  = nArray[0];

                for(i = 0; i < (byPidDataSize-1); i++) byTempDataSum += Com.bySndBuf[i];
                Com.bySndBuf[byPidDataSize-1] = ~(byTempDataSum) + 1; //check sum

                ser.write(Com.bySndBuf, byPidDataSize);

                break;

        case PID_COMMAND:
            byDataSize    = 1;
            byPidDataSize = 7;
            byTempDataSum = 0;

            Com.bySndBuf[4]  = byDataSize;
            Com.bySndBuf[5]  = nArray[0];

            for(i = 0; i < (byPidDataSize-1); i++) byTempDataSum += Com.bySndBuf[i];
            Com.bySndBuf[byPidDataSize-1] = ~(byTempDataSum) + 1; //check sum

            ser.write(Com.bySndBuf, byPidDataSize);

            break;

        case PID_VEL_CMD:

            byDataSize    = 2;
            byPidDataSize = 8;
            byTempDataSum = 0;

            Com.bySndBuf[4]  = byDataSize;
            Com.bySndBuf[5]  = nArray[0];
            Com.bySndBuf[6]  = nArray[1];


            for(i = 0; i < (byPidDataSize-1); i++) byTempDataSum += Com.bySndBuf[i];
            Com.bySndBuf[byPidDataSize-1] = ~(byTempDataSum) + 1; //check sum

            ser.write(Com.bySndBuf, byPidDataSize);
            // printf("send data : ");
            // for(int k = 0; k < byPidDataSize; k++) printf("%d ", Com.bySndBuf[k]); cout << endl;
            break;
        
        case PID_PNT_VEL_CMD:
            byDataSize = 7;
            byPidDataSize = 13;  // 헤더(5) + 데이터(7) + 체크섬(1)
            byTempDataSum = 0;
            
            Com.bySndBuf[4] = byDataSize;
            Com.bySndBuf[5] = nArray[0];   // D1: ID1 ENABLE
            Com.bySndBuf[6] = nArray[1];   // D2: ID1 RPM Low
            Com.bySndBuf[7] = nArray[2];   // D3: ID1 RPM High
            Com.bySndBuf[8] = nArray[3];   // D4: ID2 ENABLE
            Com.bySndBuf[9] = nArray[4];   // D5: ID2 RPM Low
            Com.bySndBuf[10] = nArray[5];  // D6: ID2 RPM High
            Com.bySndBuf[11] = nArray[6];  // D7: 리턴 데이터 요청

            for(i = 0; i < (byPidDataSize-1); i++) byTempDataSum += Com.bySndBuf[i];
                Com.bySndBuf[byPidDataSize-1] = ~(byTempDataSum) + 1; //check sum
    
            ser.write(Com.bySndBuf, byPidDataSize);

            break;
    }
    
    return SUCCESS;
}


int MdReceiveProc(void) //save the identified serial data to defined variable according to PID NUMBER data
{
    BYTE byRcvID, byRcvPID, byRcvDataSize;

    byRcvID       = Com.byRcvBuf[2];
    byRcvPID      = Com.byRcvBuf[3];
    byRcvDataSize = Com.byRcvBuf[4];
    Com.last_rcv_id = byRcvID;
    Com.last_rcv_pid = byRcvPID;
    Com.last_rcv_data_size = byRcvDataSize;
    for (int i = 0; i < 18; ++i) {
        Com.last_main_data[i] = (i < byRcvDataSize) ? Com.byRcvBuf[5 + i] : 0;
    }

    if (g_serial_debug) {
        printf("RX id=%d pid=%d size=%d data:", byRcvID, byRcvPID, byRcvDataSize);
        for (int i = 0; i < byRcvDataSize; ++i) printf(" %d", Com.byRcvBuf[5 + i]);
        printf("\n");
    }

    switch(byRcvPID)
    {
        case PID_MAIN_DATA:
            Com.rpm  = Byte2Short(Com.byRcvBuf[5], Com.byRcvBuf[6]);
            Com.position = Byte2LInt(Com.byRcvBuf[15], Com.byRcvBuf[16], Com.byRcvBuf[17], Com.byRcvBuf[18]);
            if (byRcvID < 3) {
                Com.rpm_by_id[byRcvID] = Com.rpm;
                Com.position_by_id[byRcvID] = Com.position;
                Com.feedback_seen_by_id[byRcvID] = 1;
            }
            break;

        case PID_PNT_MAIN_DATA:
            if (byRcvDataSize >= 18) {
                Com.pnt_rpm[0] = Byte2Short(Com.byRcvBuf[5], Com.byRcvBuf[6]);
                Com.pnt_position[0] = Byte2LInt(Com.byRcvBuf[10], Com.byRcvBuf[11],
                                                Com.byRcvBuf[12], Com.byRcvBuf[13]);
                Com.pnt_rpm[1] = Byte2Short(Com.byRcvBuf[14], Com.byRcvBuf[15]);
                Com.pnt_position[1] = Byte2LInt(Com.byRcvBuf[19], Com.byRcvBuf[20],
                                                Com.byRcvBuf[21], Com.byRcvBuf[22]);
                Com.pnt_feedback_seen = 1;
            }
            break;
    }

    return SUCCESS;
}

int AnalyzeReceivedData(BYTE byArray[], BYTE byBufNum) //Analyze the communication data
{
    static BYTE byChkSec;
    BYTE i, j;
    // printf("0 : %d , 1 : %d \n",byArray[0],byArray[1]);
    // printf("id : %d \n",byArray[2]);

    if(Com.byPacketNum >= MAX_PACKET_SIZE)
    {
        ResetReceiveState();
        return FAIL;
    }
    for(j = 0; j < byBufNum; j++)
    {
        switch(Com.byStep){
            case 0:    //Put the first header byte after checking the data
                if((byArray[j] == 184) || (byArray[j] == 183))
                {
                    Com.byChkSum += byArray[j];
                    Com.byRcvBuf[Com.byPacketNum++] = byArray[j];
                    Com.byChkComError = 0;
                    Com.byStep++;
                }
                else
                {
                    if (g_serial_debug) printf("ERROR (1)\n");
                    ResetReceiveState();
                    Com.byChkComError++;

                }
                break;

            case 1:    //Check the second header byte
                if(((Com.byRcvBuf[0] == 184) && (byArray[j] == 183)) ||
                   ((Com.byRcvBuf[0] == 183) && (byArray[j] == 184)))
                {
                    Com.byChkSum += byArray[j];
                    Com.byRcvBuf[Com.byPacketNum++] = byArray[j];
                    Com.byStep++;
                    Com.byChkComError = 0;
                }
                else
                {
                    if (g_serial_debug) printf("ERROR (header)\n");
                    BYTE candidate = byArray[j];
                    ResetReceiveState();
                    if((candidate == 184) || (candidate == 183))
                    {
                        Com.byChkSum += candidate;
                        Com.byRcvBuf[Com.byPacketNum++] = candidate;
                        Com.byStep = 1;
                    }
                    Com.byChkComError++;
                }
                break;

            case 2:    //Check ID
                if(byArray[j] == 1 || byArray[j] == 2)
                {
                    Com.byChkSum += byArray[j];
                    Com.byRcvBuf[Com.byPacketNum++] = byArray[j];
                    Com.byStep++;
                    Com.byChkComError = 0;
                }
                else
                {
                    if (g_serial_debug) printf("ERROR (2)\n");
                    ResetReceiveState();
                    Com.byChkComError++;
                }
                break;

             case 3:    //Put the PID number into the array
                if(byArray[j] != PID_MAIN_DATA && byArray[j] != PID_PNT_MAIN_DATA)
                {
                    if (g_serial_debug) printf("ERROR (pid %d)\n", byArray[j]);
                    ResetReceiveState();
                    Com.byChkComError++;
                    break;
                }
                Com.byChkSum += byArray[j];
                Com.byRcvBuf[Com.byPacketNum++] = byArray[j];
                Com.byStep++;
                break;

             case 4:    //Put the DATANUM into the array
                if(byArray[j] > MAX_DATA_SIZE ||
                   (Com.byRcvBuf[3] == PID_MAIN_DATA && byArray[j] < 14) ||
                   (Com.byRcvBuf[3] == PID_PNT_MAIN_DATA && byArray[j] < 18))
                {
                    if (g_serial_debug) printf("ERROR (size %d)\n", byArray[j]);
                    ResetReceiveState();
                    Com.byChkComError++;
                    break;
                }
                Com.byMaxDataNum = byArray[j];
                Com.byDataNum = 0;
                Com.byChkSum += byArray[j];
                Com.byRcvBuf[Com.byPacketNum++] = byArray[j];
                Com.byStep++;
                break;

             case 5:    //Put the DATA into the array
                Com.byRcvBuf[Com.byPacketNum++] = byArray[j];
                Com.byChkSum += byArray[j];

                if(++Com.byDataNum >= MAX_DATA_SIZE)
                {
                    if (g_serial_debug) printf("check 5\n");
                    Com.byTotalRcvDataNum = 0;
                    ResetReceiveState();
                    break;
                }

                if(Com.byDataNum>= Com.byMaxDataNum) Com.byStep++;
                break;

             case 6:    //Put the check sum after Checking checksum
                Com.byChkSum += byArray[j];
                Com.byRcvBuf[Com.byPacketNum++] = byArray[j];
                // printf("byChkSum : %d \n", Com.byChkSum);
                if(Com.byChkSum == 0)
                {
                    Com.fgPacketOK   = 1;
                    Com.fgComDataChk = 1;
                    Com.byDataNum    = 0;
                    Com.byMaxDataNum = 0;
                } else {
                    Com.byPacketNum = 0;
                    Com.byDataNum = 0;
                    Com.byMaxDataNum = 0;
                    Com.fgPacketOK = 0;
                }

                Com.byTotalRcvDataNum = 0;
                Com.byStep = 0;
                Com.byChkSum = 0;
                
                break;

            default:
                if (g_serial_debug) printf("check default\n");

                ResetReceiveState();
                Com.fgComComple = ON;
                break;
        }
        if(Com.fgPacketOK)
        {

            Com.fgPacketOK   = 0;
            Com.byPacketSize = 0;
            Com.byPacketNum  = 0;

            if(byChkSec == 0)
            {
                byChkSec = 1;
            }
            MdReceiveProc();                                 //save the identified serial data to defined variable
        }

        if(Com.byChkComError == 10) //while 50ms
        {
            if (g_serial_debug) printf("check error\n");
    
            Com.byChkComError = 0;
            Com.byStep = 0;
            Com.byChkSum = 0;
            Com.byMaxDataNum = 0;
            Com.byDataNum = 0;
            for(i = 0; i < MAX_PACKET_SIZE; i++) Com.byRcvBuf[i] = 0;
            j = byBufNum;
        }

    }
    return SUCCESS;
}

int ReceiveDataFromController(BYTE init) //Analyze the communication data
{
    BYTE byRcvBuf[250];
    size_t byBufNumber;
    
    byBufNumber = ser.available();

    if(byBufNumber != 0)
    {
        byBufNumber = std::min(byBufNumber, sizeof(byRcvBuf));
        ser.read(byRcvBuf, byBufNumber);
        AnalyzeReceivedData(byRcvBuf, static_cast<BYTE>(byBufNumber));
        if(init == ON){
            if(Com.feedback_seen_by_id[Motor.ID] || Com.pnt_feedback_seen){
                RCLCPP_INFO(rclcpp::get_logger("rclcpp"), "ID %d Motor Init success!", Motor.ID);
                Motor.InitMotor=OFF;
            }
        }
    }
    return 1;
}
