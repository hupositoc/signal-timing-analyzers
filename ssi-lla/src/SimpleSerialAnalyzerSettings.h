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

    // For compatibility with original SampleAnalyzer.
    Channel mInputChannel;

    // SSI inputs.
    Channel mClockChannel;
    Channel mDataChannel;

    // If CLK rising -> falling width is shorter than this,
    // that falling edge is ignored as a glitch.
    U32 mGlitchPulseWidthLimitNs;

    // 0 = sample DATA at CLK rising edge
    // 1 = sample DATA at CLK falling edge
    U32 mSampleEdgeMode;

    // Kept for simulation generator compatibility.
    U32 mBitRate;

protected:
    AnalyzerSettingInterfaceChannel mClockChannelInterface;
    AnalyzerSettingInterfaceChannel mDataChannelInterface;
    AnalyzerSettingInterfaceInteger mGlitchPulseWidthLimitNsInterface;
    AnalyzerSettingInterfaceInteger mSampleEdgeModeInterface;
};

#endif
