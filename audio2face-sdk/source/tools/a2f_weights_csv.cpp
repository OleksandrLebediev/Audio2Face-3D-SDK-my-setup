// Minimal CLI tool: read WAV, run A2F blendshape solve (regression/diffusion), print weights CSV
#include "audio2face/audio2face.h"
#include "audio2face/parse_helper.h"
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
    if (!audio.load(path)) throw std::runtime_error("Failed to load audio: " + path);
    if (audio.getSampleRate() != 16000) throw std::runtime_error("Expected 16kHz WAV input");
    if (audio.getNumChannels() < 1) throw std::runtime_error("No audio channels");
    return audio.samples[0];
}

int main(int argc, char** argv) {
    try {
        cxxopts::Options options("a2f_weights_csv", "Audio2Face blendshape weights -> CSV");
        options.add_options()
            ("i,input", "Input WAV (16kHz)", cxxopts::value<std::string>())
            ("type", "Model type: regression|diffusion", cxxopts::value<std::string>()->default_value("regression"))
            ("model", "Model JSON (geometry model.json)", cxxopts::value<std::string>())
            ("identity", "Diffusion identity index", cxxopts::value<int>()->default_value("0"))
            ("fps", "Target FPS for geometry", cxxopts::value<int>()->default_value("60"))
            ("gpu-solver", "Use GPU blendshape solver", cxxopts::value<bool>()->default_value("false"))
            ("h,help", "Show help");
        auto result = options.parse(argc, argv);
        if (result.count("help") || !result.count("input") || !result.count("model")) {
            std::cout << options.help() << std::endl;
            return 2;
        }
        const std::string inputWav = result["input"].as<std::string>();
        const std::string modelJson = result["model"].as<std::string>();
        const std::string type = result["type"].as<std::string>();
        const int fps = result["fps"].as<int>();
        const bool useGpuSolver = result["gpu-solver"].as<bool>();
        const int identity = result["identity"].as<int>();

        auto audioBuf = readAudioMono16k(inputWav);

        auto cudaStream = ToUniquePtr(nva2x::CreateCudaStream());
        if (!cudaStream) throw std::runtime_error("Failed to create CUDA stream");
        auto audioAcc = ToUniquePtr(nva2x::CreateAudioAccumulator(16000, 0));
        if (!audioAcc) throw std::runtime_error("Failed to create audio accumulator");
        if (auto ec = audioAcc->Accumulate(nva2x::HostTensorFloatConstView{audioBuf.data(), audioBuf.size()}, cudaStream->Data())) (void)ec;
        if (auto ec = audioAcc->Close()) (void)ec;

        // Create bundle and blendshape executor
        nva2f::IBlendshapeExecutorBundle* rawBundle = nullptr;
        if (type == "regression") {
            nva2f::IRegressionModel::IGeometryModelInfo* tmp = nullptr;
            rawBundle = nva2f::ReadRegressionBlendshapeSolveExecutorBundle(
                1, modelJson.c_str(), nva2f::IGeometryExecutor::ExecutionOption::All, useGpuSolver, static_cast<std::size_t>(fps), 1, &tmp, nullptr
            );
            if (!rawBundle || !tmp) throw std::runtime_error("Failed to read regression bundle");
            tmp->Destroy();
        } else if (type == "diffusion") {
            nva2f::IDiffusionModel::IGeometryModelInfo* tmp = nullptr;
            rawBundle = nva2f::ReadDiffusionBlendshapeSolveExecutorBundle(
                1, modelJson.c_str(), nva2f::IGeometryExecutor::ExecutionOption::All, useGpuSolver, static_cast<std::size_t>(identity), true, &tmp, nullptr
            );
            if (!rawBundle || !tmp) throw std::runtime_error("Failed to read diffusion bundle");
            tmp->Destroy();
        } else {
            throw std::runtime_error("Unknown type: " + type);
        }
        UniquePtr<nva2f::IBlendshapeExecutorBundle> bundle(rawBundle);

        // Put default emotion once so that geometry can run
        {
            auto& emoAcc = bundle->GetEmotionAccumulator(0);
            // query count from skin solver config if available is non-trivial; use network info via model json is internal
            // Instead, accumulate a zero-sized default by reading GetWeightCount later; but we need at least one emotion value.
            // Use zero-vector of size 10 (default emotion dims) — the solver/bundle uses A2E internally if needed; this is a safe default for neutral.
            std::vector<float> neutral(10, 0.0f);
            emoAcc.Accumulate(0, nva2x::HostTensorFloatConstView{neutral.data(), neutral.size()}, bundle->GetCudaStream().Data());
            emoAcc.Close();
        }

        // Accumulate audio
        if (auto ec = bundle->GetAudioAccumulator(0).Accumulate(nva2x::HostTensorFloatConstView{audioBuf.data(), audioBuf.size()}, bundle->GetCudaStream().Data())) (void)ec;
        if (auto ec = bundle->GetAudioAccumulator(0).Close()) (void)ec;

        auto& exec = bundle->GetExecutor();
        const std::size_t weightCount = exec.GetWeightCount();

        // Header
        std::cout << "frame_index,time_s";
        for (std::size_t i = 0; i < weightCount; ++i) {
            std::cout << ",pose_" << i;
        }
        std::cout << "\n";

        struct Ctx { std::size_t frame = 0; } ctx;
        auto cb = [](void* ud, const nva2f::IBlendshapeExecutor::HostResults& r) {
            auto* c = static_cast<Ctx*>(ud);
            const double t = static_cast<double>(r.timeStampCurrentFrame) / 1000.0;
            std::cout << c->frame++ << "," << std::fixed << std::setprecision(3) << t;
            for (std::size_t i = 0; i < r.weights.Size(); ++i) std::cout << "," << std::setprecision(6) << r.weights.Data()[i];
            std::cout << "\n";
        };

        if (exec.GetResultType() == nva2f::IBlendshapeExecutor::ResultsType::HOST) {
            exec.SetResultsCallback(cb, &ctx);
        } else {
            auto cbd = [](void* ud, const nva2f::IBlendshapeExecutor::DeviceResults& r) -> bool {
                auto* c = static_cast<Ctx*>(ud);
                std::vector<float> host(r.weights.Size());
                nva2x::CopyDeviceToHost({host.data(), host.size()}, r.weights, r.cudaStream);
                const double t = static_cast<double>(r.timeStampCurrentFrame) / 1000.0;
                std::cout << c->frame++ << "," << std::fixed << std::setprecision(3) << t;
                for (float v : host) std::cout << "," << std::setprecision(6) << v;
                std::cout << "\n";
                return true;
            };
            exec.SetResultsCallback(cbd, &ctx);
        }

        while (nva2x::GetNbReadyTracks(exec) > 0) {
            exec.Execute(nullptr);
        }

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}


