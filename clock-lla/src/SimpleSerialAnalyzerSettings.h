#ifndef SIMPLESERIAL_ANALYZER_SETTINGS
#define SIMPLESERIAL_ANALYZER_SETTINGS

#include <AnalyzerSettings.h>
#include <AnalyzerTypes.h>

class SimpleSerialAnalyzerSettings : public AnalyzerSettings
{
public:
    SimpleSerialAnalyzerSettings();
    virtual ~SimpleSerialAnalyzerSettings();

    virtual bool SetSettingsFromInterfaces();
    void UpdateInterfacesFromSettings();
    virtual void LoadSettings( const char* settings );
    virtual const char* SaveSettings();

    Channel mInputChannel;

    // User input only.
    U32 mExpectedFrequencyHz;

    // Kept for simulation generator compatibility.
    U32 mBitRate;

protected:
    AnalyzerSettingInterfaceChannel mInputChannelInterface;
    AnalyzerSettingInterfaceInteger mExpectedFrequencyHzInterface;
};

#endif
