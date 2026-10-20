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

static void FormatFrequencyString( U64 frequency_hz, char* out, size_t out_size )
{
    if( frequency_hz >= 1000000ULL )
    {
        double mhz = static_cast<double>( frequency_hz ) / 1000000.0;
        std::snprintf( out, out_size, "%.6f MHz", mhz );
    }
    else if( frequency_hz >= 1000ULL )
    {
        double khz = static_cast<double>( frequency_hz ) / 1000.0;
        std::snprintf( out, out_size, "%.3f kHz", khz );
    }
    else
    {
        std::snprintf(
            out,
            out_size,
            "%llu Hz",
            static_cast<unsigned long long>( frequency_hz )
        );
    }
}

void SimpleSerialAnalyzerResults::GenerateBubbleText(
    U64 frame_index,
    Channel& channel,
    DisplayBase display_base )
{
    ClearResultStrings();

    Frame frame = GetFrame( frame_index );

    char freq_str[128];
    FormatFrequencyString( frame.mData1, freq_str, sizeof( freq_str ) );

    const char* result_text =
        ( frame.mFlags == 0 ) ? "PASS" : "FAIL";

    char result[256];
    std::snprintf(
        result,
        sizeof( result ),
        "%s, %s, Period %llu ns",
        result_text,
        freq_str,
        static_cast<unsigned long long>( frame.mData2 )
    );

    AddResultString( result_text );
    AddResultString( freq_str );
    AddResultString( result );
}

void SimpleSerialAnalyzerResults::GenerateExportFile(
    const char* file,
    DisplayBase display_base,
    U32 export_type_user_id )
{
    std::ofstream file_stream( file, std::ios::out );

    U64 trigger_sample = mAnalyzer->GetTriggerSample();
    U32 sample_rate = mAnalyzer->GetSampleRate();

    const double fixed_frequency_margin_percent = 1.0;

    const double expected_frequency =
        static_cast<double>( mSettings->mExpectedFrequencyHz );

    const double expected_period_ns =
        1000000000.0 / expected_frequency;

    const double max_frequency_for_glitch_filter =
        expected_frequency * ( 1.0 + fixed_frequency_margin_percent / 100.0 );

    const double min_frequency_for_pass =
        expected_frequency * ( 1.0 - fixed_frequency_margin_percent / 100.0 );

    const double min_valid_falling_interval_ns =
        1000000000.0 / max_frequency_for_glitch_filter;

    const double max_pass_period_ns =
        1000000000.0 / min_frequency_for_pass;

    file_stream
        << "Time [s],Start Sample,End Sample,Period [ns],Frequency [Hz],Frequency [kHz],Result,"
        << "Expected Frequency [Hz],Fixed Margin [%],Expected Period [ns],"
        << "Min Valid Falling Interval [ns],Max PASS Period [ns]"
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

        const double freq_khz =
            static_cast<double>( frame.mData1 ) / 1000.0;

        const char* result_text =
            ( frame.mFlags == 0 ) ? "PASS" : "FAIL";

        file_stream
            << time_str << ","
            << frame.mStartingSampleInclusive << ","
            << frame.mEndingSampleInclusive << ","
            << frame.mData2 << ","
            << frame.mData1 << ","
            << std::fixed << std::setprecision( 3 ) << freq_khz << ","
            << result_text << ","
            << mSettings->mExpectedFrequencyHz << ","
            << std::fixed << std::setprecision( 1 ) << fixed_frequency_margin_percent << ","
            << std::fixed << std::setprecision( 0 ) << expected_period_ns << ","
            << std::fixed << std::setprecision( 0 ) << min_valid_falling_interval_ns << ","
            << std::fixed << std::setprecision( 0 ) << max_pass_period_ns
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

    char freq_str[128];
    FormatFrequencyString( frame.mData1, freq_str, sizeof( freq_str ) );

    const char* result_text =
        ( frame.mFlags == 0 ) ? "PASS" : "FAIL";

    char result[256];
    std::snprintf(
        result,
        sizeof( result ),
        "%s / %s / %llu ns",
        result_text,
        freq_str,
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
