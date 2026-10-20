#include "SimpleSerialAnalyzerResults.h"
#include <AnalyzerHelpers.h>
#include "SimpleSerialAnalyzer.h"
#include "SimpleSerialAnalyzerSettings.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <cstdio>

SimpleSerialAnalyzerResults::SimpleSerialAnalyzerResults(
    SimpleSerialAnalyzer* analyzer,
    SimpleSerialAnalyzerSettings* settings )
    : AnalyzerResults(),
      mSettings( settings ),
      mAnalyzer( analyzer )
{
}

SimpleSerialAnalyzerResults::~SimpleSerialAnalyzerResults()
{
}

static const char* GetSampleEdgeText( U64 flags )
{
    return ( ( flags & 0x01 ) == 0 ) ? "Rising" : "Falling";
}

void SimpleSerialAnalyzerResults::GenerateBubbleText(
    U64 frame_index,
    Channel& channel,
    DisplayBase display_base )
{
    ClearResultStrings();

    Frame frame = GetFrame( frame_index );

    const U64 bit_value = frame.mData1 & 0x01;
    const char* sample_edge = GetSampleEdgeText( frame.mFlags );

    char value_str[128];

    AnalyzerHelpers::GetNumberString(
        bit_value,
        display_base,
        1,
        value_str,
        sizeof( value_str )
    );

    char detail_str[192];
    std::snprintf(
        detail_str,
        sizeof( detail_str ),
        "%s | 1 bit | Edge=%s | Gap=%llu ns",
        value_str,
        sample_edge,
        static_cast<unsigned long long>( frame.mData2 )
    );

    AddResultString( value_str );
    AddResultString( detail_str );
}

void SimpleSerialAnalyzerResults::GenerateExportFile(
    const char* file,
    DisplayBase display_base,
    U32 export_type_user_id )
{
    std::ofstream file_stream( file, std::ios::out );

    U64 trigger_sample = mAnalyzer->GetTriggerSample();
    U32 sample_rate = mAnalyzer->GetSampleRate();

    file_stream
        << "Time [s],Start Sample,End Sample,Raw Value,Bit Count,Sample Edge,Falling Interval [ns],Glitch Pulse Width Limit [ns]"
        << std::endl;

    U64 num_frames = GetNumFrames();

    for( U64 i = 0; i < num_frames; i++ )
    {
        Frame frame = GetFrame( i );

        char time_str[128];
        AnalyzerHelpers::GetTimeString(
            frame.mStartingSampleInclusive,
            trigger_sample,
            sample_rate,
            time_str,
            sizeof( time_str )
        );

        const U64 bit_value = frame.mData1 & 0x01;
        const char* sample_edge = GetSampleEdgeText( frame.mFlags );

        char value_str[128];

        AnalyzerHelpers::GetNumberString(
            bit_value,
            display_base,
            1,
            value_str,
            sizeof( value_str )
        );

        file_stream
            << time_str << ","
            << frame.mStartingSampleInclusive << ","
            << frame.mEndingSampleInclusive << ","
            << value_str << ","
            << 1 << ","
            << sample_edge << ","
            << frame.mData2 << ","
            << mSettings->mGlitchPulseWidthLimitNs
            << std::endl;

        if( UpdateExportProgressAndCheckForCancel( i, num_frames ) == true )
        {
            file_stream.close();
            return;
        }
    }

    file_stream.close();
}

void SimpleSerialAnalyzerResults::GenerateFrameTabularText(
    U64 frame_index,
    DisplayBase display_base )
{
#ifdef SUPPORTS_PROTOCOL_SEARCH
    ClearTabularText();

    Frame frame = GetFrame( frame_index );

    const U64 bit_value = frame.mData1 & 0x01;
    const char* sample_edge = GetSampleEdgeText( frame.mFlags );

    char value_str[128];

    AnalyzerHelpers::GetNumberString(
        bit_value,
        display_base,
        1,
        value_str,
        sizeof( value_str )
    );

    char result[192];
    std::snprintf(
        result,
        sizeof( result ),
        "%s / 1 bit / Edge=%s / Gap=%llu ns",
        value_str,
        sample_edge,
        static_cast<unsigned long long>( frame.mData2 )
    );

    AddTabularText( result );
#endif
}

void SimpleSerialAnalyzerResults::GeneratePacketTabularText(
    U64 packet_id,
    DisplayBase display_base )
{
}

void SimpleSerialAnalyzerResults::GenerateTransactionTabularText(
    U64 transaction_id,
    DisplayBase display_base )
{
}
