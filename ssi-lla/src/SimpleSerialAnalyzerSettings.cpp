#include "SimpleSerialAnalyzerSettings.h"
#include <AnalyzerHelpers.h>

SimpleSerialAnalyzerSettings::SimpleSerialAnalyzerSettings()
    : mInputChannel( UNDEFINED_CHANNEL ),
      mClockChannel( UNDEFINED_CHANNEL ),
      mDataChannel( UNDEFINED_CHANNEL ),
      mGlitchPulseWidthLimitNs( 500 ),
      mSampleEdgeMode( 0 ),
      mBitRate( 500000 ),
      mClockChannelInterface(),
      mDataChannelInterface(),
      mGlitchPulseWidthLimitNsInterface(),
      mSampleEdgeModeInterface()
{
    mClockChannelInterface.SetTitleAndTooltip(
        "Clock",
        "SSI clock input channel."
    );
    mClockChannelInterface.SetChannel( mClockChannel );

    mDataChannelInterface.SetTitleAndTooltip(
        "Data",
        "SSI data input channel."
    );
    mDataChannelInterface.SetChannel( mDataChannel );

    mGlitchPulseWidthLimitNsInterface.SetTitleAndTooltip(
        "Glitch Pulse Width Limit [ns]",
        "If CLK rising-to-falling width is shorter than this value, that high pulse is ignored as a glitch."
    );
    mGlitchPulseWidthLimitNsInterface.SetMin( 0 );
    mGlitchPulseWidthLimitNsInterface.SetMax( 100000000 );
    mGlitchPulseWidthLimitNsInterface.SetInteger( mGlitchPulseWidthLimitNs );

    mSampleEdgeModeInterface.SetTitleAndTooltip(
        "Sample Edge",
        "0 = Rising edge, 1 = Falling edge. Default is 0, Rising."
    );
    mSampleEdgeModeInterface.SetMin( 0 );
    mSampleEdgeModeInterface.SetMax( 1 );
    mSampleEdgeModeInterface.SetInteger( mSampleEdgeMode );

    AddInterface( &mClockChannelInterface );
    AddInterface( &mDataChannelInterface );
    AddInterface( &mGlitchPulseWidthLimitNsInterface );
    AddInterface( &mSampleEdgeModeInterface );

    AddExportOption( 0, "Export as CSV file" );
    AddExportExtension( 0, "csv", "csv" );
    AddExportExtension( 0, "text", "txt" );

    ClearChannels();

    AddChannel( mClockChannel, "SSI Clock", false );
    AddChannel( mDataChannel, "SSI Data", false );

    // Compatibility field.
    mInputChannel = mClockChannel;
}

SimpleSerialAnalyzerSettings::~SimpleSerialAnalyzerSettings()
{
}

bool SimpleSerialAnalyzerSettings::SetSettingsFromInterfaces()
{
    mClockChannel = mClockChannelInterface.GetChannel();
    mDataChannel = mDataChannelInterface.GetChannel();
    mGlitchPulseWidthLimitNs = mGlitchPulseWidthLimitNsInterface.GetInteger();
    mSampleEdgeMode = mSampleEdgeModeInterface.GetInteger();

    if( mGlitchPulseWidthLimitNs > 100000000 )
        mGlitchPulseWidthLimitNs = 500;

    if( mSampleEdgeMode > 1 )
        mSampleEdgeMode = 0;

    // Compatibility field.
    mInputChannel = mClockChannel;

    ClearChannels();

    AddChannel( mClockChannel, "SSI Clock", true );
    AddChannel( mDataChannel, "SSI Data", true );

    return true;
}

void SimpleSerialAnalyzerSettings::UpdateInterfacesFromSettings()
{
    mClockChannelInterface.SetChannel( mClockChannel );
    mDataChannelInterface.SetChannel( mDataChannel );
    mGlitchPulseWidthLimitNsInterface.SetInteger( mGlitchPulseWidthLimitNs );
    mSampleEdgeModeInterface.SetInteger( mSampleEdgeMode );
}

void SimpleSerialAnalyzerSettings::LoadSettings( const char* settings )
{
    SimpleArchive text_archive;
    text_archive.SetString( settings );

    text_archive >> mClockChannel;
    text_archive >> mDataChannel;
    text_archive >> mGlitchPulseWidthLimitNs;
    text_archive >> mSampleEdgeMode;

    if( mGlitchPulseWidthLimitNs > 100000000 )
        mGlitchPulseWidthLimitNs = 500;

    if( mSampleEdgeMode > 1 )
        mSampleEdgeMode = 0;

    // Compatibility field.
    mInputChannel = mClockChannel;

    ClearChannels();

    AddChannel( mClockChannel, "SSI Clock", true );
    AddChannel( mDataChannel, "SSI Data", true );

    UpdateInterfacesFromSettings();
}

const char* SimpleSerialAnalyzerSettings::SaveSettings()
{
    SimpleArchive text_archive;

    text_archive << mClockChannel;
    text_archive << mDataChannel;
    text_archive << mGlitchPulseWidthLimitNs;
    text_archive << mSampleEdgeMode;

    return SetReturnString( text_archive.GetString() );
}
