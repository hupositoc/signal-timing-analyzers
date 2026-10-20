#include "SimpleSerialAnalyzerSettings.h"
#include <AnalyzerHelpers.h>

SimpleSerialAnalyzerSettings::SimpleSerialAnalyzerSettings()
    : mInputChannel( UNDEFINED_CHANNEL ),
      mExpectedFrequencyHz( 300 ),
      mBitRate( 300 ),
      mInputChannelInterface(),
      mExpectedFrequencyHzInterface()
{
    mInputChannelInterface.SetTitleAndTooltip(
        "Clock",
        "Clock input channel to analyze."
    );
    mInputChannelInterface.SetChannel( mInputChannel );

    mExpectedFrequencyHzInterface.SetTitleAndTooltip(
        "Expected Frequency [Hz]",
        "Expected input clock frequency. Example: 300 for 300 Hz."
    );
    mExpectedFrequencyHzInterface.SetMin( 1 );
    mExpectedFrequencyHzInterface.SetMax( 100000000 );
    mExpectedFrequencyHzInterface.SetInteger( mExpectedFrequencyHz );

    AddInterface( &mInputChannelInterface );
    AddInterface( &mExpectedFrequencyHzInterface );

    AddExportOption( 0, "Export as CSV file" );
    AddExportExtension( 0, "csv", "csv" );
    AddExportExtension( 0, "text", "txt" );

    ClearChannels();
    AddChannel( mInputChannel, "Clock", false );
}

SimpleSerialAnalyzerSettings::~SimpleSerialAnalyzerSettings()
{
}

bool SimpleSerialAnalyzerSettings::SetSettingsFromInterfaces()
{
    mInputChannel = mInputChannelInterface.GetChannel();
    mExpectedFrequencyHz = mExpectedFrequencyHzInterface.GetInteger();

    if( mExpectedFrequencyHz < 1 )
        mExpectedFrequencyHz = 300;

    ClearChannels();
    AddChannel( mInputChannel, "Clock Analyzer", true );

    return true;
}

void SimpleSerialAnalyzerSettings::UpdateInterfacesFromSettings()
{
    mInputChannelInterface.SetChannel( mInputChannel );
    mExpectedFrequencyHzInterface.SetInteger( mExpectedFrequencyHz );
}

void SimpleSerialAnalyzerSettings::LoadSettings( const char* settings )
{
    SimpleArchive text_archive;
    text_archive.SetString( settings );

    text_archive >> mInputChannel;
    text_archive >> mExpectedFrequencyHz;

    if( mExpectedFrequencyHz < 1 || mExpectedFrequencyHz > 100000000 )
        mExpectedFrequencyHz = 300;

    ClearChannels();
    AddChannel( mInputChannel, "Clock Analyzer", true );

    UpdateInterfacesFromSettings();
}

const char* SimpleSerialAnalyzerSettings::SaveSettings()
{
    SimpleArchive text_archive;

    text_archive << mInputChannel;
    text_archive << mExpectedFrequencyHz;

    return SetReturnString( text_archive.GetString() );
}
