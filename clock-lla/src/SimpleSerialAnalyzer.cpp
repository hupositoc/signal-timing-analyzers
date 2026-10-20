#include "SimpleSerialAnalyzer.h"
#include "SimpleSerialAnalyzerSettings.h"
#include <AnalyzerChannelData.h>
#include <algorithm>
#include <cmath>

SimpleSerialAnalyzer::SimpleSerialAnalyzer()
    : Analyzer2(),
      mSettings(),
      mSimulationInitilized( false )
{
    SetAnalyzerSettings( &mSettings );
}

SimpleSerialAnalyzer::~SimpleSerialAnalyzer()
{
    KillThread();
}

void SimpleSerialAnalyzer::SetupResults()
{
    mResults.reset( new SimpleSerialAnalyzerResults( this, &mSettings ) );
    SetAnalyzerResults( mResults.get() );
    mResults->AddChannelBubblesWillAppearOn( mSettings.mInputChannel );
}

static U64 NsToSamplesCeil( U32 sample_rate_hz, double ns )
{
    const double samples =
        static_cast<double>( sample_rate_hz ) * ns / 1000000000.0;

    return static_cast<U64>( samples + 0.999999 );
}

void SimpleSerialAnalyzer::WorkerThread()
{
    const U32 sample_rate_hz = GetSampleRate();

    mSerial = GetAnalyzerChannelData( mSettings.mInputChannel );

    bool has_last_valid_falling = false;
    U64 last_valid_falling_sample = 0;

    // Fixed internally. Do not expose this to user setting.
    const double fixed_frequency_margin_percent = 1.0;

    const double expected_frequency =
        static_cast<double>( mSettings.mExpectedFrequencyHz );

    const double max_frequency_for_glitch_filter =
        expected_frequency * ( 1.0 + fixed_frequency_margin_percent / 100.0 );

    const double min_frequency_for_pass =
        expected_frequency * ( 1.0 - fixed_frequency_margin_percent / 100.0 );

    const double expected_period_ns =
        1000000000.0 / expected_frequency;

    // Falling interval shorter than this is treated as glitch and ignored.
    const double min_valid_falling_interval_ns =
        1000000000.0 / max_frequency_for_glitch_filter;

    // Period longer than this is FAIL.
    const double max_pass_period_ns =
        1000000000.0 / min_frequency_for_pass;

    const U64 min_valid_falling_interval_samples =
        NsToSamplesCeil( sample_rate_hz, min_valid_falling_interval_ns );

    for( ;; )
    {
        mSerial->AdvanceToNextEdge();

        const U64 edge_sample = mSerial->GetSampleNumber();
        const BitState state_after_edge = mSerial->GetBitState();

        // We only use falling edges for clock period judgment.
        if( state_after_edge != BIT_LOW )
        {
            ReportProgress( edge_sample );
            continue;
        }

        // First falling edge becomes reference.
        if( has_last_valid_falling == false )
        {
            last_valid_falling_sample = edge_sample;
            has_last_valid_falling = true;

            mResults->AddMarker(
                edge_sample,
                AnalyzerResults::Dot,
                mSettings.mInputChannel
            );

            ReportProgress( edge_sample );
            continue;
        }

        const U64 period_samples =
            edge_sample - last_valid_falling_sample;

        // If this falling edge occurs too soon after the last valid falling,
        // treat it as a glitch falling edge and ignore it.
        // Important: last_valid_falling_sample is NOT updated.
        if( period_samples < min_valid_falling_interval_samples )
        {
            mResults->AddMarker(
                edge_sample,
                AnalyzerResults::ErrorX,
                mSettings.mInputChannel
            );

            ReportProgress( edge_sample );
            continue;
        }

        const double period_s =
            static_cast<double>( period_samples ) /
            static_cast<double>( sample_rate_hz );

        const double period_ns =
            period_s * 1000000000.0;

        const double frequency_hz =
            1.0 / period_s;

        // Only maximum period is used for PASS/FAIL.
        // Too-long period = FAIL.
        // Too-short period was already handled as glitch and ignored.
        const bool pass =
            ( period_ns <= max_pass_period_ns );

        const U64 frequency_hz_u64 =
            static_cast<U64>( frequency_hz + 0.5 );

        const U64 period_ns_u64 =
            static_cast<U64>( period_ns + 0.5 );

        Frame frame;
        frame.mStartingSampleInclusive = last_valid_falling_sample;
        frame.mEndingSampleInclusive = edge_sample;
        frame.mData1 = frequency_hz_u64;
        frame.mData2 = period_ns_u64;
        frame.mFlags = pass ? 0 : 1;

        mResults->AddFrame( frame );
        mResults->CommitResults();

        mResults->AddMarker(
            edge_sample,
            pass ? AnalyzerResults::Dot : AnalyzerResults::ErrorX,
            mSettings.mInputChannel
        );

        ReportProgress( edge_sample );

        // Only accepted falling updates the reference.
        last_valid_falling_sample = edge_sample;
    }
}

bool SimpleSerialAnalyzer::NeedsRerun()
{
    return false;
}

U32 SimpleSerialAnalyzer::GenerateSimulationData(
    U64 minimum_sample_index,
    U32 device_sample_rate,
    SimulationChannelDescriptor** simulation_channels )
{
    if( mSimulationInitilized == false )
    {
        mSimulationDataGenerator.Initialize( GetSimulationSampleRate(), &mSettings );
        mSimulationInitilized = true;
    }

    return mSimulationDataGenerator.GenerateSimulationData(
        minimum_sample_index,
        device_sample_rate,
        simulation_channels
    );
}

U32 SimpleSerialAnalyzer::GetMinimumSampleRateHz()
{
    return 1000000;
}

const char* SimpleSerialAnalyzer::GetAnalyzerName() const
{
    return "Clock Analyzer";
}

const char* GetAnalyzerName()
{
    return "Clock Analyzer";
}

Analyzer* CreateAnalyzer()
{
    return new SimpleSerialAnalyzer();
}

void DestroyAnalyzer( Analyzer* analyzer )
{
    delete analyzer;
}
