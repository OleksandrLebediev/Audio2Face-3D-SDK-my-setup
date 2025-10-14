// Minimal CLI tool: read WAV, run A2E, print CSV to stdout
#include "audio2emotion/audio2emotion.h"
#include "audio2x/cuda_utils.h"
#include "audio2x/audio_accumulator.h"
#include "AudioFile.h"
#include <cxxopts.hpp>
#include <iostream>
#include <vector>
#include <string>
#include <iomanip>

template <typename T> struct Destroyer { void operator()(T* p) const { if (p) p->Destroy(); } };
template <typename T> using UniquePtr = std::unique_ptr<T, Destroyer<T>>;
template <typename T> UniquePtr<T> ToUniquePtr(T* p) { return UniquePtr<T>(p); }

static std::vector<float> readAudioMono16k(const std::string& path) {
    AudioFile<float> audio;
    if (!audio.load(path)) {
        throw std::runtime_error("Failed to load audio: " + path);
    }
    if (audio.getSampleRate() != 16000) {
        throw std::runtime_error("Expected 16kHz WAV input");
    }
    if (audio.getNumChannels() < 1) {
        throw std::runtime_error("No audio channels");
    }
    return audio.samples[0];
}

int main(int argc, char** argv) {
    try {
        cxxopts::Options options("a2e_csv", "Audio2Emotion -> CSV");
        options.add_options()
            ("i,input", "Input WAV (16kHz)", cxxopts::value<std::string>())
            ("m,model", "Model JSON (classifier model.json)", cxxopts::value<std::string>())
            ("h,help", "Show help");
        auto result = options.parse(argc, argv);
        if (result.count("help") || !result.count("input") || !result.count("model")) {
            std::cout << options.help() << std::endl;
            return 2;
        }
        const std::string inputWav = result["input"].as<std::string>();
        const std::string modelJson = result["model"].as<std::string>();

        auto audioBuf = readAudioMono16k(inputWav);

        // CUDA stream
        auto cudaStream = ToUniquePtr(nva2x::CreateCudaStream());
        if (!cudaStream) throw std::runtime_error("Failed to create CUDA stream");

        // Audio accumulator
        auto audioAcc = ToUniquePtr(nva2x::CreateAudioAccumulator(16000, 0));
        if (!audioAcc) throw std::runtime_error("Failed to create audio accumulator");
        if (auto ec = audioAcc->Accumulate(nva2x::HostTensorFloatConstView{audioBuf.data(), audioBuf.size()}, cudaStream->Data()))
            throw std::runtime_error("Accumulate failed");
        if (auto ec = audioAcc->Close()) (void)ec;

        // Model
        auto modelInfo = ToUniquePtr(nva2e::ReadClassifierModelInfo(modelJson.c_str()));
        if (!modelInfo) throw std::runtime_error("Failed to read A2E model info");

        // Executor
        nva2e::EmotionExecutorCreationParameters params{};
        params.cudaStream = cudaStream->Data();
        params.nbTracks = 1;
        const auto sharedAudio = audioAcc.get();
        params.sharedAudioAccumulators = &sharedAudio;
        auto classifierParams = modelInfo->GetExecutorCreationParameters(60000, 30, 1, 30);
        auto executor = ToUniquePtr(nva2e::CreateClassifierEmotionExecutor(params, classifierParams));
        if (!executor) throw std::runtime_error("Failed to create A2E executor");

        const std::size_t emotionsSize = executor->GetEmotionsSize();

        // CSV header
        std::cout << "frame_index,time_s";
        static const char* kEmoNames[10] = {"amazement","anger","cheekiness","disgust","fear","grief","joy","outofbreath","pain","sadness"};
        for (std::size_t i = 0; i < emotionsSize; ++i) {
            const char* name = (i < 10 ? kEmoNames[i] : "emo");
            std::cout << "," << name << (i >= 10 ? std::to_string(i).c_str() : "");
        }
        std::cout << "\n";

        struct Ctx { std::size_t frame = 0; } ctx;
        auto cb = [](void* ud, const nva2e::IEmotionExecutor::Results& r) -> bool {
            auto* c = static_cast<Ctx*>(ud);
            std::vector<float> host(r.emotions.Size());
            nva2x::CopyDeviceToHost({host.data(), host.size()}, r.emotions, r.cudaStream);
            const double t = static_cast<double>(r.timeStampCurrentFrame) / 1000.0;
            std::cout << c->frame++ << "," << std::fixed << std::setprecision(3) << t;
            for (float v : host) std::cout << "," << std::setprecision(6) << v;
            std::cout << "\n";
            return true;
        };
        if (auto ec = executor->SetResultsCallback(cb, &ctx)) (void)ec;

        while (nva2x::GetNbReadyTracks(*executor) > 0) {
            if (auto ec = executor->Execute(nullptr)) (void)ec;
        }

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}


