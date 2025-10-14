// CLI: read WAV, run A2E + A2F, align by timestamp, print combined CSV
#include "audio2face/audio2face.h"
#include "audio2face/parse_helper.h"
#include "audio2emotion/audio2emotion.h"
#include "audio2x/cuda_utils.h"
#include "audio2x/audio_accumulator.h"
#include "AudioFile.h"
#include <cxxopts.hpp>
#include <iostream>
#include <vector>
#include <map>
#include <string>
#include <iomanip>

template <typename T> struct Destroyer { void operator()(T* p) const { if (p) p->Destroy(); } };
template <typename T> using UniquePtr = std::unique_ptr<T, Destroyer<T>>;
template <typename T> UniquePtr<T> ToUniquePtr(T* p) { return UniquePtr<T>(p); }

static std::vector<float> readAudioMono16k(const std::string& path) {
    AudioFile<float> audio;
    if (!audio.load(path)) throw std::runtime_error("Failed to load audio: " + path);
    if (audio.getSampleRate() != 16000) throw std::runtime_error("Expected 16kHz WAV input");
    if (audio.getNumChannels() < 1) throw std::runtime_error("No audio channels");
    return audio.samples[0];
}

struct EmotionsAtTs {
    std::vector<float> v; // size = 10
};

int main(int argc, char** argv) {
    try {
        cxxopts::Options options("a2f_a2e_combined_csv", "Combined A2E + A2F -> CSV");
        options.add_options()
            ("i,input", "Input WAV (16kHz)", cxxopts::value<std::string>())
            ("a2e-model", "A2E model.json", cxxopts::value<std::string>())
            ("type", "A2F type: regression|diffusion", cxxopts::value<std::string>()->default_value("regression"))
            ("a2f-model", "A2F model.json", cxxopts::value<std::string>())
            ("identity", "Diffusion identity index", cxxopts::value<int>()->default_value("0"))
            ("fps", "A2F FPS", cxxopts::value<int>()->default_value("60"))
            ("gpu-solver", "Use GPU blendshape solver", cxxopts::value<bool>()->default_value("false"))
            ("h,help", "Help");
        auto result = options.parse(argc, argv);
        if (result.count("help") || !result.count("input") || !result.count("a2e-model") || !result.count("a2f-model")) {
            std::cout << options.help() << std::endl;
            return 2;
        }
        const std::string inputWav = result["input"].as<std::string>();
        const std::string a2eModel = result["a2e-model"].as<std::string>();
        const std::string a2fModel = result["a2f-model"].as<std::string>();
        const std::string type = result["type"].as<std::string>();
        const int fps = result["fps"].as<int>();
        const bool useGpuSolver = result["gpu-solver"].as<bool>();
        const int identity = result["identity"].as<int>();

        auto audioBuf = readAudioMono16k(inputWav);
        auto cudaStream = ToUniquePtr(nva2x::CreateCudaStream());
        if (!cudaStream) throw std::runtime_error("CUDA stream failed");
        auto audioAcc = ToUniquePtr(nva2x::CreateAudioAccumulator(16000, 0));
        if (!audioAcc) throw std::runtime_error("Audio accumulator failed");
        audioAcc->Accumulate(nva2x::HostTensorFloatConstView{audioBuf.data(), audioBuf.size()}, cudaStream->Data());
        audioAcc->Close();

        // Run A2E first and store emotions by timestamp
        auto a2eInfo = ToUniquePtr(nva2e::ReadClassifierModelInfo(a2eModel.c_str()));
        if (!a2eInfo) throw std::runtime_error("A2E model read failed");
        nva2e::EmotionExecutorCreationParameters eparams{};
        eparams.cudaStream = cudaStream->Data(); eparams.nbTracks = 1; const auto sharedAudio = audioAcc.get(); eparams.sharedAudioAccumulators = &sharedAudio;
        auto eexec = ToUniquePtr(nva2e::CreateClassifierEmotionExecutor(eparams, a2eInfo->GetExecutorCreationParameters(60000, 30, 1, 30)));
        if (!eexec) throw std::runtime_error("A2E exec failed");
        std::map<long long, EmotionsAtTs> emoByTs;
        auto ecb = [](void* ud, const nva2e::IEmotionExecutor::Results& r) -> bool {
            auto* mapPtr = static_cast<std::map<long long, EmotionsAtTs>*>(ud);
            std::vector<float> host(r.emotions.Size());
            nva2x::CopyDeviceToHost({host.data(), host.size()}, r.emotions, r.cudaStream);
            (*mapPtr)[r.timeStampCurrentFrame] = EmotionsAtTs{std::move(host)};
            return true;
        };
        eexec->SetResultsCallback(ecb, &emoByTs);
        while (nva2x::GetNbReadyTracks(*eexec) > 0) eexec->Execute(nullptr);

        // Create A2F blendshape executor
        UniquePtr<nva2f::IBlendshapeExecutorBundle> bundle;
        if (type == "regression") {
            nva2f::IRegressionModel::IGeometryModelInfo* tmp = nullptr;
            bundle.reset(nva2f::ReadRegressionBlendshapeSolveExecutorBundle(1, a2fModel.c_str(), nva2f::IGeometryExecutor::ExecutionOption::All, useGpuSolver, static_cast<std::size_t>(fps), 1, &tmp, nullptr));
            if (!bundle || !tmp) throw std::runtime_error("A2F regression bundle failed");
            tmp->Destroy();
        } else if (type == "diffusion") {
            nva2f::IDiffusionModel::IGeometryModelInfo* tmp = nullptr;
            bundle.reset(nva2f::ReadDiffusionBlendshapeSolveExecutorBundle(1, a2fModel.c_str(), nva2f::IGeometryExecutor::ExecutionOption::All, useGpuSolver, static_cast<std::size_t>(identity), true, &tmp, nullptr));
            if (!bundle || !tmp) throw std::runtime_error("A2F diffusion bundle failed");
            tmp->Destroy();
        } else {
            throw std::runtime_error("Unknown type: " + type);
        }

        // Feed the same audio into the bundle executor
        bundle->GetAudioAccumulator(0).Accumulate(nva2x::HostTensorFloatConstView{audioBuf.data(), audioBuf.size()}, bundle->GetCudaStream().Data());
        bundle->GetAudioAccumulator(0).Close();

        // CSV header
        const std::size_t weightCount = bundle->GetExecutor().GetWeightCount();
        std::cout << "frame_index,time_s,amazement,anger,cheekiness,disgust,fear,grief,joy,outofbreath,pain,sadness";
        for (std::size_t i = 0; i < weightCount; ++i) std::cout << ",pose_" << i;
        std::cout << "\n";

        struct Ctx { std::size_t frame = 0; std::map<long long, EmotionsAtTs>* emo; } ctx{0, &emoByTs};
        auto cbh = [](void* ud, const nva2f::IBlendshapeExecutor::HostResults& r, std::error_code /*ec*/) {
            auto* c = static_cast<Ctx*>(ud);
            const double t = static_cast<double>(r.timeStampCurrentFrame) / 1000.0;
            // find nearest or last-known emotion by timestamp
            auto it = c->emo->upper_bound(r.timeStampCurrentFrame);
            if (it == c->emo->begin() && it != c->emo->end()) {
                // take current
            } else if (it != c->emo->begin()) {
                --it; // last-known <= ts
            }
            std::cout << c->frame++ << "," << std::fixed << std::setprecision(3) << t;
            if (it != c->emo->end()) {
                const auto& v = it->second.v;
                for (std::size_t i = 0; i < v.size(); ++i) std::cout << "," << std::setprecision(6) << v[i];
            } else {
                for (int i = 0; i < 10; ++i) std::cout << ",0";
            }
            for (std::size_t i = 0; i < r.weights.Size(); ++i) std::cout << "," << std::setprecision(6) << r.weights.Data()[i];
            std::cout << "\n";
        };

        auto& exec = bundle->GetExecutor();
        if (exec.GetResultType() == nva2f::IBlendshapeExecutor::ResultsType::HOST) {
            exec.SetResultsCallback(cbh, &ctx);
        } else {
            auto cbd = [](void* ud, const nva2f::IBlendshapeExecutor::DeviceResults& r) -> bool {
                auto* c = static_cast<Ctx*>(ud);
                std::vector<float> host(r.weights.Size());
                nva2x::CopyDeviceToHost({host.data(), host.size()}, r.weights, r.cudaStream);
                const double t = static_cast<double>(r.timeStampCurrentFrame) / 1000.0;
                auto it = c->emo->upper_bound(r.timeStampCurrentFrame);
                if (it != c->emo->begin()) --it;
                std::cout << c->frame++ << "," << std::fixed << std::setprecision(3) << t;
                if (it != c->emo->end()) {
                    const auto& v = it->second.v;
                    for (std::size_t i = 0; i < v.size(); ++i) std::cout << "," << std::setprecision(6) << v[i];
                } else {
                    for (int i = 0; i < 10; ++i) std::cout << ",0";
                }
                for (float w : host) std::cout << "," << std::setprecision(6) << w;
                std::cout << "\n";
                return true;
            };
            exec.SetResultsCallback(cbd, &ctx);
        }

        while (nva2x::GetNbReadyTracks(exec) > 0) exec.Execute(nullptr);
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}


