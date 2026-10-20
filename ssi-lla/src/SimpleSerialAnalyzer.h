#ifndef SIMPLESERIAL_ANALYZER_H
#define SIMPLESERIAL_ANALYZER_H

#include <Analyzer.h>
#include "SimpleSerialAnalyzerResults.h"
#include "SimpleSerialAnalyzerSettings.h"
#include "SimpleSerialSimulationDataGenerator.h"

class ANALYZER_EXPORT SimpleSerialAnalyzer : public Analyzer2
{
public:
    SimpleSerialAnalyzer();
    virtual ~SimpleSerialAnalyzer();

    virtual void SetupResults();
    virtual void WorkerThread();

    virtual U32 GenerateSimulationData(
        U64 minimum_sample_index,
        U32 device_sample_rate,
        SimulationChannelDescriptor** simulation_channels
    );

    virtual U32 GetMinimumSampleRateHz();

    virtual const char* GetAnalyzerName() const;
    virtual bool NeedsRerun();

protected:
    std::unique_ptr< SimpleSerialAnalyzerResults > mResults;
    SimpleSerialAnalyzerSettings mSettings;
    SimpleSerialSimulationDataGenerator mSimulationDataGenerator;

    bool mSimulationInitilized;

    AnalyzerChannelData* mClock;
    AnalyzerChannelData* mData;
};

extern "C" ANALYZER_EXPORT const char* GetAnalyzerName();
extern "C" ANALYZER_EXPORT Analyzer* CreateAnalyzer();
extern "C" ANALYZER_EXPORT void DestroyAnalyzer( Analyzer* analyzer );

#endif
