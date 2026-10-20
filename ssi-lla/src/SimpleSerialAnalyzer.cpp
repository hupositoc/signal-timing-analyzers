#include "SimpleSerialAnalyzer.h"
#include "SimpleSerialAnalyzerSettings.h"
#include <AnalyzerChannelData.h>
#include <algorithm>
#include <cmath>

SimpleSerialAnalyzer::SimpleSerialAnalyzer()
    : Analyzer2(),
      mSettings(),
      mSimulationInitilized( false ),
      mClock( nullptr ),
      mData( nullptr )
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

    mResults->AddChannelBubblesWillAppearOn( mSettings.mClockChannel );
}

static U64 NsToSamplesCeil( U32 sample_rate_hz, U32 ns )
{
    const double samples =
        static_cast<double>( sample_rate_hz ) *
        static_cast<double>( ns ) /
        1000000000.0;

    return static_cast<U64>( samples + 0.999999 );
}

static U64 SamplesToNs( U32 sample_rate_hz, U64 samples )
{
    const double seconds =
        static_cast<double>( samples ) /
        static_cast<double>( sample_rate_hz );

    return static_cast<U64>( seconds * 1000000000.0 + 0.5 );
}

void SimpleSerialAnalyzer::WorkerThread()
{
    const U32 sample_rate_hz = GetSampleRate();

    mClock = GetAnalyzerChannelData( mSettings.mClockChannel );
    mData = GetAnalyzerChannelData( mSettings.mDataChannel );

    bool has_pending_rising = false;
    U64 pending_rising_sample = 0;
    U64 pending_rising_data_bit = 0;

    U64 last_valid_falling_sample = 0;
    bool has_last_valid_falling = false;

    const U64 glitch_limit_samples =
        NsToSamplesCeil(
            sample_rate_hz,
            mSettings.mGlitchPulseWidthLimitNs
        );

    for( ;; )
    {
        mClock->AdvanceToNextEdge();

        const U64 clk_edge_sample = mClock->GetSampleNumber();
        const BitState clk_state_after_edge = mClock->GetBitState();

        // CLK rising edge:
        // Start of HIGH pulse.
        if( clk_state_after_edge == BIT_HIGH )
        {
            pending_rising_sample = clk_edge_sample;
            has_pending_rising = true;

            // Sample DATA at rising edge if selected.
            if( mSettings.mSampleEdgeMode == 0 )
            {
                mData->AdvanceToAbsPosition( clk_edge_sample );
                pending_rising_data_bit =
                    ( mData->GetBitState() == BIT_HIGH ) ? 1 : 0;
            }

            ReportProgress( clk_edge_sample );
            continue;
        }

        // CLK falling edge:
        // End of HIGH pulse.
        if( clk_state_after_edge == BIT_LOW )
        {
            if( has_pending_rising == false )
            {
                ReportProgress( clk_edge_sample );
                continue;
            }

            const U64 high_width_samples =
                clk_edge_sample - pending_rising_sample;

            // Consume this rising/falling pair.
            has_pending_rising = false;

            // Short HIGH pulse = glitch.
            // Ignore this falling edge and do not output a bit.
            if( mSettings.mGlitchPulseWidthLimitNs > 0 &&
                high_width_samples < glitch_limit_samples )
            {
                mResults->AddMarker(
                    clk_edge_sample,
                    AnalyzerResults::ErrorX,
                    mSettings.mClockChannel
                );

                ReportProgress( clk_edge_sample );
                continue;
            }

            U64 sample_point = clk_edge_sample;
            U64 bit_value = 0;

            if( mSettings.mSampleEdgeMode == 0 )
            {
                // Rising mode:
                // DATA was sampled at pending_rising_sample.
                sample_point = pending_rising_sample;
                bit_value = pending_rising_data_bit;
            }
            else
            {
                // Falling mode:
                // DATA is sampled at current falling edge.
                sample_point = clk_edge_sample;
                mData->AdvanceToAbsPosition( clk_edge_sample );
                bit_value = ( mData->GetBitState() == BIT_HIGH ) ? 1 : 0;
            }

            U64 falling_interval_ns = 0;

            if( has_last_valid_falling == true )
            {
                const U64 falling_interval_samples =
                    clk_edge_sample - last_valid_falling_sample;

                falling_interval_ns =
                    SamplesToNs( sample_rate_hz, falling_interval_samples );
            }

            // IMPORTANT:
            // Do not create zero-width frames.
            // For Rising sample mode, frame spans rising -> falling.
            // For Falling sample mode, frame spans falling -> falling+1 sample.
            U64 frame_start = sample_point;
            U64 frame_end = clk_edge_sample;

            if( frame_end <= frame_start )
                frame_end = frame_start + 1;

            Frame frame;
            frame.mStartingSampleInclusive = frame_start;
            frame.mEndingSampleInclusive = frame_end;
            frame.mData1 = bit_value;
            frame.mData2 = falling_interval_ns;
            frame.mFlags = mSettings.mSampleEdgeMode & 0x01;

            mResults->AddFrame( frame );
            mResults->CommitResults();

            mResults->AddMarker(
                sample_point,
                AnalyzerResults::Dot,
                mSettings.mClockChannel
            );

            ReportProgress( clk_edge_sample );

            last_valid_falling_sample = clk_edge_sample;
            has_last_valid_falling = true;
        }
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
    return "SSI";
}

const char* GetAnalyzerName()
{
    return "SSI";
}

Analyzer* CreateAnalyzer()
{
    return new SimpleSerialAnalyzer();
}

void DestroyAnalyzer( Analyzer* analyzer )
{
    delete analyzer;
}
